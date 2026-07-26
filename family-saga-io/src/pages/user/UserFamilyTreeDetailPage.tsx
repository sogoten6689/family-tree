import { useEffect, useMemo, useState } from "react";
import { Button, Card, Empty, Spin, Tabs, Typography } from "antd";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { FamilyTreeVisualPanel } from "@/components/family-tree/FamilyTreeVisualPanel";
import { GenealogyFlowStepper } from "@/components/flow/GenealogyFlowStepper";
import { getUserFamilyTree } from "@/lib/userWorkspaceApi";
import type { FamilyTreeDocument } from "@/lib/familyTreeApi";
import { toFamilyMembers } from "@/lib/familyTreeUtils";
import type { GenealogyFlowStepId } from "@/lib/genealogyFlow";

const UserFamilyTreeDetailPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { treeId } = useParams<{ treeId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tree, setTree] = useState<FamilyTreeDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const activeTab = searchParams.get("tab") ?? "visual";

  useEffect(() => {
    if (!treeId) return;
    (async () => {
      setLoading(true);
      try {
        const data = await getUserFamilyTree(treeId);
        setTree(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Không tải được gia phả");
      } finally {
        setLoading(false);
      }
    })();
  }, [treeId]);

  const nodeCount = useMemo(() => tree?.nodes?.length ?? 0, [tree]);
  const members = useMemo(() => toFamilyMembers(tree?.nodes ?? []), [tree]);

  const completedSteps: GenealogyFlowStepId[] = ["material", "ocr", "extract", "canonical", "visual"];
  const currentStep: GenealogyFlowStepId = activeTab === "export" ? "export" : "visual";

  if (loading) return <Spin className="flex justify-center py-16" size="large" />;
  if (!tree || error) return <Empty description={error ?? "Không tải được gia phả"} />;

  return (
    <div className="space-y-4">
      <Card size="small" className="border-[hsl(var(--border))]">
        <GenealogyFlowStepper compact currentStep={currentStep} completedSteps={completedSteps} />
      </Card>

      <Card
        title={tree.name}
        extra={
          <Button onClick={() => navigate("/user/family-trees")}>
            {t("common.back", { defaultValue: "Quay lại" })}
          </Button>
        }
      >
        <Typography.Paragraph type="secondary">{tree.description}</Typography.Paragraph>
        <Typography.Text className="block mb-4">
          {t("familyTree.totalMembers", { defaultValue: "Thành viên" })}: {nodeCount}
        </Typography.Text>

        <Tabs
          activeKey={activeTab}
          onChange={(tab) => setSearchParams({ tab })}
          items={[
            {
              key: "visual",
              label: t("flow.step.visual", { defaultValue: "Xem sơ đồ" }),
              children:
                tree.nodes.length > 0 ? (
                  <FamilyTreeVisualPanel nodes={tree.nodes} treeName={tree.name} members={members} />
                ) : (
                  <Empty description={t("familyTree.emptyTree", { defaultValue: "Cây này chưa có node nào" })} />
                ),
            },
            {
              key: "export",
              label: t("flow.step.export", { defaultValue: "Xuất / chia sẻ" }),
              children: (
                <Typography.Paragraph type="secondary">
                  {t("userFamilyTrees.exportHint", {
                    defaultValue:
                      "Dùng nút Export trên thanh công cụ sơ đồ (tab Sơ đồ) để tải JSON, CSV hoặc GEDCOM.",
                  })}
                </Typography.Paragraph>
              ),
            },
            {
              key: "edit",
              label: t("flow.step.canonical", { defaultValue: "Chuẩn hóa & lưu" }),
              children: (
                <Typography.Paragraph>
                  {t("userFamilyTrees.editHint", {
                    defaultValue: "Cây đã lưu trên server. Chỉnh sửa node chi tiết sẽ bổ sung trong bản cập nhật tiếp.",
                  })}
                </Typography.Paragraph>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default UserFamilyTreeDetailPage;
