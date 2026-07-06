import { useEffect, useState } from "react";
import { Alert, Button, Spin, Typography } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";

import { EditDocumentForm } from "@/components/documents/EditDocumentForm";
import { getDocumentTypeLabel } from "@/components/documents/constants";
import { ApiError } from "@/lib/apiClient";
import { getDocument } from "@/lib/documentApi";
import type { FamilyTreeSourceDocument } from "@/types/document";

const EditDocumentPage = () => {
  const navigate = useNavigate();
  const { documentId } = useParams<{ documentId: string }>();
  const parsedId = Number(documentId);

  const [document, setDocument] = useState<FamilyTreeSourceDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(parsedId)) {
      setError("Document ID không hợp lệ.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    getDocument(parsedId)
      .then(setDocument)
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Không thể tải tài liệu.");
      })
      .finally(() => setLoading(false));
  }, [parsedId]);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <Button
            type="link"
            icon={<ArrowLeftOutlined />}
            className="!px-0"
            onClick={() =>
              navigate(
                document
                  ? `/admin/gia-pha/${document.family_tree_id}?tab=documents`
                  : "/admin/gia-pha",
              )
            }
          >
            Quay lại danh sách gia phả
          </Button>
          <Typography.Title level={4} className="!mb-1">
            Chỉnh sửa tài liệu
          </Typography.Title>
          {document && (
            <Typography.Text type="secondary">
              {document.title} · {getDocumentTypeLabel(document.type)} · Gia phả {document.family_tree_id}
            </Typography.Text>
          )}
        </div>
      </div>

      {loading ? (
        <div className="py-20 flex justify-center">
          <Spin size="large" tip="Đang tải tài liệu..." />
        </div>
      ) : error ? (
        <Alert
          type="error"
          showIcon
          message="Không tải được tài liệu"
          description={error}
          action={
            <Button onClick={() => navigate("/admin/gia-pha")}>Quay lại</Button>
          }
        />
      ) : document ? (
        <EditDocumentForm
          document={document}
          onUpdated={setDocument}
          onCancel={() => navigate(`/admin/gia-pha/${document.family_tree_id}?tab=documents`)}
        />
      ) : null}
    </div>
  );
};

export default EditDocumentPage;
