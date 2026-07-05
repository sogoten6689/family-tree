import { LockOutlined, ReadOutlined, TeamOutlined, UserOutlined } from "@ant-design/icons";
import { Card, Col, Row, Table, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ADMIN_PAGES, APP_PAGES, PUBLIC_PAGES, USER_PAGES, type AppPageMeta } from "@/config/pages";

const zoneColors: Record<AppPageMeta["zone"], string> = {
  public: "blue",
  user: "green",
  admin: "gold",
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
        <Tag color={zoneColors[zone]}>
          {t(`guide.zone.${zone}`, { defaultValue: zone })}
        </Tag>
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
        {t("guide.pageIntro", {
          defaultValue:
            "Tài liệu tổng quan về cấu trúc ứng dụng: trang công khai, trang người dùng và trang quản trị.",
        })}
      </Typography.Paragraph>

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
                defaultValue: "Cần đăng nhập: bảng điều khiển, đọc tài liệu, xem gia phả.",
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
                defaultValue: "Chỉ role admin: quản lý gia phả và quản lý tài khoản.",
              })}
            </Typography.Paragraph>
            <Typography.Text strong>{ADMIN_PAGES.length} trang</Typography.Text>
          </Card>
        </Col>
      </Row>

      <Card title={t("guide.allPagesTitle", { defaultValue: "Danh sách toàn bộ trang" })}>
        <Table rowKey="id" pagination={false} columns={columns} dataSource={APP_PAGES} scroll={{ x: 900 }} />
      </Card>

      <Card className="mt-6" title={t("guide.quickStartTitle", { defaultValue: "Bắt đầu nhanh" })}>
        <Typography.Paragraph>
          1. {t("guide.step1", { defaultValue: "Đăng ký tài khoản tại /register (mặc định role user)." })}
        </Typography.Paragraph>
        <Typography.Paragraph>
          2. {t("guide.step2", { defaultValue: "Đăng nhập và vào /user/document-reader để upload tài liệu gia phả." })}
        </Typography.Paragraph>
        <Typography.Paragraph>
          3. {t("guide.step3", { defaultValue: "Xem cây gia phả tại /user/family-tree." })}
        </Typography.Paragraph>
        <Typography.Paragraph className="!mb-0">
          4. {t("guide.step4", { defaultValue: "Admin quản lý hệ thống tại /admin/gia-pha và /admin/users." })}
        </Typography.Paragraph>
      </Card>
    </div>
  );
};

export default GuidePage;
