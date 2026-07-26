import { Tag } from "antd";
import { useTranslation } from "react-i18next";

import type { OcrStatus, TreeStatus } from "@/lib/userWorkspaceApi";

const OCR_COLORS: Record<OcrStatus, string> = {
  pending: "default",
  processing: "processing",
  completed: "success",
  failed: "error",
  skipped: "warning",
};

const TREE_COLORS: Record<TreeStatus, string> = {
  none: "default",
  draft: "processing",
  created: "success",
};

export function OcrStatusTag({ status }: { status: OcrStatus }) {
  const { t } = useTranslation();
  return (
    <Tag color={OCR_COLORS[status] ?? "default"}>
      {t(`userDocuments.ocrStatus.${status}`, { defaultValue: status })}
    </Tag>
  );
}

export function TreeStatusTag({ status }: { status: TreeStatus }) {
  const { t } = useTranslation();
  return (
    <Tag color={TREE_COLORS[status] ?? "default"}>
      {t(`userDocuments.treeStatus.${status}`, { defaultValue: status })}
    </Tag>
  );
}
