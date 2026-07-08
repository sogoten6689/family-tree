import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Typography } from "antd";
import { useTranslation } from "react-i18next";

import { PageState } from "@/components/ui/PageState";
import { getAdminStats, type AdminStats } from "@/lib/userWorkspaceApi";

const AdminDashboardPage = () => {
  const { t } = useTranslation();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminStats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được thống kê");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const statCards = [
    { title: t("adminDashboard.totalTrees", { defaultValue: "Tổng cây gia phả" }), value: stats?.total_trees ?? 0 },
    { title: t("adminDashboard.publicTrees", { defaultValue: "Gia phả công khai" }), value: stats?.public_trees ?? 0 },
    { title: t("adminDashboard.totalUsers", { defaultValue: "Người dùng" }), value: stats?.total_users ?? 0 },
    { title: t("adminDashboard.totalScans", { defaultValue: "Tài liệu đã scan" }), value: stats?.total_scans ?? 0 },
    { title: t("adminDashboard.historyTotal", { defaultValue: "Lịch sử truy vấn" }), value: stats?.history_total ?? 0 },
  ];

  return (
    <div className="space-y-6">
      <Typography.Title level={3}>
        {t("adminDashboard.title", { defaultValue: "Dashboard quản trị" })}
      </Typography.Title>

      <PageState loading={loading} error={error} onRetry={load}>
        <Row gutter={[16, 16]}>
          {statCards.map((item) => (
            <Col xs={24} sm={12} md={8} key={item.title}>
              <Card>
                <Statistic title={item.title} value={item.value} />
              </Card>
            </Col>
          ))}
        </Row>
      </PageState>
    </div>
  );
};

export default AdminDashboardPage;
