import { useEffect, useState } from "react";
import { Card, Table, Typography, message } from "antd";
import { useTranslation } from "react-i18next";

import { listAdminHistory, type AdminHistoryItem } from "@/lib/userWorkspaceApi";

const AdminHistoryPage = () => {
  const { t } = useTranslation();
  const [items, setItems] = useState<AdminHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await listAdminHistory(100);
        setItems(data.items);
      } catch (err) {
        message.error(err instanceof Error ? err.message : "Không tải được lịch sử");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <Card>
      <Typography.Title level={4}>
        {t("adminHistory.title", { defaultValue: "Lịch sử scan & truy vấn" })}
      </Typography.Title>
      <Table
        rowKey="request_id"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: "Request ID", dataIndex: "request_id", width: 280 },
          {
            title: t("adminHistory.createdAt", { defaultValue: "Thời gian" }),
            dataIndex: "created_at",
            render: (value: string) => new Date(value).toLocaleString("vi-VN"),
          },
          { title: "Source", dataIndex: "source" },
          { title: "User ID", dataIndex: "user_id", render: (v: number | null) => v ?? "—" },
          { title: t("adminHistory.people", { defaultValue: "Người" }), dataIndex: "people_count" },
          { title: t("adminHistory.relationships", { defaultValue: "Quan hệ" }), dataIndex: "relationship_count" },
          { title: t("adminHistory.warnings", { defaultValue: "Cảnh báo" }), dataIndex: "warning_count" },
        ]}
      />
    </Card>
  );
};

export default AdminHistoryPage;
