import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  message,
} from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import api from "../../../api";
import { useAgentStore } from "../../../stores/agentStore";
import type {
  AgentModelSlotsResponse,
  AgentTriggerPolicyConfig,
  EvolutionConfig,
} from "../../../api/types/digitalEmployee";
import type { ProviderInfo } from "../../../api/types/provider";
import styles from "./index.module.less";

type ModelSlotFormValues = {
  auto_model_failover: boolean;
  primary_provider_id?: string;
  primary_model?: string;
  fallback_provider_id?: string;
  fallback_model?: string;
};

type TriggerFormValues = AgentTriggerPolicyConfig & {
  allowed_poll_domains_text: string;
};

function toModelFormValues(slots: AgentModelSlotsResponse): ModelSlotFormValues {
  return {
    auto_model_failover: Boolean(slots.auto_model_failover),
    primary_provider_id: slots.primary_model?.provider_id,
    primary_model: slots.primary_model?.model,
    fallback_provider_id: slots.fallback_model?.provider_id,
    fallback_model: slots.fallback_model?.model,
  };
}

function toTriggerFormValues(policy: AgentTriggerPolicyConfig): TriggerFormValues {
  return {
    ...policy,
    allowed_poll_domains_text: (policy.allowed_poll_domains || []).join("\n"),
  };
}

function toEvolutionFormValues(config: EvolutionConfig): EvolutionConfig {
  return {
    enabled: Boolean(config.enabled),
    mode: config.mode || "full_auto",
    every: config.every || "24h",
    query_file: config.query_file || "SELF_EVOLUTION.md",
    timeout_seconds: config.timeout_seconds || 300,
    session_id: config.session_id || "evolution",
    user_id: config.user_id || "evolution",
  };
}

