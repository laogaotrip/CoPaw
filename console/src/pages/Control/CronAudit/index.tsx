import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  message,
} from "@agentscope-ai/design";
import { Table, Tag } from "antd";
import { useTranslation } from "react-i18next";
import api from "../../../api";
import { useAgentStore } from "../../../stores/agentStore";
import type {
  CronAuditEvent,
  CronAuditStats,
} from "../../../api/types/digitalEmployee";
import styles from "./index.module.less";

type FilterValues = {
  job_id?: string;
  status?: string;
  trigger_type?: string;
  limit: number;
  since_hours: number;
};

export default function CronAuditPage() {
  const { t } = useTranslation();
  const { selectedAgent } = useAgentStore();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [events, setEvents] = useState<CronAuditEvent[]>([]);
  const [stats, setStats] = useState<CronAuditStats | null>(null);

  const [filterForm] = Form.useForm<FilterValues>();

  const loadData = useCallback(async () => {
    const values = filterForm.getFieldsValue();
    const query = {
      job_id: values.job_id || "",
      status: values.status || "",
      trigger_type: values.trigger_type || "",
      limit: values.limit || 100,
    };
    const sinceHours = values.since_hours || 24;

    setRefreshing(true);
    try {
      const [eventsResp, statsResp] = await Promise.all([
        api.listCronAuditEvents(query),
        api.getCronAuditStats(sinceHours),
      ]);
      setEvents(Array.isArray(eventsResp.events) ? eventsResp.events : []);
      setStats(statsResp);
    } catch (error) {
      console.error("Failed to load cron audit data:", error);
      message.error(t("cronAudit.loadFailed"));
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, [filterForm, t]);

  useEffect(() => {
    filterForm.setFieldsValue({
      job_id: "",
      status: "",
      trigger_type: "",
      limit: 100,
      since_hours: 24,
    });
    loadData();
  }, [filterForm, loadData, selectedAgent]);

  const columns = useMemo(
    () => [
      {
        title: t("cronAudit.colTime"),
        dataIndex: "ts",
        key: "ts",
        width: 220,
      },
      {
        title: t("cronAudit.colJobId"),
        dataIndex: "job_id",
        key: "job_id",
        width: 260,
        ellipsis: true,
      },
      {
        title: t("cronAudit.colStatus"),
        dataIndex: "status",
        key: "status",
        width: 120,
        render: (value: string) => <Tag>{value || "-"}</Tag>,
      },
      {
        title: t("cronAudit.colTriggerType"),
        dataIndex: "trigger_type",
        key: "trigger_type",
        width: 120,
        render: (value: string) => <Tag>{value || "-"}</Tag>,
      },
      {
        title: t("cronAudit.colDetail"),
        dataIndex: "detail",
        key: "detail",
        render: (value: unknown) => {
          if (!value) return "-";
          try {
            return JSON.stringify(value);
          } catch {
            return String(value);
          }
        },
      },
    ],
    [t],
  );

  if (loading) {
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>{t("cronAudit.title")}</h1>
        <p className={styles.description}>{t("cronAudit.description")}</p>
        <span className={styles.loading}>{t("common.loading")}</span>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>{t("cronAudit.title")}</h1>
      <p className={styles.description}>{t("cronAudit.description")}</p>

      <Card className={styles.card}>
        <div className={styles.rowBetween}>
          <h3 className={styles.cardTitle}>{t("cronAudit.filters")}</h3>
          <Button onClick={loadData} loading={refreshing}>
            {t("common.refresh")}
          </Button>
        </div>

        <Form layout="vertical" form={filterForm}>
          <div className={styles.rowFive}>
            <Form.Item label={t("cronAudit.jobId")} name="job_id">
              <Input />
            </Form.Item>
            <Form.Item label={t("cronAudit.status")} name="status">
              <Select
                allowClear
                options={[
                  { value: "", label: t("cronAudit.all") },
                  { value: "success", label: "success" },
                  { value: "error", label: "error" },
                  { value: "cancelled", label: "cancelled" },
                  { value: "skipped", label: "skipped" },
                ]}
              />
            </Form.Item>
            <Form.Item label={t("cronAudit.triggerType")} name="trigger_type">
              <Select
                allowClear
                options={[
                  { value: "", label: t("cronAudit.all") },
                  { value: "cron", label: "cron" },
                  { value: "on_message", label: "on_message" },
                  { value: "webhook", label: "webhook" },
                  { value: "poll", label: "poll" },
                ]}
              />
            </Form.Item>
            <Form.Item label={t("cronAudit.limit")} name="limit">
              <InputNumber min={1} max={1000} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label={t("cronAudit.sinceHours")} name="since_hours">
              <InputNumber min={0} max={720} style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <div className={styles.actions}>
            <Button onClick={loadData}>{t("common.refresh")}</Button>
          </div>
        </Form>
      </Card>

      <Card className={styles.card}>
        <h3 className={styles.cardTitle}>{t("cronAudit.eventsTitle")}</h3>
        <Table
          rowKey={(record, index) =>
            `${record.ts || ""}-${record.job_id || ""}-${index}`
          }
          columns={columns}
          dataSource={events}
          loading={refreshing}
          scroll={{ x: 1300 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: false,
          }}
        />
      </Card>

      <Card className={styles.card}>
        <h3 className={styles.cardTitle}>{t("cronAudit.statsTitle")}</h3>
        <div className={styles.statsGrid}>
          <div className={styles.statItem}>
            <div className={styles.statLabel}>{t("cronAudit.totalEvents")}</div>
            <div className={styles.statValue}>{stats?.total ?? 0}</div>
          </div>
          <div className={styles.statItem}>
            <div className={styles.statLabel}>{t("cronAudit.byStatus")}</div>
            <div className={styles.statList}>
              {Object.entries(stats?.by_status || {}).length === 0
                ? "-"
                : Object.entries(stats?.by_status || {}).map(([k, v]) => (
                    <Tag key={k}>{`${k}: ${v}`}</Tag>
                  ))}
            </div>
          </div>
          <div className={styles.statItem}>
            <div className={styles.statLabel}>{t("cronAudit.byTriggerType")}</div>
            <div className={styles.statList}>
              {Object.entries(stats?.by_trigger_type || {}).length === 0
                ? "-"
                : Object.entries(stats?.by_trigger_type || {}).map(([k, v]) => (
                    <Tag key={k}>{`${k}: ${v}`}</Tag>
                  ))}
            </div>
          </div>
          <div className={styles.statItem}>
            <div className={styles.statLabel}>{t("cronAudit.sinceHours")}</div>
            <div className={styles.statValue}>{stats?.since_hours ?? 24}</div>
          </div>
        </div>
      </Card>
    </div>
  );
}
