import { useEffect, useState } from "react";
import { Button, Card, Descriptions, Spin, Tag, Typography, message } from "antd";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { getUserDocument, type UserScan } from "@/lib/userWorkspaceApi";

const UserDocumentDetailPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { scanId } = useParams<{ scanId: string }>();
  const [scan, setScan] = useState<UserScan | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!scanId) return;
    (async () => {
      setLoading(true);
      try {
        const data = await getUserDocument(Number(scanId));
        setScan(data);
      } catch (err) {
        message.error(err instanceof Error ? err.message : "Không tải được tài liệu");
      } finally {
        setLoading(false);
      }
    })();
  }, [scanId]);

  if (loading) {
    return <Spin className="flex justify-center py-16" size="large" />;
  }

  if (!scan) {
    return (
      <Card>
        <Typography.Text type="danger">
          {t("userDocuments.notFound", { defaultValue: "Không tìm thấy tài liệu." })}
        </Typography.Text>
      </Card>
    );
  }

  return (
    <Card
      title={scan.title}
      extra={
        <Button onClick={() => navigate("/user/documents")}>
          {t("common.back", { defaultValue: "Quay lại" })}
        </Button>
      }
    >
      <Descriptions bordered column={1}>
        <Descriptions.Item label={t("userDocuments.name", { defaultValue: "Tên tài liệu" })}>{scan.title}</Descriptions.Item>
        <Descriptions.Item label={t("userDocuments.fileName", { defaultValue: "Tên file" })}>{scan.file_name}</Descriptions.Item>
        <Descriptions.Item label={t("userDocuments.fileType", { defaultValue: "Loại file" })}>{scan.file_type}</Descriptions.Item>
        <Descriptions.Item label={t("userDocuments.pages", { defaultValue: "Số trang" })}>{scan.page_count}</Descriptions.Item>
        <Descriptions.Item label={t("userDocuments.uploadedAt", { defaultValue: "Ngày upload" })}>
          {new Date(scan.uploaded_at).toLocaleString("vi-VN")}
        </Descriptions.Item>
        <Descriptions.Item label={t("userDocuments.ocrStatus", { defaultValue: "Trạng thái OCR" })}>
          <Tag>{scan.ocr_status}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label={t("userDocuments.treeStatus", { defaultValue: "Trạng thái gia phả" })}>
          <Tag>{scan.tree_status}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Request ID">{scan.request_id ?? "—"}</Descriptions.Item>
        <Descriptions.Item label={t("familyTree.treeName", { defaultValue: "Gia phả" })}>
          {scan.family_tree_id ? (
            <Button type="link" onClick={() => navigate(`/user/family-trees/${scan.family_tree_id}`)}>
              {scan.family_tree_id}
            </Button>
          ) : (
            "—"
          )}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};

export default UserDocumentDetailPage;
