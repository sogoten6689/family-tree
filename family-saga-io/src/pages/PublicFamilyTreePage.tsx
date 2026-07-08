import { useEffect, useMemo, useState } from "react";
import { Button, Card, Col, Empty, Row, Spin, Statistic, Table, Tabs, Tag, Typography } from "antd";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { BalkanFamilyTreeView } from "@/components/BalkanFamilyTreeView";
import { FamilyTreeAncestralSidebar } from "@/components/family-tree/FamilyTreeAncestralSidebar";
import { FamilyTreeMembersTable } from "@/components/family-tree/FamilyTreeMembersTable";
import { getPublicFamilyTree, listPublicFamilyTreeDocuments } from "@/lib/publicFamilyTreeApi";
import type { FamilyTreeDocument } from "@/lib/familyTreeApi";
import type { FamilyTreeSourceDocument } from "@/types/document";
import { toFamilyMembers, toTreeStats } from "@/lib/familyTreeUtils";

const PublicFamilyTreePage = () => {
  const { t } = useTranslation();
  const { treeId } = useParams<{ treeId: string }>();
  const [tree, setTree] = useState<FamilyTreeDocument | null>(null);
  const [documents, setDocuments] = useState<FamilyTreeSourceDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!treeId) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [treeData, docsData] = await Promise.all([
          getPublicFamilyTree(treeId),
          listPublicFamilyTreeDocuments(treeId).catch(() => ({ total: 0, items: [] })),
        ]);
        setTree(treeData);
        setDocuments(docsData.items);
      } catch (err) {
        setTree(null);
        setDocuments([]);
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
              title={t("familyTree.totalMembers", { defaultValue: "Thành viên" })}
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
                {
                  key: "documents",
                  label: t("familyTree.documentsTab", { defaultValue: "Tài liệu Hán-Nôm" }),
                  children: (
                    <Table
                      rowKey="id"
                      dataSource={documents}
                      pagination={false}
                      locale={{ emptyText: t("publicFamilyTrees.noDocuments", { defaultValue: "Chưa có tài liệu công khai." }) }}
                      columns={[
                        {
                          title: t("documents.title", { defaultValue: "Tiêu đề" }),
                          dataIndex: "title",
                        },
                        {
                          title: t("documents.type", { defaultValue: "Loại" }),
                          dataIndex: "type",
                        },
                        {
                          title: t("documents.files", { defaultValue: "Files" }),
                          render: (_, record) => record.files?.length ?? 0,
                        },
                        {
                          title: t("auth.actions", { defaultValue: "Thao tác" }),
                          render: (_, record) =>
                            record.files?.[0]?.download_url ? (
                              <Button type="link" href={record.files[0].download_url} target="_blank" rel="noreferrer">
                                {t("documents.download", { defaultValue: "Tải xuống" })}
                              </Button>
                            ) : (
                              "—"
                            ),
                        },
                      ]}
                    />
                  ),
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
