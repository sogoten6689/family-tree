import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Col, Row, Skeleton, Space, Typography } from "antd";
import { FileSearchOutlined, HistoryOutlined, NodeIndexOutlined, SettingOutlined, TeamOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { FlowNextBanner } from "@/components/flow/FlowNextBanner";
import { GenealogyFlowStepper } from "@/components/flow/GenealogyFlowStepper";
import { QuickStartCards } from "@/components/flow/QuickStartCards";
import { GiaPhaSummaryCards, StatTile } from "@/components/gia-pha/GiaPhaSummaryCards";
import { useAuth } from "@/contexts/AuthContext";
import { computeFlowProgress } from "@/lib/flowProgress";
import { getUserStats, listUserDocuments } from "@/lib/userWorkspaceApi";

const STALE_MS = 30_000; // cache phía trình duyệt (server cũng cache 30 giây)

const DashboardPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();

  // Số liệu cá nhân + danh sách tài liệu (để tính bước tiếp theo của quy trình); cache theo người dùng.
  const { data, isLoading: statsLoading } = useQuery({
    queryKey: ["user-dashboard", user?.id],
    queryFn: async () => {
      const [stats, docs] = await Promise.all([getUserStats(), listUserDocuments()]);
      return { stats, scans: docs.items };
    },
    staleTime: STALE_MS,
  });
  const stats = data?.stats ?? { scanned_documents: 0, family_trees: 0, history_total: 0 };
  const scans = data?.scans ?? [];
  const flow = useMemo(() => computeFlowProgress(stats, scans), [stats, scans]);

  const personal = [
    { icon: <FileSearchOutlined />, label: t("dashboard.scannedDocs", { defaultValue: "Tài liệu đã scan" }), value: stats.scanned_documents },
    { icon: <NodeIndexOutlined />, label: t("dashboard.familyTrees", { defaultValue: "Cây gia phả đã tạo" }), value: stats.family_trees },
    { icon: <HistoryOutlined />, label: t("dashboard.historyTotal", { defaultValue: "Lịch sử truy vấn" }), value: stats.history_total },
  ];

  return (
    <div className="space-y-6">
      <section className="brand-gradient rounded-2xl px-6 py-7 shadow-sm">
        <Typography.Title level={3} className="!mb-1 !text-white">
          {t("auth.welcomeUser", { defaultValue: "Xin chào, {{name}}", name: user?.full_name ?? user?.email })}
        </Typography.Title>
        <Typography.Paragraph className="!mb-0 !text-white/85">
          {t("flow.dashboardIntro", { defaultValue: "Theo dõi tiến độ xử lý tư liệu → OCR → trích xuất → cây gia phả." })}
        </Typography.Paragraph>
      </section>

      {flow.nextStep && !statsLoading && (
        <FlowNextBanner
          message={t(`flow.stepDesc.${flow.nextStep}`, { defaultValue: "" })}
          nextLabel={t("flow.continueStep", {
            defaultValue: "Tiếp tục: {{step}}",
            step: t(`flow.step.${flow.nextStep}`, { defaultValue: flow.nextStep }),
          })}
          nextHref={flow.nextRoute}
        />
      )}

      <div>
        <Typography.Title level={5} className="!mb-3">
          {t("dashboard.summaryTitle", { defaultValue: "Thống kê Gia phả" })}
        </Typography.Title>
        <GiaPhaSummaryCards />
      </div>

      <div>
        <Typography.Title level={5} className="!mb-3">
          {t("dashboard.activityTitle", { defaultValue: "Hoạt động của bạn" })}
        </Typography.Title>
        <Row gutter={[16, 16]}>
          {personal.map((item) => (
            <Col xs={12} md={8} key={item.label}>
              {statsLoading ? (
                <Card size="small"><Skeleton active avatar paragraph={{ rows: 1 }} title={false} /></Card>
              ) : (
                <StatTile icon={item.icon} label={item.label} value={item.value.toLocaleString("vi-VN")} />
              )}
            </Col>
          ))}
        </Row>
      </div>

      <Card title={t("flow.stepperTitle", { defaultValue: "Quy trình xử lý gia phả" })} className="border-[hsl(var(--border))]">
        <GenealogyFlowStepper currentStep={flow.currentStep} completedSteps={flow.completedSteps} />
      </Card>

      <QuickStartCards />

      {isAdmin && (
        <Card title={t("admin.zoneTitle", { defaultValue: "Quản trị" })}>
          <Space wrap>
            <Button icon={<SettingOutlined />} onClick={() => navigate("/admin/gia-pha")}>
              {t("admin.menuFamilyTrees", { defaultValue: "Quản lý gia phả" })}
            </Button>
            <Button icon={<TeamOutlined />} onClick={() => navigate("/admin/users")}>
              {t("admin.menuUsers", { defaultValue: "Quản lý thành viên" })}
            </Button>
          </Space>
        </Card>
      )}
    </div>
  );
};

export default DashboardPage;
