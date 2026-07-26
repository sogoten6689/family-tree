import {
  ExportOutlined,
  EyeOutlined,
  FileSearchOutlined,
  LockOutlined,
  ReadOutlined,
  SaveOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Button, Card, Col, Row, Table, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { GenealogyFlowStepper } from "@/components/flow/GenealogyFlowStepper";
import { ADMIN_PAGES, APP_PAGES, PUBLIC_PAGES, USER_PAGES, type AppPageMeta } from "@/config/pages";
import { GENEALOGY_FLOW_STEPS, GENEALOGY_FLOW_ROUTES, type GenealogyFlowStepId } from "@/lib/genealogyFlow";

const zoneColors: Record<AppPageMeta["zone"], string> = {
  public: "blue",
  user: "green",
  admin: "gold",
};

const FLOW_STEP_ICONS: Record<GenealogyFlowStepId, React.ReactNode> = {
  material: <ReadOutlined />,
  ocr: <FileSearchOutlined />,
  extract: <TeamOutlined />,
  canonical: <SaveOutlined />,
  visual: <EyeOutlined />,
  export: <ExportOutlined />,
};

const GuidePage = () => {
  const { t } = useTranslation();

  const columns = [
    {
      title: t("guide.colPage", { defaultValue: "Trang" }),
      dataIndex: "titleKey",
      render: (titleKey: string, record: AppPageMeta) => (
        <Link to={record.path}>{t(titleKey, { defaultValue: record.id })}</Link>
      ),
    },
    {
      title: t("guide.colPath", { defaultValue: "Đường dẫn" }),
      dataIndex: "path",
      render: (path: string) => <Typography.Text code>{path}</Typography.Text>,
    },
    {
      title: t("guide.colZone", { defaultValue: "Khu vực" }),
      dataIndex: "zone",
      render: (zone: AppPageMeta["zone"]) => (
        <Tag color={zoneColors[zone]}>{t(`guide.zone.${zone}`, { defaultValue: zone })}</Tag>
      ),
    },
    {
      title: t("guide.colAccess", { defaultValue: "Quyền truy cập" }),
      render: (_: unknown, record: AppPageMeta) => {
        if (record.requiresAdmin) {
          return (
            <Tag icon={<TeamOutlined />} color="gold">
              {t("guide.accessAdmin", { defaultValue: "Admin" })}
            </Tag>
          );
        }
        if (record.requiresAuth) {
          return (
            <Tag icon={<UserOutlined />} color="green">
              {t("guide.accessUser", { defaultValue: "Đã đăng nhập" })}
            </Tag>
          );
        }
        return (
          <Tag icon={<ReadOutlined />} color="blue">
            {t("guide.accessPublic", { defaultValue: "Công khai" })}
          </Tag>
        );
      },
    },
    {
      title: t("guide.colDesc", { defaultValue: "Mô tả" }),
      dataIndex: "descKey",
      render: (descKey: string) => t(descKey, { defaultValue: "—" }),
    },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <Typography.Title level={2}>
        {t("guide.pageTitle", { defaultValue: "Hướng dẫn sử dụng" })}
      </Typography.Title>
      <Typography.Paragraph type="secondary" className="text-lg">
        {t("guide.flowIntro", {
          defaultValue:
            "Quy trình 6 bước: tư liệu → OCR → trích xuất → chuẩn hóa → xem sơ đồ → xuất file. Demo hoàn chỉnh trong 5–7 thao tác.",
        })}
      </Typography.Paragraph>

      <Card className="mb-8 border-[hsl(var(--border))]" title={t("flow.stepperTitle", { defaultValue: "Quy trình xử lý gia phả" })}>
        <GenealogyFlowStepper currentStep="material" completedSteps={[]} />
      </Card>

      <Row gutter={[16, 16]} className="mb-8">
        {GENEALOGY_FLOW_STEPS.map((stepId, index) => (
          <Col xs={24} md={12} lg={8} key={stepId}>
            <Card className="h-full border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.45)] transition-colors">
              <div className="flex items-start gap-3 mb-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[hsl(var(--accent))] text-[hsl(var(--primary))] text-lg">
                  {FLOW_STEP_ICONS[stepId]}
                </span>
                <div>
                  <Typography.Text type="secondary" className="text-xs">
                    {t("flow.stepNumber", { defaultValue: "Bước {{n}}", n: index + 1 })}
                  </Typography.Text>
                  <Typography.Title level={5} className="!mb-0">
                    {t(`flow.step.${stepId}`, { defaultValue: stepId })}
                  </Typography.Title>
                </div>
              </div>
              <Typography.Paragraph type="secondary" className="!mb-4 text-sm">
                {t(`flow.stepDesc.${stepId}`, { defaultValue: "" })}
              </Typography.Paragraph>
              <Link to={GENEALOGY_FLOW_ROUTES[stepId]}>
                <Button type="primary" size="small">
                  {t("flow.openStep", { defaultValue: "Mở bước này" })}
                </Button>
              </Link>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} className="mb-8">
        <Col xs={24} md={8}>
          <Card>
            <Typography.Title level={4}>
              <ReadOutlined /> {t("guide.zone.public", { defaultValue: "Public" })}
            </Typography.Title>
            <Typography.Paragraph>
              {t("guide.publicSummary", {
                defaultValue: "Trang ai cũng xem được: trang chủ, hướng dẫn, đăng nhập, đăng ký.",
              })}
            </Typography.Paragraph>
            <Typography.Text strong>{PUBLIC_PAGES.length} trang</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Typography.Title level={4}>
              <UserOutlined /> {t("guide.zone.user", { defaultValue: "User" })}
            </Typography.Title>
            <Typography.Paragraph>
              {t("guide.userSummary", {
                defaultValue: "Cần đăng nhập: tổng quan, thư viện tài liệu, quy trình OCR, gia phả.",
              })}
            </Typography.Paragraph>
            <Typography.Text strong>{USER_PAGES.length} trang</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Typography.Title level={4}>
              <LockOutlined /> {t("guide.zone.admin", { defaultValue: "Admin" })}
            </Typography.Title>
            <Typography.Paragraph>
              {t("guide.adminSummary", {
                defaultValue: "Chỉ role admin: quản lý gia phả, pipeline và thành viên.",
              })}
            </Typography.Paragraph>
            <Typography.Text strong>{ADMIN_PAGES.length} trang</Typography.Text>
          </Card>
        </Col>
      </Row>

      <Card title={t("guide.allPagesTitle", { defaultValue: "Danh sách toàn bộ trang" })}>
        <Table rowKey="id" pagination={false} columns={columns} dataSource={APP_PAGES} scroll={{ x: 900 }} />
      </Card>

      <Card className="mt-6" title={t("guide.demoTitle", { defaultValue: "Demo luận văn (5–7 click)" })}>
        <Typography.Paragraph>
          1. {t("guide.demo1", { defaultValue: "Đăng nhập → /user/dashboard xem tiến độ quy trình." })}
        </Typography.Paragraph>
        <Typography.Paragraph>
          2. {t("guide.demo2", { defaultValue: "/user/documents — chọn tài liệu mẫu hoặc upload ảnh." })}
        </Typography.Paragraph>
        <Typography.Paragraph>
          3. {t("guide.demo3", { defaultValue: "Chi tiết tài liệu — OCR từng trang → Ghép trang (banner xanh bước ②)." })}
        </Typography.Paragraph>
        <Typography.Paragraph>
          4. {t("guide.demo4", { defaultValue: "Trích xuất quan hệ → xem preview people/edges." })}
        </Typography.Paragraph>
        <Typography.Paragraph>
          5. {t("guide.demo5", { defaultValue: "Lưu thành gia phả → /user/family-trees/:id." })}
        </Typography.Paragraph>
        <Typography.Paragraph className="!mb-0">
          6. {t("guide.demo6", { defaultValue: "Tab Sơ đồ — chọn dom-classic hoặc bảng; (tuỳ chọn) Export JSON." })}
        </Typography.Paragraph>
      </Card>
    </div>
  );
};

export default GuidePage;
