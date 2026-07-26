import { useEffect, useState } from "react";
import { Button, Card, Col, Row, Statistic, Typography } from "antd";
import { EyeOutlined } from "@ant-design/icons";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { PageState } from "@/components/ui/PageState";
import { listPublicFamilyTrees } from "@/lib/publicFamilyTreeApi";
import type { FamilyTreeSummary } from "@/lib/familyTreeApi";

const PublicFamilyTreeListPage = () => {
  const { t } = useTranslation();
  const [items, setItems] = useState<FamilyTreeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listPublicFamilyTrees();
      setItems(data.items);
    } catch (err) {
      setItems([]);
      setError(err instanceof Error ? err.message : "Không tải được danh sách gia phả");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="max-w-6xl mx-auto py-8 md:py-10 px-4 sm:px-6">
      <Typography.Title level={2} className="!text-2xl sm:!text-3xl">
        {t("publicFamilyTrees.title", { defaultValue: "Gia phả mẫu công khai" })}
      </Typography.Title>
      <Typography.Paragraph type="secondary" className="!mb-6">
        {t("publicFamilyTrees.subtitle", {
          defaultValue: "Khám phá các cây gia phả được chia sẻ công khai và tài liệu Hán-Nôm đi kèm.",
        })}
      </Typography.Paragraph>

      <PageState
        loading={loading}
        error={error}
        onRetry={load}
        empty={!loading && !error && items.length === 0}
        emptyDescription={t("publicFamilyTrees.empty", { defaultValue: "Chưa có gia phả công khai." })}
      >
        <Row gutter={[16, 16]}>
          {items.map((tree) => (
            <Col xs={24} sm={12} lg={8} key={tree.id}>
              <Card
                hoverable
                title={tree.name}
                actions={[
                  <Link key="view" to={`/gia-pha/${tree.id}`}>
                    <Button type="link" icon={<EyeOutlined />}>
                      {t("publicFamilyTrees.viewDetail", { defaultValue: "Xem chi tiết" })}
                    </Button>
                  </Link>,
                ]}
              >
                <Typography.Paragraph ellipsis={{ rows: 2 }} type="secondary">
                  {tree.description || t("publicFamilyTrees.noDescription", { defaultValue: "Chưa có mô tả" })}
                </Typography.Paragraph>
                <Row gutter={12}>
                  <Col span={12}>
                    <Statistic
                      title={t("familyTree.totalMembers", { defaultValue: "Thành viên" })}
                      value={tree.node_count}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title={t("familyTree.generations", { defaultValue: "Thế hệ" })}
                      value={tree.generation_count ?? 0}
                    />
                  </Col>
                </Row>
              </Card>
            </Col>
          ))}
        </Row>
      </PageState>
    </div>
  );
};

export default PublicFamilyTreeListPage;
