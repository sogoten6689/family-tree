import { Form, Input, InputNumber, Modal, Select } from "antd";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import {
  PIPELINE_SKIPPED_REASONS,
  PIPELINE_STEP_LABELS,
  type PipelineStep,
  type PipelineStepId,
  type PipelineStepStatus,
  type PipelineStepUpdatePayload,
} from "@/lib/pipelineApi";

type FormValues = {
  status: PipelineStepStatus;
  skipped_reason?: string | null;
  input_ref?: string | null;
  output_ref?: string | null;
  error_message?: string | null;
  document_id?: number;
  admin_note?: string | null;
};

type Props = {
  open: boolean;
  treeId: string;
  stepId: PipelineStepId;
  step?: PipelineStep | null;
  saving: boolean;
  onCancel: () => void;
  onSubmit: (payload: PipelineStepUpdatePayload) => Promise<void>;
};

const STATUS_OPTIONS: PipelineStepStatus[] = ["pending", "running", "done", "skipped", "error"];

export function PipelineStepEditForm({
  open,
  stepId,
  step,
  saving,
  onCancel,
  onSubmit,
}: Props) {
  const { t, i18n } = useTranslation();
  const [form] = Form.useForm<FormValues>();
  const lang = i18n.language.startsWith("en") ? "en" : "vi";
  const status = Form.useWatch("status", form);

  useEffect(() => {
    if (!open || !step) return;
    form.setFieldsValue({
      status: step.status,
      skipped_reason: step.skipped_reason ?? undefined,
      input_ref: step.input_ref ?? undefined,
      output_ref: step.output_ref ?? undefined,
      error_message: step.error_message ?? undefined,
      document_id: step.document_id || undefined,
      admin_note: step.admin_note ?? undefined,
    });
  }, [form, open, step]);

  const handleFinish = async (values: FormValues) => {
    const payload: PipelineStepUpdatePayload = {
      status: values.status,
      skipped_reason: values.status === "skipped" ? values.skipped_reason ?? "user_skip" : null,
      input_ref: values.input_ref ?? null,
      output_ref: values.output_ref ?? null,
      error_message: values.error_message ?? null,
      document_id: values.document_id ?? 0,
      admin_note: values.admin_note ?? null,
    };
    await onSubmit(payload);
  };

  return (
    <Modal
      open={open}
      title={t("pipeline.editStepTitle", {
        defaultValue: "Sửa bước: {{step}}",
        step: PIPELINE_STEP_LABELS[stepId][lang],
      })}
      okText={t("common.save", { defaultValue: "Lưu" })}
      cancelText={t("common.cancel", { defaultValue: "Hủy" })}
      confirmLoading={saving}
      onCancel={onCancel}
      onOk={() => void form.submit()}
      destroyOnClose
      width={560}
    >
      <Form form={form} layout="vertical" onFinish={(values) => void handleFinish(values)}>
        <Form.Item
          label={t("pipeline.fields.status", { defaultValue: "Trạng thái" })}
          name="status"
          rules={[{ required: true }]}
        >
          <Select
            options={STATUS_OPTIONS.map((value) => ({
              value,
              label: t(`pipeline.status.${value}`, { defaultValue: value }),
            }))}
          />
        </Form.Item>

        {status === "skipped" && (
          <Form.Item
            label={t("pipeline.fields.skippedReason", { defaultValue: "Lý do bỏ qua" })}
            name="skipped_reason"
            rules={[{ required: true, message: t("pipeline.skippedReasonRequired", { defaultValue: "Chọn lý do bỏ qua" }) }]}
          >
            <Select
              options={PIPELINE_SKIPPED_REASONS.map((item) => ({
                value: item.value,
                label: lang === "en" ? item.en : item.vi,
              }))}
            />
          </Form.Item>
        )}

        <Form.Item label={t("pipeline.fields.inputRef", { defaultValue: "Input ref" })} name="input_ref">
          <Input placeholder="documents:41" />
        </Form.Item>

        <Form.Item label={t("pipeline.fields.outputRef", { defaultValue: "Output ref" })} name="output_ref">
          <Input placeholder="documents:42 / nodes:74" />
        </Form.Item>

        <Form.Item label={t("pipeline.fields.documentId", { defaultValue: "Document ID" })} name="document_id">
          <InputNumber className="w-full" min={0} />
        </Form.Item>

        <Form.Item label={t("pipeline.fields.errorMessage", { defaultValue: "Thông báo lỗi" })} name="error_message">
          <Input.TextArea rows={3} />
        </Form.Item>

        <Form.Item label={t("pipeline.fields.adminNote", { defaultValue: "Ghi chú admin" })} name="admin_note">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
