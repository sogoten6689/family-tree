import { Button, Card, Col, Row, Space, Typography } from "antd";
import {
  BookOutlined,
  BranchesOutlined,
  ReadOutlined,
  SettingOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useAuth } from "@/contexts/AuthContext";

const DashboardPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <Card>
        <Typography.Title level={4}>
          {t("auth.welcomeUser", {
            defaultValue: "Xin chào, {{name}}",
            name: user?.full_name ?? user?.email,
          })}
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          {t("auth.currentRole", {
            defaultValue: "Quyền hiện tại: {{role}}",
            role: user?.role,
          })}
        </Typography.Paragraph>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card hoverable onClick={() => navigate("/user/document-reader")}>
            <BookOutlined className="text-2xl text-[#1677ff] mb-3" />
            <Typography.Title level={5}>
              {t("pages.userDocumentReader.title", { defaultValue: "Phòng đọc tài liệu" })}
            </Typography.Title>
            <Typography.Paragraph type="secondary" className="!mb-0">
              {t("pages.userDocumentReader.desc", { defaultValue: "Upload và phân tích tài liệu gia phả." })}
            </Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card hoverable onClick={() => navigate("/user/family-tree")}>
            <BranchesOutlined className="text-2xl text-[#1677ff] mb-3" />
            <Typography.Title level={5}>
              {t("pages.userFamilyTree.title", { defaultValue: "Xem gia phả" })}
            </Typography.Title>
            <Typography.Paragraph type="secondary" className="!mb-0">
              {t("pages.userFamilyTree.desc", { defaultValue: "Xem cây gia phả trực quan." })}
            </Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card hoverable onClick={() => navigate("/huong-dan")}>
            <ReadOutlined className="text-2xl text-[#1677ff] mb-3" />
            <Typography.Title level={5}>
              {t("pages.guide.title", { defaultValue: "Hướng dẫn" })}
            </Typography.Title>
            <Typography.Paragraph type="secondary" className="!mb-0">
              {t("pages.guide.desc", { defaultValue: "Xem danh sách trang và cách sử dụng." })}
            </Typography.Paragraph>
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
