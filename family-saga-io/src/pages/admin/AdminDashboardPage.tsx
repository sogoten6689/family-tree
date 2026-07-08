import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Typography, message } from "antd";
import { useTranslation } from "react-i18next";

import { getAdminStats, type AdminStats } from "@/lib/userWorkspaceApi";

const AdminDashboardPage = () => {
  const { t } = useTranslation();
  const [stats, setStats] = useState<AdminStats | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getAdminStats();
        setStats(data);
      } catch (err) {
        message.error(err instanceof Error ? err.message : "Không tải được thống kê");
      }
    })();
  }, []);

  return (
    <div className="space-y-6">
      <Typography.Title level={3}>
        {t("adminDashboard.title", { defaultValue: "Dashboard quản trị" })}
      </Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card><Statistic title={t("adminDashboard.totalTrees", { defaultValue: "Tổng cây gia phả" })} value={stats?.total_trees ?? 0} /></Card>
        </Col>
        <Col xs={24} md={8}>
          <Card><Statistic title={t("adminDashboard.publicTrees", { defaultValue: "Gia phả công khai" })} value={stats?.public_trees ?? 0} /></Card>
        </Col>
        <Col xs={24} md={8}>
          <Card><Statistic title={t("adminDashboard.totalUsers", { defaultValue: "Người dùng" })} value={stats?.total_users ?? 0} /></Card>
        </Col>
        <Col xs={24} md={8}>
          <Card><Statistic title={t("adminDashboard.totalScans", { defaultValue: "Tài liệu đã scan" })} value={stats?.total_scans ?? 0} /></Card>
        </Col>
        <Col xs={24} md={8}>
          <Card><Statistic title={t("adminDashboard.historyTotal", { defaultValue: "Lịch sử truy vấn" })} value={stats?.history_total ?? 0} /></Card>
        </Col>
      </Row>
    </div>
  );
};

export default AdminDashboardPage;
