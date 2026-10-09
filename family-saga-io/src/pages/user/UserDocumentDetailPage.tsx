import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Card, Descriptions, Modal, Space, Spin, Tabs, Typography } from "antd";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { FlowNextBanner } from "@/components/flow/FlowNextBanner";
import { GenealogyFlowStepper } from "@/components/flow/GenealogyFlowStepper";
import { ServerSavedAlert } from "@/components/flow/ServerSavedAlert";
import { OcrStatusTag, TreeStatusTag } from "@/components/flow/StatusTags";
import DocumentReaderPage from "@/pages/DocumentReaderPage";
import { LlmImportPanel } from "@/components/documents/LlmImportPanel";
import { MaDinhDanhField } from "@/components/documents/MaDinhDanhField";
import { PageViewer } from "@/components/documents/PageViewer";
import { useAuth } from "@/contexts/AuthContext";
import { computeFlowProgressForScan } from "@/lib/flowProgress";
import { flowRouteForStep } from "@/lib/genealogyFlow";
import { deleteUserDocument, getUserDocument, type UserScan } from "@/lib/userWorkspaceApi";

const UserDocumentDetailPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { scanId } = useParams<{ scanId: string }>();
  const { isAdmin } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [scan, setScan] = useState<UserScan | null>(null);
  const [loading, setLoading] = useState(true);
  // Tăng khi đổi phiên bản hiện tại → tab Trích xuất / Trang dựng lại với dữ liệu mới.
  const [contentKey, setContentKey] = useState(0);

  // Tab "OCR / phiên âm" cũ chỉ là thông báo — OCR + vote từng trang nằm ở tab Trang;
  // link cũ ?tab=ocr (luồng gia phả) mở thẳng tab Trang.
  const rawTab = searchParams.get("tab") ?? "overview";
  const activeTab = rawTab === "ocr" ? "pages" : rawTab;

  useEffect(() => {
    if (!scanId || scanId === "new") {
      setLoading(false);
      return;
    }

    (async () => {
      setLoading(true);
      try {
        const data = await getUserDocument(Number(scanId));
        setScan(data);
      } catch {
        setScan(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [scanId]);

  const flowState = useMemo(
    () => (scan ? computeFlowProgressForScan(scan) : null),
    [scan],
  );

  // Xoá MỀM cả bộ (chỉ admin): ẩn khỏi mọi danh sách, khôi phục được ở trang Tài liệu.
  const confirmDeleteDocument = () => {
    if (!scan) return;
    Modal.confirm({
      title: t("userDocuments.deleteTitle", { defaultValue: "Xoá bộ \"{{title}}\"?", title: scan.title }),
      content: t("userDocuments.deleteBody", {
        defaultValue:
          "Bộ sẽ bị ẩn khỏi danh sách và thống kê công khai. Trang, ảnh và mã định danh vẫn được giữ; admin khôi phục lại được ở mục \"Đã xoá\" của trang Tài liệu.",
      }),
      okText: t("userDocuments.deleteOk", { defaultValue: "Xoá bộ" }),
      okButtonProps: { danger: true },
      cancelText: t("pageViewer.cancel", { defaultValue: "Huỷ" }),
      onOk: async () => {
        try {
          await deleteUserDocument(scan.id);
          navigate("/user/documents");
        } catch (err) {
          Modal.error({ title: err instanceof Error ? err.message : "Không xoá được bộ" });
        }
      },
    });
  };

  if (scanId === "new") {
    // Keep the reader mounted: the selected File and its preview are local
    // until recognition finishes. Navigating here would discard both.
    return <DocumentReaderPage embedded />;
  }

  if (loading) {
    return <Spin className="flex justify-center py-16" size="large" />;
  }

  if (!scan) {
    return (
      <Card>
        <Typography.Text type="danger">
          {t("userDocuments.notFound", { defaultValue: "Không tìm thấy tài liệu." })}
        </Typography.Text>
        <Button className="mt-4" onClick={() => navigate("/user/documents")}>
          {t("common.back", { defaultValue: "Quay lại" })}
        </Button>
      </Card>
    );
  }

  const setTab = (tab: string) => {
    setSearchParams({ tab });
  };

  return (
    <div className="space-y-4">
      <ServerSavedAlert uploadedAt={scan.uploaded_at} />

      {flowState && (
        <Card className="border-[hsl(var(--border))]" size="small">
          <GenealogyFlowStepper
            compact
            currentStep={flowState.currentStep}
            completedSteps={flowState.completedSteps}
          />
        </Card>
      )}

      {scan.ocr_status === "completed" && scan.tree_status === "none" && (
        <FlowNextBanner
          message={t("flow.ocrMergeDone")}
          nextLabel={t("flow.nextExtract")}
          nextHref={`/user/documents/${scan.id}?tab=extract`}
        />
      )}

      {scan.tree_status === "created" && scan.family_tree_id && (
        <FlowNextBanner
          message={t("flow.treeCreated", { defaultValue: "Cây gia phả đã được tạo." })}
          nextLabel={t("flow.openVisual", { defaultValue: "Xem sơ đồ" })}
          nextHref={flowRouteForStep("visual", { treeId: scan.family_tree_id })}
        />
      )}

      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Typography.Title level={4} className="!mb-0">
            {scan.title}
          </Typography.Title>
          <Space>
            {isAdmin && (
              <Button danger onClick={confirmDeleteDocument}>
                {t("userDocuments.delete", { defaultValue: "Xoá bộ" })}
              </Button>
            )}
            <Button onClick={() => navigate("/user/documents")}>
              {t("common.back", { defaultValue: "Quay lại" })}
            </Button>
          </Space>
        </div>
        <Tabs
          activeKey={activeTab}
          onChange={setTab}
          items={[
            {
              key: "overview",
              label: t("userDocuments.tabOverview", { defaultValue: "Tổng quan" }),
              children: (
                <Descriptions bordered column={1}>
                  <Descriptions.Item label={t("userDocuments.name", { defaultValue: "Tên tài liệu" })}>
                    {scan.title}
                  </Descriptions.Item>
                  <Descriptions.Item label={t("maDinhDanh.label", { defaultValue: "Mã định danh" })}>
                    <MaDinhDanhField scan={scan} onChanged={() => void getUserDocument(scan.id).then(setScan)} />
                  </Descriptions.Item>
                  <Descriptions.Item label={t("userDocuments.fileName", { defaultValue: "Tên file" })}>
                    {scan.file_name}
                  </Descriptions.Item>
                  <Descriptions.Item label={t("userDocuments.fileType", { defaultValue: "Loại file" })}>
                    {scan.file_type}
                  </Descriptions.Item>
                  <Descriptions.Item label={t("userDocuments.pages", { defaultValue: "Số trang" })}>
                    {scan.page_count}
                  </Descriptions.Item>
                  <Descriptions.Item label={t("userDocuments.uploadedAt", { defaultValue: "Ngày upload" })}>
                    {new Date(scan.uploaded_at).toLocaleString("vi-VN")}
                  </Descriptions.Item>
                  <Descriptions.Item label={t("userDocuments.ocrStatusLabel", { defaultValue: "Trạng thái OCR" })}>
                    <OcrStatusTag status={scan.ocr_status} />
                  </Descriptions.Item>
                  <Descriptions.Item label={t("userDocuments.treeStatusLabel", { defaultValue: "Trạng thái gia phả" })}>
                    <TreeStatusTag status={scan.tree_status} />
                  </Descriptions.Item>
                  <Descriptions.Item label={t("familyTree.treeName", { defaultValue: "Gia phả" })}>
                    {scan.family_tree_id ? (
                      <Button
                        type="link"
                        onClick={() =>
                          navigate(flowRouteForStep("visual", { treeId: scan.family_tree_id! }))
                        }
                      >
                        {scan.family_tree_id}
                      </Button>
                    ) : (
                      "—"
                    )}
                  </Descriptions.Item>
                </Descriptions>
              ),
            },
            {
              key: "extract",
              label: t("flow.step.extract", { defaultValue: "Trích xuất" }),
              children: (
                <DocumentReaderPage
                  key={`extract-${contentKey}`}
                  embedded
                  initialScanId={scan.id}
                  onScanRegistered={() => {
                    void getUserDocument(scan.id).then(setScan);
                  }}
                />
              ),
            },
            {
              key: "pages",
              label: t("pageViewer.tab", { defaultValue: "Trang" }),
              children: <PageViewer key={`pages-${contentKey}`} scanId={scan.id} />,
            },
            {
              key: "versions",
              label: t("llmImport.tab", { defaultValue: "Phiên bản & nhập LLM" }),
              children: (
                <LlmImportPanel
                  scanId={scan.id}
                  isAdmin={isAdmin}
                  onCurrentChanged={() => {
                    setContentKey((k) => k + 1);
                    void getUserDocument(scan.id).then(setScan);
                  }}
                />
              ),
            },
          ]}
        />
      </div>
    </div>
  );
};

export default UserDocumentDetailPage;
