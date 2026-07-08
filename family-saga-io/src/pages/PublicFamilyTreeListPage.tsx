import { useEffect, useState } from "react";
import { Button, Card, Col, Empty, Row, Spin, Statistic, Tag, Typography } from "antd";
import { EyeOutlined } from "@ant-design/icons";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { listPublicFamilyTrees } from "@/lib/publicFamilyTreeApi";
import type { FamilyTreeSummary } from "@/lib/familyTreeApi";

const PublicFamilyTreeListPage = () => {
  const { t } = useTranslation();
  const [items, setItems] = useState<FamilyTreeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
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
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-10 px-6">
      <Typography.Title level={2}>
        {t("publicFamilyTrees.title", { defaultValue: "Gia phả mẫu công khai" })}
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        {t("publicFamilyTrees.subtitle", {
          defaultValue: "Khám phá các cây gia phả được chia sẻ công khai và tài liệu Hán-Nôm đi kèm.",
        })}
      </Typography.Paragraph>

      {error && <Empty className="my-8" description={error} />}
      {!error && items.length === 0 && (
        <Empty
          className="my-8"
          description={t("publicFamilyTrees.empty", { defaultValue: "Chưa có gia phả công khai." })}
        />
      )}

      <Row gutter={[16, 16]} className="mt-6">
        {items.map((tree) => (
          <Col xs={24} md={12} lg={8} key={tree.id}>
            <Card
              hoverable
              title={tree.name}
              extra={<Tag color="blue">{tree.id}</Tag>}
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
    </div>
  );
};

export default PublicFamilyTreeListPage;
