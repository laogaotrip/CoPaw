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
  CollaborationEvent,
  CollaborationStats,
} from "../../../api/types/digitalEmployee";
import styles from "./index.module.less";

type ActionMode = "notify" | "consult" | "delegate";

type ActionFormValues = {
  mode: ActionMode;
  target_agent_id: string;
  content: string;
  channel: string;
  user_id: string;
  session_id: string;
  hop_count: number;
};

type FilterValues = {
  mode?: string;
  target_agent_id?: string;
  limit: number;
  since_hours: number;
};

export default function CollaborationPage() {
  const { t } = useTranslation();
  const { selectedAgent } = useAgentStore();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [eventsLoading, setEventsLoading] = useState(false);

  const [events, setEvents] = useState<CollaborationEvent[]>([]);
  const [stats, setStats] = useState<CollaborationStats | null>(null);
  const [resultText, setResultText] = useState("");

  const [actionForm] = Form.useForm<ActionFormValues>();
  const [filterForm] = Form.useForm<FilterValues>();

  const actionMode = Form.useWatch("mode", actionForm);

  const loadData = useCallback(async () => {
    const values = filterForm.getFieldsValue();
    const limit = values.limit || 50;
    const mode = values.mode || "";
    const target = values.target_agent_id || "";
    const sinceHours = values.since_hours || 24;

    setEventsLoading(true);
    try {
      const [eventsResp, statsResp] = await Promise.all([
        api.listCollaborationEvents({
          limit,
          mode,
          target_agent_id: target,
        }),
        api.getCollaborationStats(sinceHours),
      ]);
      setEvents(Array.isArray(eventsResp.events) ? eventsResp.events : []);
      setStats(statsResp);
    } catch (error) {
      console.error("Failed to load collaboration data:", error);
      message.error(t("collaboration.loadFailed"));
    } finally {
      setEventsLoading(false);
      setLoading(false);
    }
  }, [filterForm, t]);

  useEffect(() => {
    actionForm.setFieldsValue({
      mode: "notify",
      target_agent_id: "",
      content: "",
      channel: "console",
      user_id: "collaboration",
      session_id: "collaboration",
      hop_count: 0,
    });
    filterForm.setFieldsValue({
      mode: "",
      target_agent_id: "",
      limit: 50,
      since_hours: 24,
    });
    loadData();
  }, [actionForm, filterForm, loadData, selectedAgent]);

  const submitAction = async () => {
    try {
      const values = await actionForm.validateFields();
      setSubmitting(true);
      setResultText("");

      if (values.mode === "notify") {
        await api.notifyCollaboration({
          target_agent_id: values.target_agent_id,
          text: values.content,
          channel: values.channel,
          user_id: values.user_id,
          session_id: values.session_id,
        });
        message.success(t("collaboration.notifySuccess"));
      } else if (values.mode === "consult") {
        const response = await api.consultCollaboration({
          target_agent_id: values.target_agent_id,
          prompt: values.content,
          hop_count: values.hop_count,
          user_id: values.user_id,
          session_id: values.session_id,
        });
        setResultText(response.response_text || "");
        message.success(t("collaboration.consultSuccess"));
      } else {
        const response = await api.delegateCollaboration({
          target_agent_id: values.target_agent_id,
          prompt: values.content,
          hop_count: values.hop_count,
          user_id: values.user_id,
          session_id: values.session_id,
        });
        setResultText(response.response_text || "");
        message.success(t("collaboration.delegateSuccess"));
      }

      await loadData();
    } catch (error) {
      if (error instanceof Error && "errorFields" in error) {
        return;
      }
      console.error("Failed to submit collaboration action:", error);
      message.error(t("collaboration.actionFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const modeOptions = useMemo(
    () => [
      { value: "", label: t("collaboration.allModes") },
      { value: "notify", label: t("collaboration.modeNotify") },
      { value: "consult", label: t("collaboration.modeConsult") },
      { value: "delegate", label: t("collaboration.modeDelegate") },
    ],
    [t],
  );

  const columns = useMemo(
    () => [
      {
        title: t("collaboration.colTime"),
        dataIndex: "ts",
        key: "ts",
        width: 200,
      },
      {
        title: t("collaboration.colMode"),
        dataIndex: "mode",
        key: "mode",
        width: 120,
        render: (value: string) => <Tag>{value || "-"}</Tag>,
      },
      {
        title: t("collaboration.colTargetAgent"),
        dataIndex: "target_agent_id",
        key: "target_agent_id",
        width: 160,
        ellipsis: true,
      },
      {
        title: t("collaboration.colSession"),
        dataIndex: "session_id",
        key: "session_id",
        width: 180,
        ellipsis: true,
      },
      {
        title: t("collaboration.colPrompt"),
        dataIndex: "prompt",
        key: "prompt",
        ellipsis: true,
      },
      {
        title: t("collaboration.colResponse"),
        dataIndex: "response_text",
        key: "response_text",
        ellipsis: true,
      },
    ],
    [t],
  );

  if (loading) {
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>{t("collaboration.title")}</h1>
        <p className={styles.description}>{t("collaboration.description")}</p>
        <span className={styles.loading}>{t("common.loading")}</span>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>{t("collaboration.title")}</h1>
      <p className={styles.description}>{t("collaboration.description")}</p>

      <Card className={styles.card}>
        <h3 className={styles.cardTitle}>{t("collaboration.actionTitle")}</h3>
        <Form layout="vertical" form={actionForm}>
          <div className={styles.rowThree}>
            <Form.Item
              label={t("collaboration.mode")}
              name="mode"
              rules={[{ required: true }]}
            >
              <Select
                options={modeOptions.filter((item) => item.value !== "")}
              />
            </Form.Item>
            <Form.Item
              label={t("collaboration.targetAgent")}
              name="target_agent_id"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label={t("collaboration.channel")} name="channel">
              <Input disabled={actionMode !== "notify"} />
            </Form.Item>
          </div>

          <div className={styles.rowThree}>
            <Form.Item label={t("collaboration.userId")} name="user_id">
              <Input />
            </Form.Item>
            <Form.Item label={t("collaboration.sessionId")} name="session_id">
              <Input />
            </Form.Item>
            <Form.Item label={t("collaboration.hopCount")} name="hop_count">
              <InputNumber min={0} max={3} style={{ width: "100%" }} />
            </Form.Item>
          </div>

          <Form.Item
            label={
              actionMode === "notify"
                ? t("collaboration.notifyText")
                : t("collaboration.prompt")
            }
            name="content"
            rules={[{ required: true }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>

          <div className={styles.actions}>
            <Button type="primary" loading={submitting} onClick={submitAction}>
              {t("collaboration.submit")}
            </Button>
          </div>
        </Form>

        {resultText ? (
          <div className={styles.resultBox}>
            <div className={styles.resultTitle}>{t("collaboration.result")}</div>
            <pre className={styles.resultText}>{resultText}</pre>
          </div>
        ) : null}
      </Card>

      <Card className={styles.card}>
        <div className={styles.rowBetween}>
          <h3 className={styles.cardTitle}>{t("collaboration.eventsTitle")}</h3>
          <Button onClick={loadData}>{t("common.refresh")}</Button>
        </div>

        <Form layout="vertical" form={filterForm}>
          <div className={styles.rowFour}>
            <Form.Item label={t("collaboration.filterMode")} name="mode">
              <Select options={modeOptions} />
            </Form.Item>
            <Form.Item
              label={t("collaboration.filterTargetAgent")}
              name="target_agent_id"
            >
              <Input />
            </Form.Item>
            <Form.Item label={t("collaboration.limit")} name="limit">
              <InputNumber min={1} max={500} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label={t("collaboration.sinceHours")} name="since_hours">
              <InputNumber min={0} max={720} style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <div className={styles.actions}>
            <Button onClick={loadData}>{t("common.refresh")}</Button>
          </div>
        </Form>

        <Table
          rowKey={(record, index) => `${record.ts || ""}-${index}`}
          columns={columns}
          dataSource={events}
          loading={eventsLoading}
          scroll={{ x: 1200 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: false,
          }}
        />
      </Card>

      <Card className={styles.card}>
        <h3 className={styles.cardTitle}>{t("collaboration.statsTitle")}</h3>
        <div className={styles.statsGrid}>
          <div className={styles.statItem}>
            <div className={styles.statLabel}>{t("collaboration.totalEvents")}</div>
            <div className={styles.statValue}>{stats?.total ?? 0}</div>
          </div>
          <div className={styles.statItem}>
            <div className={styles.statLabel}>{t("collaboration.byMode")}</div>
            <div className={styles.statList}>
              {Object.entries(stats?.by_mode || {}).length === 0
                ? "-"
                : Object.entries(stats?.by_mode || {}).map(([k, v]) => (
                    <Tag key={k}>{`${k}: ${v}`}</Tag>
                  ))}
            </div>
          </div>
          <div className={styles.statItem}>
            <div className={styles.statLabel}>{t("collaboration.byTarget")}</div>
            <div className={styles.statList}>
              {Object.entries(stats?.by_target_agent || {}).length === 0
                ? "-"
                : Object.entries(stats?.by_target_agent || {}).map(([k, v]) => (
                    <Tag key={k}>{`${k}: ${v}`}</Tag>
                  ))}
            </div>
          </div>
          <div className={styles.statItem}>
            <div className={styles.statLabel}>{t("collaboration.sinceHours")}</div>
            <div className={styles.statValue}>{stats?.since_hours ?? 24}</div>
          </div>
        </div>
      </Card>
    </div>
  );
}
