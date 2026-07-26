import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Card, Descriptions, Spin, Tabs, Typography } from "antd";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { FlowNextBanner } from "@/components/flow/FlowNextBanner";
import { GenealogyFlowStepper } from "@/components/flow/GenealogyFlowStepper";
import { ServerSavedAlert } from "@/components/flow/ServerSavedAlert";
import { OcrStatusTag, TreeStatusTag } from "@/components/flow/StatusTags";
import DocumentReaderPage from "@/pages/DocumentReaderPage";
import { computeFlowProgressForScan } from "@/lib/flowProgress";
import { flowRouteForStep } from "@/lib/genealogyFlow";
import { getUserDocument, type UserScan } from "@/lib/userWorkspaceApi";

const UserDocumentDetailPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { scanId } = useParams<{ scanId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [scan, setScan] = useState<UserScan | null>(null);
  const [loading, setLoading] = useState(true);

  const activeTab = searchParams.get("tab") ?? "overview";

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

  if (scanId === "new") {
    return (
      <DocumentReaderPage
        embedded
        onScanRegistered={(id) => navigate(`/user/documents/${id}?tab=extract`)}
      />
    );
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

      <Card
        title={scan.title}
        extra={
          <Button onClick={() => navigate("/user/documents")}>
            {t("common.back", { defaultValue: "Quay lại" })}
          </Button>
        }
      >
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
              key: "ocr",
              label: t("flow.step.ocr", { defaultValue: "OCR / phiên âm" }),
              children: (
                <Alert
                  type="info"
                  showIcon
                  message={t("userDocuments.ocrTabTitle", { defaultValue: "OCR Hán-Nôm" })}
                  description={t("userDocuments.ocrTabDesc", {
                    defaultValue:
                      "Với ảnh scan Hán-Nôm: dùng Word/txt đã phiên âm và chuyển sang tab Trích xuất. OCR từng trang trên MinIO sẽ bổ sung trong bản cập nhật tiếp theo.",
                  })}
                  action={
                    <Button size="small" onClick={() => setTab("extract")}>
                      {t("flow.nextExtract")}
                    </Button>
                  }
                />
              ),
            },
            {
              key: "extract",
              label: t("flow.step.extract", { defaultValue: "Trích xuất" }),
              children: (
                <DocumentReaderPage
                  embedded
                  initialScanId={scan.id}
                  onScanRegistered={() => {
                    void getUserDocument(scan.id).then(setScan);
                  }}
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default UserDocumentDetailPage;
