import { useEffect, useMemo, useState } from "react";
import { Card, Col, Empty, Row, Spin, Statistic, Tabs, Tag, Typography } from "antd";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { BalkanFamilyTreeView } from "@/components/BalkanFamilyTreeView";
import { FamilyTreeAncestralSidebar } from "@/components/family-tree/FamilyTreeAncestralSidebar";
import { FamilyTreeMembersTable } from "@/components/family-tree/FamilyTreeMembersTable";
import { getFamilyTree, type FamilyTreeDocument } from "@/lib/familyTreeApi";
import { toFamilyMembers, toTreeStats } from "@/lib/familyTreeUtils";

const PublicFamilyTreePage = () => {
  const { t } = useTranslation();
  const { treeId } = useParams<{ treeId: string }>();
  const [tree, setTree] = useState<FamilyTreeDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!treeId) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getFamilyTree(treeId);
        setTree(data);
      } catch (err) {
        setTree(null);
        setError(err instanceof Error ? err.message : "Không tải được gia phả");
      } finally {
        setLoading(false);
      }
    })();
  }, [treeId]);

  const members = useMemo(() => toFamilyMembers(tree?.nodes ?? []), [tree]);
  const stats = useMemo(() => toTreeStats(tree?.nodes ?? []), [tree]);

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Spin size="large" tip={t("familyTree.loadingTreeDetail", { defaultValue: "Đang tải chi tiết cây..." })} />
      </div>
    );
  }

  if (!tree || error) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-6">
        <Empty description={error ?? t("familyTree.treeDetailLoadFailed", { defaultValue: "Không tải được chi tiết cây" })} />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-6">
      <div className="mb-6">
        <Typography.Title level={2} className="!mb-2">
          {tree.name}
        </Typography.Title>
        <Tag color="green">{t("familyTree.statusPublic", { defaultValue: "Công khai" })}</Tag>
      </div>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={t("familyTree.totalMembers", { defaultValue: "Tổng thành viên" })}
              value={stats.totalMembers}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={t("familyTree.totalGenerations", { defaultValue: "Số đời" })}
              value={stats.totalGenerations}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={t("familyTree.establishedYear", { defaultValue: "Năm ghi nhận sớm nhất" })}
              value={stats.established || "—"}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={17}>
          <Card>
            <Tabs
              defaultActiveKey="visual"
              items={[
                {
                  key: "visual",
                  label: t("familyTree.visualTreeTab", { defaultValue: "Sơ đồ Gia phả" }),
                  children:
                    tree.nodes.length > 0 ? (
                      <BalkanFamilyTreeView key={tree.id} treeId={tree.id} nodes={tree.nodes} height={560} />
                    ) : (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description={t("familyTree.emptyTree", { defaultValue: "Cây này chưa có node nào" })}
                      />
                    ),
                },
                {
                  key: "members",
                  label: t("familyTree.memberDirectoryTab", { defaultValue: "Hồ sơ Thành viên" }),
                  children: <FamilyTreeMembersTable members={members} />,
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={7}>
          <FamilyTreeAncestralSidebar tree={tree} establishedYear={stats.established} />
        </Col>
      </Row>
    </div>
  );
};

export default PublicFamilyTreePage;
