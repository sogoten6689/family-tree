import { useEffect, useState } from "react";
import { Button, Card, Space, Table, Typography, message } from "antd";
import { EyeOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { listUserFamilyTrees } from "@/lib/userWorkspaceApi";
import type { FamilyTreeSummary } from "@/lib/familyTreeApi";

const UserFamilyTreesPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [items, setItems] = useState<FamilyTreeSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await listUserFamilyTrees();
        setItems(data.items);
      } catch (err) {
        message.error(err instanceof Error ? err.message : "Không tải được danh sách gia phả");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <Card>
      <Space className="w-full justify-between mb-4">
        <Typography.Title level={4} className="!mb-0">
          {t("userFamilyTrees.title", { defaultValue: "Gia phả đã tạo" })}
        </Typography.Title>
        <Button type="primary" onClick={() => navigate("/user/document-reader")}>
          {t("userFamilyTrees.createNew", { defaultValue: "Tạo từ tài liệu" })}
        </Button>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 10 }}
        columns={[
          { title: "STT", width: 70, render: (_, __, index) => index + 1 },
          { title: t("familyTree.treeName", { defaultValue: "Tên gia phả" }), dataIndex: "name" },
          {
            title: t("userFamilyTrees.sourceDoc", { defaultValue: "Tài liệu nguồn" }),
            dataIndex: "source_document_title",
            render: (value: string | null | undefined) => value ?? "—",
          },
          { title: t("familyTree.totalMembers", { defaultValue: "Số thành viên" }), dataIndex: "node_count" },
          {
            title: t("familyTree.generations", { defaultValue: "Số thế hệ" }),
            dataIndex: "generation_count",
            render: (value: number | undefined) => value ?? 0,
          },
          {
            title: t("familyTree.createdAt", { defaultValue: "Ngày tạo" }),
            dataIndex: "created_at",
            render: (value: string) => new Date(value).toLocaleDateString("vi-VN"),
          },
          {
            title: t("familyTree.updatedAt", { defaultValue: "Ngày cập nhật" }),
            dataIndex: "updated_at",
            render: (value: string) => new Date(value).toLocaleDateString("vi-VN"),
          },
          {
            title: t("auth.actions", { defaultValue: "Thao tác" }),
            render: (_, record) => (
              <Button icon={<EyeOutlined />} onClick={() => navigate(`/user/family-trees/${record.id}`)}>
                {t("userFamilyTrees.view", { defaultValue: "Xem" })}
              </Button>
            ),
          },
        ]}
      />
    </Card>
  );
};

export default UserFamilyTreesPage;
