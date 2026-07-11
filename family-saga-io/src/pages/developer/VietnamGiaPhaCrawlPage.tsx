import { CloudDownloadOutlined, PlayCircleOutlined, ReloadOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Row,
  Space,
  Statistic,
  Switch,
  Typography,
  message,
} from "antd";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import CodeBlock from "@/components/developer/CodeBlock";
import { getBackendBaseUrl } from "@/lib/apiClient";
import {
  crawlAndSyncVietnamGiaPha,
  type VietnamGiaPhaCrawlSyncResult,
} from "@/lib/familyTreeApi";
import { DEVELOPER_ROUTES } from "@/config/developerRoutes";

type CrawlFormValues = {
  startId: number;
  endId: number;
  delaySeconds: number;
  syncDb: boolean;
  skipUnchanged: boolean;
  exportText: boolean;
  attachDocuments: boolean;
};

const DEFAULT_VALUES: CrawlFormValues = {
  startId: 100,
  endId: 200,
  delaySeconds: 0.2,
  syncDb: true,
  skipUnchanged: true,
  exportText: false,
  attachDocuments: true,
};

const baseUrl = getBackendBaseUrl() || "https://giapha.kimtudien.com.vn";

const CRAWL_CURL = `curl -X POST "${baseUrl}/api/vietnamgiapha/crawl-sync" \\
  -H "Authorization: Bearer <JWT_ADMIN>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "start_id": 100,
    "end_id": 200,
    "delay_seconds": 0.2,
    "sync_db": true,
    "skip_unchanged": true,
    "export_text": true,
    "attach_documents": false
  }'`;

