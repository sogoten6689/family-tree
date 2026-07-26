import { BookOutlined, BranchesOutlined, CloudUploadOutlined } from "@ant-design/icons";
import { Card, Col, Row, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

export function QuickStartCards() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const items = [
    {
      key: "upload",
      icon: CloudUploadOutlined,
      title: t("flow.quick.uploadTitle", { defaultValue: "Tải tư liệu" }),
      desc: t("flow.quick.uploadDesc", { defaultValue: "Bước 1 — upload ảnh hoặc văn bản gia phả." }),
      href: "/user/documents",
    },
    {
      key: "ocr",
      icon: BookOutlined,
      title: t("flow.quick.ocrTitle", { defaultValue: "Tiếp tục OCR" }),
      desc: t("flow.quick.ocrDesc", { defaultValue: "Bước 2 — OCR và ghép trang phiên âm." }),
      href: "/user/documents",
    },
    {
      key: "tree",
      icon: BranchesOutlined,
      title: t("flow.quick.treeTitle", { defaultValue: "Xem gia phả" }),
      desc: t("flow.quick.treeDesc", { defaultValue: "Bước 5 — mở sơ đồ cây đã tạo." }),
      href: "/user/family-trees",
    },
  ];

  return (
    <Row gutter={[16, 16]}>
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <Col xs={24} md={8} key={item.key}>
            <Card
              hoverable
              className="h-full border-[hsl(var(--border))] bg-card hover:border-[hsl(var(--primary)/0.45)] transition-colors"
              onClick={() => navigate(item.href)}
            >
              <Icon className="text-2xl text-[hsl(var(--primary))] mb-3" />
              <Typography.Title level={5} className="!mb-1">
                {item.title}
              </Typography.Title>
              <Typography.Paragraph type="secondary" className="!mb-0 text-sm">
                {item.desc}
              </Typography.Paragraph>
            </Card>
          </Col>
        );
      })}
    </Row>
  );
}
