import { useEffect, useState } from "react";
import { Button, Card, Col, Row, Skeleton, Space, Statistic, Typography } from "antd";
import { SettingOutlined, TeamOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { GenealogyFlowStepper } from "@/components/flow/GenealogyFlowStepper";
import { QuickStartCards } from "@/components/flow/QuickStartCards";
import { useAuth } from "@/contexts/AuthContext";
import type { GenealogyFlowStepId } from "@/lib/genealogyFlow";
import { getUserStats } from "@/lib/userWorkspaceApi";

const DashboardPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const [stats, setStats] = useState({ scanned_documents: 0, family_trees: 0, history_total: 0 });
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    setStatsLoading(true);
    getUserStats()
      .then(setStats)
      .catch(() => setStats({ scanned_documents: 0, family_trees: 0, history_total: 0 }))
      .finally(() => setStatsLoading(false));
  }, []);

  const completedSteps: GenealogyFlowStepId[] =
    stats.scanned_documents > 0
      ? stats.family_trees > 0
        ? ["material", "ocr", "extract", "canonical", "visual"]
        : ["material"]
      : [];

  const currentStep: GenealogyFlowStepId =
    stats.family_trees > 0 ? "visual" : stats.scanned_documents > 0 ? "ocr" : "material";

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <Card className="border-[hsl(var(--border))]">
        <Typography.Title level={4} className="!mb-1">
          {t("auth.welcomeUser", {
            defaultValue: "Xin chào, {{name}}",
            name: user?.full_name ?? user?.email,
          })}
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="!mb-0">
          {t("flow.dashboardIntro", {
            defaultValue: "Theo dõi tiến độ xử lý tư liệu → OCR → trích xuất → cây gia phả.",
          })}
        </Typography.Paragraph>
      </Card>

      <Card
        title={t("flow.stepperTitle", { defaultValue: "Quy trình xử lý gia phả" })}
        className="border-[hsl(var(--border))]"
      >
        <GenealogyFlowStepper currentStep={currentStep} completedSteps={completedSteps} />
      </Card>

      <QuickStartCards />

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            {statsLoading ? (
              <Skeleton active paragraph={false} />
            ) : (
              <Statistic
                title={t("dashboard.scannedDocs", { defaultValue: "Tài liệu đã scan" })}
                value={stats.scanned_documents}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            {statsLoading ? (
              <Skeleton active paragraph={false} />
            ) : (
              <Statistic
                title={t("dashboard.familyTrees", { defaultValue: "Cây gia phả đã tạo" })}
                value={stats.family_trees}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            {statsLoading ? (
              <Skeleton active paragraph={false} />
            ) : (
              <Statistic
                title={t("dashboard.historyTotal", { defaultValue: "Lịch sử truy vấn" })}
                value={stats.history_total}
              />
            )}
          </Card>
        </Col>
      </Row>

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
