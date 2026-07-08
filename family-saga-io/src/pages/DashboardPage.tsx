import { useEffect, useState } from "react";
import { Button, Card, Col, Row, Space, Statistic, Typography } from "antd";
import {
  BookOutlined,
  BranchesOutlined,
  ReadOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useAuth } from "@/contexts/AuthContext";
import { getUserStats } from "@/lib/userWorkspaceApi";

const DashboardPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const [stats, setStats] = useState({ scanned_documents: 0, family_trees: 0, history_total: 0 });

  useEffect(() => {
    getUserStats()
      .then(setStats)
      .catch(() => setStats({ scanned_documents: 0, family_trees: 0, history_total: 0 }));
  }, []);

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
          <Card>
            <Statistic
              title={t("dashboard.scannedDocs", { defaultValue: "Tài liệu đã scan" })}
              value={stats.scanned_documents}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title={t("dashboard.familyTrees", { defaultValue: "Cây gia phả đã tạo" })}
              value={stats.family_trees}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title={t("dashboard.historyTotal", { defaultValue: "Lịch sử truy vấn" })}
              value={stats.history_total}
            />
          </Card>
        </Col>
      </Row>

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
          <Card hoverable onClick={() => navigate("/user/family-trees")}>
            <BranchesOutlined className="text-2xl text-[#1677ff] mb-3" />
            <Typography.Title level={5}>
              {t("userFamilyTrees.title", { defaultValue: "Gia phả đã tạo" })}
            </Typography.Title>
            <Typography.Paragraph type="secondary" className="!mb-0">
              {t("userFamilyTrees.desc", { defaultValue: "Danh sách cây gia phả của bạn." })}
            </Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card hoverable onClick={() => navigate("/user/documents")}>
            <BookOutlined className="text-2xl text-[#1677ff] mb-3" />
            <Typography.Title level={5}>
              {t("userDocuments.title", { defaultValue: "Tài liệu đã scan" })}
            </Typography.Title>
            <Typography.Paragraph type="secondary" className="!mb-0">
              {t("userDocuments.desc", { defaultValue: "Quản lý tài liệu đã upload." })}
            </Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card hoverable onClick={() => navigate("/user/profile")}>
            <UserOutlined className="text-2xl text-[#1677ff] mb-3" />
            <Typography.Title level={5}>
              {t("profile.title", { defaultValue: "Tài khoản" })}
            </Typography.Title>
            <Typography.Paragraph type="secondary" className="!mb-0">
              {t("profile.desc", { defaultValue: "Quản lý thông tin cá nhân." })}
            </Typography.Paragraph>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
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
