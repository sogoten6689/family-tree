import { Card, Timeline, Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { FamilyTreeDocument } from "@/lib/familyTreeApi";
import { formatTreeDate } from "@/lib/familyTreeUtils";

type Props = {
  tree: FamilyTreeDocument;
  establishedYear: number;
};

export function FamilyTreeAncestralSidebar({ tree, establishedYear }: Props) {
  const { t } = useTranslation();

  const timelineItems = [
    establishedYear > 0
      ? {
          children: t("familyTree.established", {
            defaultValue: "Thành lập: {{year}}",
            year: establishedYear,
          }),
        }
      : null,
    {
      children: `${t("familyTree.createdAt", { defaultValue: "Ngày tạo" })}: ${formatTreeDate(tree.created_at)}`,
    },
    {
      children: `${t("familyTree.updatedAt", { defaultValue: "Cập nhật" })}: ${formatTreeDate(tree.updated_at)}`,
    },
  ].filter(Boolean) as { children: React.ReactNode }[];

  return (
    <Card
      title={t("familyTree.ancestralSidebarTitle", {
        defaultValue: "Thông tin Từ đường / Lịch sử",
      })}
      className="h-full"
    >
      <Typography.Paragraph type="secondary">
        {tree.description?.trim() ||
          t("familyTree.noHistorySummary", {
            defaultValue: "Chưa có mô tả lịch sử dòng họ.",
          })}
      </Typography.Paragraph>

      <Typography.Title level={5} className="!mt-4 !mb-3">
        {t("familyTree.timelineTitle", { defaultValue: "Mốc thời gian" })}
      </Typography.Title>
      <Timeline items={timelineItems} />

      <Typography.Title level={5} className="!mt-4 !mb-2">
        {t("familyTree.managerContact", { defaultValue: "Người quản lý" })}
      </Typography.Title>
      <Typography.Text type="secondary">
        {t("familyTree.managerContactPlaceholder", {
          defaultValue: "Thông tin liên hệ sẽ được cập nhật sau.",
        })}
      </Typography.Text>
    </Card>
  );
}