const VietnamGiaPhaCrawlPage = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm<CrawlFormValues>();
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<VietnamGiaPhaCrawlSyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (values: CrawlFormValues) => {
    if (values.startId > values.endId) {
      message.error("ID bắt đầu phải nhỏ hơn hoặc bằng ID kết thúc");
      return;
    }

    setRunning(true);
    setError(null);
    try {
      const response = await crawlAndSyncVietnamGiaPha({
        start_id: values.startId,
        end_id: values.endId,
        delay_seconds: values.delaySeconds,
        crawl_version: "v2",
        sync_db: values.syncDb,
        skip_unchanged: values.skipUnchanged,
        sync_pipeline: true,
        export_text: values.exportText,
        attach_documents: values.attachDocuments,
      });
      setResult(response);
      message.success(
        t("admin.developer.crawlSuccess", {
          defaultValue: "Crawl và đồng bộ hoàn tất.",
        }),
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Không thể crawl/sync dữ liệu";
      setError(msg);
      setResult(null);
    } finally {
      setRunning(false);
    }
  };

  return (
    <Space direction="vertical" size="large" className="w-full">
      <div>
        <Typography.Title level={4} className="!mb-1">
          {t("admin.developer.crawlTitle", { defaultValue: "Crawl VietnamGiaPha" })}
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="!mb-0">
          {t("admin.developer.crawlDesc", {
            defaultValue:
              "Thu thập cây phả hệ từ vietnamgiapha.com theo khoảng ID và đồng bộ vào MySQL (mã cây: vgp-{id}).",
          })}
        </Typography.Paragraph>
      </div>

      <Alert
        type="warning"
        showIcon
        message={t("admin.developer.crawlWarningTitle", { defaultValue: "Thao tác hệ thống" })}
        description={t("admin.developer.crawlWarningDesc", {
          defaultValue:
            "Chỉ dành cho admin/developer. Crawl nhiều ID có thể mất vài phút. Tôn trọng delay để tránh quá tải nguồn.",
        })}
      />

      {error && (
        <Alert type="error" showIcon message={error} closable onClose={() => setError(null)} />
      )}

      <Card
        title={t("admin.developer.crawlFormTitle", { defaultValue: "Tham số crawl" })}
        extra={<CloudDownloadOutlined />}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={DEFAULT_VALUES}
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col xs={24} sm={12} md={6}>
              <Form.Item
                label={t("familyTree.startId", { defaultValue: "ID bắt đầu" })}
                name="startId"
                rules={[{ required: true, message: "Nhập ID bắt đầu" }]}
              >
                <InputNumber min={1} max={100000} className="w-full" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item
                label={t("familyTree.endId", { defaultValue: "ID kết thúc" })}
                name="endId"
                rules={[{ required: true, message: "Nhập ID kết thúc" }]}
              >
                <InputNumber min={1} max={100000} className="w-full" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item
                label={t("familyTree.delaySeconds", { defaultValue: "Delay (giây)" })}
                name="delaySeconds"
              >
                <InputNumber min={0} max={5} step={0.1} className="w-full" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item
                label={t("familyTree.syncDb", { defaultValue: "Đồng bộ database" })}
                name="syncDb"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item
                label={t("admin.developer.skipUnchanged", { defaultValue: "Bỏ qua nếu không đổi" })}
                name="skipUnchanged"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item
                label={t("admin.developer.exportText", { defaultValue: "Xuất text" })}
                name="exportText"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item
                label={t("admin.developer.attachDocuments", { defaultValue: "Gắn MinIO" })}
                name="attachDocuments"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Space wrap>
            <Button
              type="primary"
              htmlType="submit"
              icon={<PlayCircleOutlined />}
              loading={running}
            >
              {t("familyTree.run", { defaultValue: "Chạy" })}
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                form.setFieldsValue(DEFAULT_VALUES);
                setResult(null);
                setError(null);
              }}
              disabled={running}
            >
              {t("admin.developer.resetForm", { defaultValue: "Đặt lại" })}
            </Button>
            <Link to="/admin/gia-pha">
              {t("admin.developer.viewTrees", { defaultValue: "Xem danh sách gia phả →" })}
            </Link>
          </Space>
        </Form>
      </Card>

      {result && (
        <Card title={t("admin.developer.crawlResult", { defaultValue: "Kết quả lần chạy gần nhất" })}>
          <Row gutter={[16, 16]} className="mb-4">
            <Col xs={12} sm={8} md={4}>
              <Statistic title="Crawl OK" value={result.crawl_success} valueStyle={{ color: "var(--ant-color-success)" }} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Statistic title="Crawl skip (trống)" value={result.crawl_skipped} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Statistic title="Crawl skip (không đổi)" value={result.crawl_skipped_unchanged} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Statistic title="Crawl lỗi" value={result.crawl_errors} valueStyle={{ color: result.crawl_errors ? "var(--ant-color-error)" : undefined }} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Statistic title="Text mới" value={result.text_built} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Statistic title="DB upsert" value={result.sync_upserted} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Statistic title="DB skip" value={result.sync_skipped} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Statistic title="Sync lỗi" value={result.sync_errors} valueStyle={{ color: result.sync_errors ? "var(--ant-color-error)" : undefined }} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Statistic title="Text gắn MinIO" value={result.text_attached} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Statistic title="Gắn skip" value={result.text_attach_skipped} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Statistic title="Gắn lỗi" value={result.text_attach_errors} valueStyle={{ color: result.text_attach_errors ? "var(--ant-color-error)" : undefined }} />
            </Col>
          </Row>
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Phiên bản crawl">{result.crawl_version}</Descriptions.Item>
            <Descriptions.Item label="Khoảng ID">
              {result.start_id} – {result.end_id}
            </Descriptions.Item>
            {result.output_dir ? (
              <Descriptions.Item label="Thư mục output">{result.output_dir}</Descriptions.Item>
            ) : null}
          </Descriptions>
          {result.error_details && result.error_details.length > 0 && (
            <Alert
              className="mt-4"
              type="error"
              showIcon
              message="Chi tiết lỗi"
              description={
                <pre className="text-xs whitespace-pre-wrap m-0">
                  {JSON.stringify(result.error_details, null, 2)}
                </pre>
              }
            />
          )}
        </Card>
      )}

      <Card title="CURL mẫu">
        <Typography.Paragraph type="secondary" className="!mb-3">
          Endpoint: <Typography.Text code>POST /api/vietnamgiapha/crawl-sync</Typography.Text>
          {" · "}
          <Link to={DEVELOPER_ROUTES.docs}>Tài liệu Developer</Link>
        </Typography.Paragraph>
        <CodeBlock code={CRAWL_CURL} language="bash" />
      </Card>
    </Space>
  );
};

export default VietnamGiaPhaCrawlPage;
