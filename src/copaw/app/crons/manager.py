# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ...config import get_heartbeat_config, get_evolution_config

from ..console_push_store import append as push_store_append
from .executor import CronExecutor
from .evolution import run_evolution_once
from .heartbeat import parse_heartbeat_every, run_heartbeat_once
from .models import CronJobSpec, CronJobState
from .repo.base import BaseJobRepository

HEARTBEAT_JOB_ID = "_heartbeat"
EVOLUTION_JOB_ID = "_evolution"

logger = logging.getLogger(__name__)


@dataclass
class _Runtime:
    sem: asyncio.Semaphore


class CronManager:
    def __init__(
        self,
        *,
        repo: BaseJobRepository,
        runner: Any,
        channel_manager: Any,
        timezone: str = "UTC",  # pylint: disable=redefined-outer-name
        agent_id: Optional[str] = None,
    ):
        self._repo = repo
        self._runner = runner
        self._channel_manager = channel_manager
        self._agent_id = agent_id
        self._scheduler = AsyncIOScheduler(timezone=timezone)
        self._executor = CronExecutor(
            runner=runner,
            channel_manager=channel_manager,
        )

        self._lock = asyncio.Lock()
        self._states: Dict[str, CronJobState] = {}
        self._rt: Dict[str, _Runtime] = {}
        self._on_message_jobs: set[str] = set()
        self._started = False

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                return
            jobs_file = await self._repo.load()

            self._scheduler.start()
            for job in jobs_file.jobs:
                try:
                    await self._register_or_update(job)
                except Exception as e:  # pylint: disable=broad-except
                    cron_expr = job.schedule.cron if job.schedule else None
                    logger.warning(
                        "Skipping invalid cron job during startup: "
                        "job_id=%s name=%s cron=%s error=%s",
                        job.id,
                        job.name,
                        cron_expr,
                        repr(e),
                    )
                    if job.enabled:
                        disabled_job = job.model_copy(
                            update={"enabled": False},
                        )
                        await self._repo.upsert_job(disabled_job)
                        logger.warning(
                            "Auto-disabled invalid cron job: "
                            "job_id=%s name=%s",
                            job.id,
                            job.name,
                        )

            # Heartbeat: one interval job when enabled in config
            hb = get_heartbeat_config(self._agent_id)
            if getattr(hb, "enabled", False):
                interval_seconds = parse_heartbeat_every(hb.every)
                self._scheduler.add_job(
                    self._heartbeat_callback,
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id=HEARTBEAT_JOB_ID,
                    replace_existing=True,
                )
                logger.info(
                    f"Heartbeat job scheduled for agent {self._agent_id}: "
                    f"every={hb.every} (interval={interval_seconds}s)",
                )

            evo = get_evolution_config(self._agent_id)
            if getattr(evo, "enabled", False) and evo.mode == "full_auto":
                interval_seconds = parse_heartbeat_every(evo.every)
                self._scheduler.add_job(
                    self._evolution_callback,
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id=EVOLUTION_JOB_ID,
                    replace_existing=True,
                )
                logger.info(
                    "Evolution job scheduled for agent %s: every=%s "
                    "(interval=%ss)",
                    self._agent_id,
                    evo.every,
                    interval_seconds,
                )

            self._started = True

    async def stop(self) -> None:
        async with self._lock:
            if not self._started:
                return
            self._scheduler.shutdown(wait=False)
            self._started = False

    # ----- read/state -----

    async def list_jobs(self) -> list[CronJobSpec]:
        return await self._repo.list_jobs()

    async def get_job(self, job_id: str) -> Optional[CronJobSpec]:
        return await self._repo.get_job(job_id)

    def get_state(self, job_id: str) -> CronJobState:
        return self._states.get(job_id, CronJobState())

    # ----- write/control -----

    async def create_or_replace_job(self, spec: CronJobSpec) -> None:
        async with self._lock:
            await self._repo.upsert_job(spec)
            if self._started:
                await self._register_or_update(spec)

    async def delete_job(self, job_id: str) -> bool:
        async with self._lock:
            if self._started and self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)
            self._on_message_jobs.discard(job_id)
            self._states.pop(job_id, None)
            self._rt.pop(job_id, None)
            return await self._repo.delete_job(job_id)

    async def pause_job(self, job_id: str) -> None:
        async with self._lock:
            spec = await self._repo.get_job(job_id)
            if spec is None:
                raise KeyError(f"Job not found: {job_id}")
            if self._scheduler.get_job(job_id):
                self._scheduler.pause_job(job_id)
            await self._repo.upsert_job(spec.model_copy(update={"enabled": False}))

    async def resume_job(self, job_id: str) -> None:
        async with self._lock:
            spec = await self._repo.get_job(job_id)
            if spec is None:
                raise KeyError(f"Job not found: {job_id}")
            if self._scheduler.get_job(job_id):
                self._scheduler.resume_job(job_id)
            await self._repo.upsert_job(spec.model_copy(update={"enabled": True}))

    async def reschedule_heartbeat(self) -> None:
        """Reload heartbeat config and update or remove the heartbeat job.

        Note: CronManager should always be started during workspace
        initialization, so this method assumes self._started is True.
        """
        async with self._lock:
            if not self._started:
                logger.warning(
                    f"CronManager not started for agent {self._agent_id}, "
                    f"cannot reschedule heartbeat. This should not happen.",
                )
                return

            hb = get_heartbeat_config(self._agent_id)

            # Remove existing heartbeat job if present
            if self._scheduler.get_job(HEARTBEAT_JOB_ID):
                self._scheduler.remove_job(HEARTBEAT_JOB_ID)

            # Add heartbeat job if enabled
            if getattr(hb, "enabled", False):
                interval_seconds = parse_heartbeat_every(hb.every)
                self._scheduler.add_job(
                    self._heartbeat_callback,
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id=HEARTBEAT_JOB_ID,
                    replace_existing=True,
                )
                logger.info(
                    "heartbeat rescheduled: every=%s (interval=%ss)",
                    hb.every,
                    interval_seconds,
                )
            else:
                logger.info("heartbeat disabled, job removed")

    async def reschedule_evolution(self) -> None:
        """Reload evolution config and update or remove evolution job."""
        async with self._lock:
            if not self._started:
                logger.warning(
                    "CronManager not started for agent %s, cannot "
                    "reschedule evolution.",
                    self._agent_id,
                )
                return

            evo = get_evolution_config(self._agent_id)

            if self._scheduler.get_job(EVOLUTION_JOB_ID):
                self._scheduler.remove_job(EVOLUTION_JOB_ID)

            if getattr(evo, "enabled", False) and evo.mode == "full_auto":
                interval_seconds = parse_heartbeat_every(evo.every)
                self._scheduler.add_job(
                    self._evolution_callback,
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id=EVOLUTION_JOB_ID,
                    replace_existing=True,
                )
                logger.info(
                    "evolution rescheduled: every=%s (interval=%ss)",
                    evo.every,
                    interval_seconds,
                )
            else:
                logger.info("evolution disabled or not full_auto, job removed")

    async def run_job(self, job_id: str) -> None:
        """Trigger a job to run in the background (fire-and-forget).

        Raises KeyError if the job does not exist.
        The actual execution happens asynchronously; errors are logged
        and reflected in the job state but NOT propagated to the caller.
        """
        job = await self._repo.get_job(job_id)
        if not job:
            raise KeyError(f"Job not found: {job_id}")
        logger.info(
            "cron run_job (async): job_id=%s channel=%s task_type=%s "
            "target_user_id=%s target_session_id=%s",
            job_id,
            job.dispatch.channel,
            job.task_type,
            (job.dispatch.target.user_id or "")[:40],
            (job.dispatch.target.session_id or "")[:40],
        )
        task = asyncio.create_task(
            self._execute_once(job),
            name=f"cron-run-{job_id}",
        )
        task.add_done_callback(lambda t: self._task_done_cb(t, job))

    # ----- callbacks -----

    def _task_done_cb(self, task: asyncio.Task, job: CronJobSpec) -> None:
        """Suppress and log exceptions from fire-and-forget tasks.

        On failure, push an error message to the console push store so
        the frontend can display it.
        """
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error(
                "cron background task %s failed: %s",
                task.get_name(),
                repr(exc),
            )
            # Push error to the console for the frontend to display
            session_id = job.dispatch.target.session_id
            if session_id:
                error_text = f"❌ Cron job [{job.name}] failed: {exc}"
                asyncio.ensure_future(
                    push_store_append(session_id, error_text),
                )

    # ----- internal -----

    async def handle_message_event(
        self,
        *,
        channel: str,
        user_id: str,
        session_id: str,
        text: str,
    ) -> int:
        """Handle one inbound user message and trigger on_message jobs."""
        fired = 0
        jobs = await self._repo.list_jobs()
        for job in jobs:
            if not job.enabled:
                continue
            if job.schedule.type != "on_message":
                continue
            if not self._on_message_matches(
                job,
                channel=channel,
                user_id=user_id,
                session_id=session_id,
                text=text,
            ):
                continue
            fired += 1
            task = asyncio.create_task(
                self._execute_once(job),
                name=f"cron-on-message-{job.id}",
            )
            task.add_done_callback(lambda t, spec=job: self._task_done_cb(t, spec))
        return fired

    @staticmethod
    def _on_message_matches(
        job: CronJobSpec,
        *,
        channel: str,
        user_id: str,
        session_id: str,
        text: str,
    ) -> bool:
        """Return True if on_message schedule matches the event."""
        sch = job.schedule
        if sch.channel and sch.channel != channel:
            return False

        expected_user = sch.user_id or job.dispatch.target.user_id
        if expected_user and expected_user != user_id:
            return False

        expected_session = sch.session_id or job.dispatch.target.session_id
        if expected_session and expected_session != session_id:
            return False

        if sch.contains and sch.contains.lower() not in (text or "").lower():
            return False

        if sch.pattern:
            try:
                if re.search(sch.pattern, text or "") is None:
                    return False
            except re.error:
                return False

        return True

    async def _register_or_update(self, spec: CronJobSpec) -> None:
        # per-job concurrency semaphore
        self._rt[spec.id] = _Runtime(
            sem=asyncio.Semaphore(spec.runtime.max_concurrency),
        )

        # Replace existing scheduler job if any
        if self._scheduler.get_job(spec.id):
            self._scheduler.remove_job(spec.id)

        if spec.schedule.type == "on_message":
            self._on_message_jobs.add(spec.id)
            st = self._states.get(spec.id, CronJobState())
            st.next_run_at = None
            self._states[spec.id] = st
            return

        self._on_message_jobs.discard(spec.id)
        # Validate and build trigger first. If invalid, fail fast without
        # mutating scheduler/runtime state.
        trigger = self._build_trigger(spec)

        self._scheduler.add_job(
            self._scheduled_callback,
            trigger=trigger,
            id=spec.id,
            args=[spec.id],
            misfire_grace_time=spec.runtime.misfire_grace_seconds,
            replace_existing=True,
        )

        if not spec.enabled:
            self._scheduler.pause_job(spec.id)

        # update next_run
        aps_job = self._scheduler.get_job(spec.id)
        st = self._states.get(spec.id, CronJobState())
        st.next_run_at = aps_job.next_run_time if aps_job else None
        self._states[spec.id] = st

    def _build_trigger(self, spec: CronJobSpec):
        schedule = spec.schedule
        if schedule.type == "once":
            assert schedule.at is not None
            return DateTrigger(run_date=schedule.at, timezone=schedule.timezone)

        if schedule.type == "interval":
            assert schedule.every_seconds is not None
            return IntervalTrigger(
                seconds=schedule.every_seconds,
                timezone=schedule.timezone,
            )

        # enforce 5 fields (no seconds)
        cron_expr = schedule.cron or ""
        parts = [p for p in cron_expr.split() if p]
        if len(parts) != 5:
            raise ValueError(
                f"cron must have 5 fields, got {len(parts)}:"
                f" {cron_expr}",
            )

        minute, hour, day, month, day_of_week = parts
        return CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone=schedule.timezone,
        )

    async def _scheduled_callback(self, job_id: str) -> None:
        job = await self._repo.get_job(job_id)
        if not job:
            return

        await self._execute_once(job)

        # refresh next_run
        aps_job = self._scheduler.get_job(job_id)
        st = self._states.get(job_id, CronJobState())
        st.next_run_at = aps_job.next_run_time if aps_job else None
        self._states[job_id] = st

    async def _heartbeat_callback(self) -> None:
        """Run one heartbeat (HEARTBEAT.md as query, optional dispatch)."""
        try:
            # Get workspace_dir from runner if available
            workspace_dir = None
            if hasattr(self._runner, "workspace_dir"):
                workspace_dir = self._runner.workspace_dir

            await run_heartbeat_once(
                runner=self._runner,
                channel_manager=self._channel_manager,
                agent_id=self._agent_id,
                workspace_dir=workspace_dir,
            )
        except asyncio.CancelledError:
            logger.info("heartbeat cancelled")
            raise
        except Exception:  # pylint: disable=broad-except
            logger.exception("heartbeat run failed")

    async def _evolution_callback(self) -> None:
        """Run one self-evolution iteration from SELF_EVOLUTION.md."""
        try:
            workspace_dir = None
            if hasattr(self._runner, "workspace_dir"):
                workspace_dir = self._runner.workspace_dir

            await run_evolution_once(
                runner=self._runner,
                agent_id=self._agent_id,
                workspace_dir=workspace_dir,
            )
        except asyncio.CancelledError:
            logger.info("evolution cancelled")
            raise
        except Exception:  # pylint: disable=broad-except
            logger.exception("evolution run failed")

    async def _execute_once(self, job: CronJobSpec) -> None:
        rt = self._rt.get(job.id)
        if not rt:
            rt = _Runtime(sem=asyncio.Semaphore(job.runtime.max_concurrency))
            self._rt[job.id] = rt

        async with rt.sem:
            st = self._states.get(job.id, CronJobState())
            st.last_status = "running"
            self._states[job.id] = st

            try:
                await self._executor.execute(job)
                st.last_status = "success"
                st.last_error = None
                logger.info(
                    "cron _execute_once: job_id=%s status=success",
                    job.id,
                )
            except asyncio.CancelledError:
                st.last_status = "cancelled"
                st.last_error = "Job was cancelled"
                logger.info(
                    "cron _execute_once: job_id=%s status=cancelled",
                    job.id,
                )
                raise
            except Exception as e:  # pylint: disable=broad-except
                st.last_status = "error"
                st.last_error = repr(e)
                logger.warning(
                    "cron _execute_once: job_id=%s status=error error=%s",
                    job.id,
                    repr(e),
                )
                raise
            finally:
                st.last_run_at = datetime.now(timezone.utc)
                self._states[job.id] = st