export default function DigitalEmployeePage() {
  const { t } = useTranslation();
  const { selectedAgent } = useAgentStore();

  const [loading, setLoading] = useState(true);
  const [savingSlots, setSavingSlots] = useState(false);
  const [savingPolicy, setSavingPolicy] = useState(false);
  const [savingEvolution, setSavingEvolution] = useState(false);
  const [slotsSaveFeedback, setSlotsSaveFeedback] = useState<
    "success" | "error" | null
  >(null);

  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [modelSlots, setModelSlots] = useState<AgentModelSlotsResponse | null>(
    null,
  );
  const [triggerPolicy, setTriggerPolicy] =
    useState<AgentTriggerPolicyConfig | null>(null);
  const [evolutionConfig, setEvolutionConfig] =
    useState<EvolutionConfig | null>(null);

  const [slotsForm] = Form.useForm<ModelSlotFormValues>();
  const [triggerForm] = Form.useForm<TriggerFormValues>();
  const [evolutionForm] = Form.useForm<EvolutionConfig>();

  const providerOptions = useMemo(
    () =>
      providers.map((provider) => ({
        label: provider.name,
        value: provider.id,
      })),
    [providers],
  );

  const modelOptionsByProvider = useMemo(() => {
    const map = new Map<string, { label: string; value: string }[]>();
    for (const provider of providers) {
      const mergedModels = [
        ...(Array.isArray(provider.models) ? provider.models : []),
        ...(Array.isArray(provider.extra_models) ? provider.extra_models : []),
      ];
      const uniqueModels = new Map<string, string>();
      for (const model of mergedModels) {
        if (!model?.id) continue;
        uniqueModels.set(model.id, model.name || model.id);
      }
      map.set(
        provider.id,
        Array.from(uniqueModels.entries()).map(([id, name]) => ({
          label: name,
          value: id,
        })),
      );
    }
    return map;
  }, [providers]);

  const primaryProviderId = Form.useWatch("primary_provider_id", slotsForm);
  const primaryModel = Form.useWatch("primary_model", slotsForm);
  const fallbackProviderId = Form.useWatch("fallback_provider_id", slotsForm);
  const fallbackModel = Form.useWatch("fallback_model", slotsForm);

  const withCurrentModelOption = useCallback(
    (options: { label: string; value: string }[], current?: string) => {
      if (!current) return options;
      if (options.some((option) => option.value === current)) return options;
      return [{ label: current, value: current }, ...options];
    },
    [],
  );

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [providerList, slots, policy, evolution] = await Promise.all([
        api.listProviders(),
        api.getAgentModelSlots(),
        api.getTriggerPolicy(),
        api.getEvolutionConfig(),
      ]);

      setProviders(Array.isArray(providerList) ? providerList : []);
      setModelSlots(slots);
      setTriggerPolicy(policy);
      setEvolutionConfig(evolution);

      slotsForm.setFieldsValue(toModelFormValues(slots));
      triggerForm.setFieldsValue(toTriggerFormValues(policy));
      evolutionForm.setFieldsValue(toEvolutionFormValues(evolution));
    } catch (error) {
      console.error("Failed to load digital employee settings:", error);
      message.error(t("digitalEmployee.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [evolutionForm, slotsForm, t, triggerForm]);

  useEffect(() => {
    loadAll();
  }, [loadAll, selectedAgent]);

  const saveModelSlots = async () => {
    try {
      const values = await slotsForm.validateFields();
      setSavingSlots(true);
      setSlotsSaveFeedback(null);
      const body = {
        primary_model:
          values.primary_provider_id && values.primary_model
            ? {
                provider_id: values.primary_provider_id,
                model: values.primary_model,
              }
            : null,
        fallback_model:
          values.fallback_provider_id && values.fallback_model
            ? {
                provider_id: values.fallback_provider_id,
                model: values.fallback_model,
              }
            : null,
        auto_model_failover: Boolean(values.auto_model_failover),
      };
      const saved = await api.updateAgentModelSlots(body);
      setModelSlots(saved);
      slotsForm.setFieldsValue(toModelFormValues(saved));
      setSlotsSaveFeedback("success");
      message.success(t("digitalEmployee.modelSlotsSaved"));
    } catch (error) {
      if (error instanceof Error && "errorFields" in error) {
        return;
      }
      console.error("Failed to save model slots:", error);
      setSlotsSaveFeedback("error");
      message.error(t("digitalEmployee.saveFailed"));
    } finally {
      setSavingSlots(false);
    }
  };

  const saveTriggerPolicy = async () => {
    try {
      const values = await triggerForm.validateFields();
      setSavingPolicy(true);
      const domains = (values.allowed_poll_domains_text || "")
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);

      const body: AgentTriggerPolicyConfig = {
        enable_webhook: Boolean(values.enable_webhook),
        enable_poll: Boolean(values.enable_poll),
        block_private_network: Boolean(values.block_private_network),
        allowed_poll_domains: domains,
      };
      const saved = await api.updateTriggerPolicy(body);
      setTriggerPolicy(saved);
      triggerForm.setFieldsValue(toTriggerFormValues(saved));
      message.success(t("digitalEmployee.triggerPolicySaved"));
    } catch (error) {
      if (error instanceof Error && "errorFields" in error) {
        return;
      }
      console.error("Failed to save trigger policy:", error);
      message.error(t("digitalEmployee.saveFailed"));
    } finally {
      setSavingPolicy(false);
    }
  };

  const saveEvolutionConfig = async () => {
    try {
      const values = await evolutionForm.validateFields();
      setSavingEvolution(true);
      const body: EvolutionConfig = {
        enabled: Boolean(values.enabled),
        mode: values.mode || "full_auto",
        every: values.every || "24h",
        query_file: values.query_file || "SELF_EVOLUTION.md",
        timeout_seconds: Number(values.timeout_seconds || 300),
        session_id: values.session_id || "evolution",
        user_id: values.user_id || "evolution",
      };
      const saved = await api.updateEvolutionConfig(body);
      setEvolutionConfig(saved);
      evolutionForm.setFieldsValue(toEvolutionFormValues(saved));
      message.success(t("digitalEmployee.evolutionSaved"));
    } catch (error) {
      if (error instanceof Error && "errorFields" in error) {
        return;
      }
      console.error("Failed to save evolution config:", error);
      message.error(t("digitalEmployee.saveFailed"));
    } finally {
      setSavingEvolution(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>{t("digitalEmployee.title")}</h1>
        <p className={styles.description}>{t("digitalEmployee.description")}</p>
        <span className={styles.loading}>{t("common.loading")}</span>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>{t("digitalEmployee.title")}</h1>
          <p className={styles.description}>{t("digitalEmployee.description")}</p>
        </div>
        <Button onClick={loadAll}>{t("common.refresh")}</Button>
      </div>

      <Card className={styles.card}>
        <h3 className={styles.cardTitle}>{t("digitalEmployee.modelSlotsTitle")}</h3>
        <p className={styles.cardDescription}>
          {t("digitalEmployee.modelSlotsDescription")}
        </p>
        <Form layout="vertical" form={slotsForm}>
          <Form.Item
            name="auto_model_failover"
            label={t("digitalEmployee.autoModelFailover")}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <div className={styles.rowTwo}>
            <Form.Item
              name="primary_provider_id"
              label={t("digitalEmployee.primaryProvider")}
            >
              <Select
                allowClear
                options={providerOptions}
                onChange={() => slotsForm.setFieldValue("primary_model", undefined)}
              />
            </Form.Item>
            <Form.Item
              name="primary_model"
              label={t("digitalEmployee.primaryModel")}
            >
              <Select
                allowClear
                options={withCurrentModelOption(
                  primaryProviderId
                    ? modelOptionsByProvider.get(primaryProviderId) || []
                    : [],
                  primaryModel,
                )}
              />
            </Form.Item>
          </div>

          <div className={styles.rowTwo}>
            <Form.Item
              name="fallback_provider_id"
              label={t("digitalEmployee.fallbackProvider")}
            >
              <Select
                allowClear
                options={providerOptions}
                onChange={() =>
                  slotsForm.setFieldValue("fallback_model", undefined)
                }
              />
            </Form.Item>
            <Form.Item
              name="fallback_model"
              label={t("digitalEmployee.fallbackModel")}
            >
              <Select
                allowClear
                options={withCurrentModelOption(
                  fallbackProviderId
                    ? modelOptionsByProvider.get(fallbackProviderId) || []
                    : [],
                  fallbackModel,
                )}
              />
            </Form.Item>
          </div>

          <div className={styles.actions}>
            <Button
              onClick={() =>
                modelSlots && slotsForm.setFieldsValue(toModelFormValues(modelSlots))
              }
            >
              {t("common.reset")}
            </Button>
            <Button type="primary" loading={savingSlots} onClick={saveModelSlots}>
              {t("common.save")}
            </Button>
          </div>
          {slotsSaveFeedback === "success" ? (
            <div className={styles.feedbackSuccess}>
              {t("digitalEmployee.modelSlotsSaved")}
            </div>
          ) : null}
          {slotsSaveFeedback === "error" ? (
            <div className={styles.feedbackError}>
              {t("digitalEmployee.saveFailed")}
            </div>
          ) : null}
        </Form>
      </Card>

      <Card className={styles.card}>
        <h3 className={styles.cardTitle}>
          {t("digitalEmployee.triggerPolicyTitle")}
        </h3>
        <p className={styles.cardDescription}>
          {t("digitalEmployee.triggerPolicyDescription")}
        </p>
        <Form layout="vertical" form={triggerForm}>
          <div className={styles.rowThree}>
            <Form.Item
              name="enable_webhook"
              label={t("digitalEmployee.enableWebhook")}
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
            <Form.Item
              name="enable_poll"
              label={t("digitalEmployee.enablePoll")}
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
            <Form.Item
              name="block_private_network"
              label={t("digitalEmployee.blockPrivateNetwork")}
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </div>

          <Form.Item
            name="allowed_poll_domains_text"
            label={t("digitalEmployee.allowedPollDomains")}
            tooltip={t("digitalEmployee.allowedPollDomainsTooltip")}
          >
            <Input.TextArea
              rows={4}
              placeholder={t("digitalEmployee.allowedPollDomainsPlaceholder")}
            />
          </Form.Item>

          <div className={styles.actions}>
            <Button
              onClick={() =>
                triggerPolicy &&
                triggerForm.setFieldsValue(toTriggerFormValues(triggerPolicy))
              }
            >
              {t("common.reset")}
            </Button>
            <Button
              type="primary"
              loading={savingPolicy}
              onClick={saveTriggerPolicy}
            >
              {t("common.save")}
            </Button>
          </div>
        </Form>
      </Card>

      <Card className={styles.card}>
        <h3 className={styles.cardTitle}>{t("digitalEmployee.evolutionTitle")}</h3>
        <p className={styles.cardDescription}>
          {t("digitalEmployee.evolutionDescription")}
        </p>
        <Form layout="vertical" form={evolutionForm}>
          <div className={styles.rowThree}>
            <Form.Item
              name="enabled"
              label={t("digitalEmployee.evolutionEnabled")}
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>

            <Form.Item
              name="mode"
              label={t("digitalEmployee.evolutionMode")}
              rules={[{ required: true }]}
            >
              <Select
                options={[
                  {
                    value: "full_auto",
                    label: t("digitalEmployee.evolutionModeFullAuto"),
                  },
                  {
                    value: "manual",
                    label: t("digitalEmployee.evolutionModeManual"),
                  },
                ]}
              />
            </Form.Item>

            <Form.Item
              name="every"
              label={t("digitalEmployee.evolutionEvery")}
              rules={[{ required: true }]}
            >
              <Input placeholder="24h" />
            </Form.Item>
          </div>

          <div className={styles.rowThree}>
            <Form.Item
              name="query_file"
              label={t("digitalEmployee.evolutionQueryFile")}
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="timeout_seconds"
              label={t("digitalEmployee.evolutionTimeout")}
              rules={[{ required: true, type: "number", min: 30, max: 7200 }]}
            >
              <InputNumber min={30} max={7200} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              name="session_id"
              label={t("digitalEmployee.evolutionSessionId")}
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
          </div>

          <Form.Item
            name="user_id"
            label={t("digitalEmployee.evolutionUserId")}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>

          <div className={styles.actions}>
            <Button
              onClick={() =>
                evolutionConfig &&
                evolutionForm.setFieldsValue(toEvolutionFormValues(evolutionConfig))
              }
            >
              {t("common.reset")}
            </Button>
            <Button
              type="primary"
              loading={savingEvolution}
              onClick={saveEvolutionConfig}
            >
              {t("common.save")}
            </Button>
          </div>
        </Form>
      </Card>
    </div>
  );
}
