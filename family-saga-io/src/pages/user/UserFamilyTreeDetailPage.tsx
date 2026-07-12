import { useEffect, useMemo, useState } from "react";
import { Button, Card, Col, Empty, Row, Spin, Typography } from "antd";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { FamilyTreeVisualPanel } from "@/components/family-tree/FamilyTreeVisualPanel";
import { getUserFamilyTree } from "@/lib/userWorkspaceApi";
import type { FamilyTreeDocument } from "@/lib/familyTreeApi";
import { toFamilyMembers } from "@/lib/familyTreeUtils";

const UserFamilyTreeDetailPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { treeId } = useParams<{ treeId: string }>();
  const [tree, setTree] = useState<FamilyTreeDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!treeId) return;
    (async () => {
      setLoading(true);
      try {
        const data = await getUserFamilyTree(treeId);
        setTree(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Không tải được gia phả");
      } finally {
        setLoading(false);
      }
    })();
  }, [treeId]);

  const nodeCount = useMemo(() => tree?.nodes?.length ?? 0, [tree]);
  const members = useMemo(() => toFamilyMembers(tree?.nodes ?? []), [tree]);

  if (loading) return <Spin className="flex justify-center py-16" size="large" />;
  if (!tree || error) return <Empty description={error ?? "Không tải được gia phả"} />;

  return (
    <Card
      title={tree.name}
      extra={
        <Button onClick={() => navigate("/user/family-trees")}>
          {t("common.back", { defaultValue: "Quay lại" })}
        </Button>
      }
    >
      <Typography.Paragraph type="secondary">{tree.description}</Typography.Paragraph>
      <Row gutter={16} className="mb-4">
        <Col><Typography.Text>{t("familyTree.totalMembers", { defaultValue: "Thành viên" })}: {nodeCount}</Typography.Text></Col>
      </Row>
      {tree.nodes.length > 0 ? (
        <FamilyTreeVisualPanel nodes={tree.nodes} treeName={tree.name} members={members} />
      ) : (
        <Empty description={t("familyTree.emptyTree", { defaultValue: "Cây này chưa có node nào" })} />
      )}
    </Card>
  );
};

export default UserFamilyTreeDetailPage;
