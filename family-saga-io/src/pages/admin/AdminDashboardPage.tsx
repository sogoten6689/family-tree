import { useQuery } from "@tanstack/react-query";
import { Col, Row, Typography } from "antd";
import { DatabaseOutlined, FileSearchOutlined, GlobalOutlined, HistoryOutlined, NodeIndexOutlined, TeamOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

import { GiaPhaSummaryCards, StatTile } from "@/components/gia-pha/GiaPhaSummaryCards";
import { PageState } from "@/components/ui/PageState";
import { getAdminStats } from "@/lib/userWorkspaceApi";

const STALE_MS = 30_000; // cache phía trình duyệt (server cũng cache 30 giây)

const AdminDashboardPage = () => {
  const { t } = useTranslation();
  const { data: stats, isLoading, error, refetch } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: getAdminStats,
    staleTime: STALE_MS,
  });

  const cards = [
    { icon: <NodeIndexOutlined />, label: t("adminDashboard.totalTrees", { defaultValue: "Tổng cây gia phả" }), value: stats?.total_trees ?? 0 },
    { icon: <GlobalOutlined />, label: t("adminDashboard.publicTrees", { defaultValue: "Gia phả công khai" }), value: stats?.public_trees ?? 0 },
    { icon: <TeamOutlined />, label: t("adminDashboard.totalUsers", { defaultValue: "Người dùng" }), value: stats?.total_users ?? 0 },
    { icon: <FileSearchOutlined />, label: t("adminDashboard.totalScans", { defaultValue: "Tài liệu đã scan" }), value: stats?.total_scans ?? 0 },
    { icon: <HistoryOutlined />, label: t("adminDashboard.historyTotal", { defaultValue: "Lịch sử truy vấn" }), value: stats?.history_total ?? 0 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <DatabaseOutlined className="text-2xl text-primary" aria-hidden />
        <Typography.Title level={3} className="!mb-0">
          {t("adminDashboard.title", { defaultValue: "Dashboard quản trị" })}
        </Typography.Title>
      </div>

      <div>
        <Typography.Title level={5} className="!mb-3">
          {t("dashboard.summaryTitle", { defaultValue: "Thống kê Gia phả" })}
        </Typography.Title>
        <GiaPhaSummaryCards />
      </div>

      <div>
        <Typography.Title level={5} className="!mb-3">
          {t("adminDashboard.systemTitle", { defaultValue: "Toàn hệ thống" })}
        </Typography.Title>
        <PageState
          loading={isLoading}
          error={error ? (error instanceof Error ? error.message : "Không tải được thống kê") : null}
          onRetry={() => void refetch()}
        >
          <Row gutter={[16, 16]}>
            {cards.map((item) => (
              <Col xs={24} sm={12} lg={8} key={item.label}>
                <StatTile icon={item.icon} label={item.label} value={item.value.toLocaleString("vi-VN")} />
              </Col>
            ))}
          </Row>
        </PageState>
      </div>
    </div>
  );
};

export default AdminDashboardPage;
