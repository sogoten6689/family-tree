import { CloudDownloadOutlined, PlayCircleOutlined, SyncOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Tag,
  Typography,
  message,
} from "antd";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiRequest } from "@/lib/apiClient";

type FormValues = {
  collectionId: number;
  volumeId: number;
  delaySeconds: number;
  maxPages: number;
  imageVariant: "large" | "jpeg";
  pageStart: number;
  pageEnd?: number | null;
  saveToSystem: boolean;
  crawlOnly: boolean;
  attachOnly: boolean;
  background: boolean;
  runOcr: boolean;
  runAnalyze: boolean;
  treeId?: string;
  syncPipeline: boolean;
};

type CrawlResult = {
  collection_id: number;
  volume_id: number;
  output_dir: string;
  downloaded_pages: number;
  page_count: number;
  errors: number;
  catalog_slug?: string | null;
  title?: string | null;
  tree_id?: string | null;
  tree_name?: string | null;
  images_document_id?: number | null;
  images_attached?: number;
  pipeline_synced?: boolean;
  job_id?: string | null;
  job_status?: string | null;
  ocr_processed?: number;
  ocr_errors?: number;
  merged_pages?: number;
  analyze_node_count?: number;
  analyze_error?: string | null;
  page_start?: number | null;
  page_end?: number | null;
};

type JobStatus = {
  job_id: string;
  status: string;
  type: string;
  progress: Record<string, unknown>;
  result?: CrawlResult | null;
  error?: string | null;
};

const DEFAULT_VALUES: FormValues = {
  collectionId: 2,
  volumeId: 1255,
  delaySeconds: 0.3,
  maxPages: 100,
  imageVariant: "large",
  pageStart: 1,
  pageEnd: null,
  saveToSystem: true,
  crawlOnly: false,
  attachOnly: false,
  background: false,
  runOcr: true,
  runAnalyze: false,
  treeId: "",
  syncPipeline: true,
};

const JOB_POLL_MS = 3000;

const NomFoundationCrawlPage = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm<FormValues>();
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CrawlResult | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const pollJob = async (jobId: string) => {
    try {
      const status = await apiRequest<JobStatus>(`/api/nomfoundation/jobs/${jobId}`);
      setJob(status);
      if (status.status === "done" && status.result) {
        setResult(status.result);
        stopPolling();
        setRunning(false);
        message.success("Job crawl/import hoàn tất.");
      } else if (status.status === "error") {
        stopPolling();
        setRunning(false);
        setError(status.error || "Job thất bại.");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Không thể lấy trạng thái job";
      setError(msg);
      stopPolling();
      setRunning(false);
    }
  };

  useEffect(() => () => stopPolling(), []);

  const handleSubmit = async (values: FormValues) => {
    setRunning(true);
    setError(null);
    setJob(null);
    stopPolling();

    try {
      const response = await apiRequest<CrawlResult>("/api/nomfoundation/crawl-volume", {
        method: "POST",
        body: JSON.stringify({
          collection_id: values.collectionId,
          volume_id: values.volumeId,
          delay_seconds: values.delaySeconds,
          max_pages: values.maxPages,
          image_variant: values.imageVariant,
          page_start: values.pageStart,
          page_end: values.pageEnd ?? null,
          save_to_system: values.saveToSystem,
          crawl_only: values.crawlOnly,
          attach_only: values.attachOnly,
          background: values.background,
          run_ocr: values.runOcr,
          run_analyze: values.runAnalyze,
          tree_id: values.treeId?.trim() || null,
          sync_pipeline: values.syncPipeline,
        }),
      });

      if (response.job_id && values.background) {
        setResult(response);
        setJob({
          job_id: response.job_id,
          status: response.job_status || "queued",
          type: "nom_import",
          progress: {},
        });
        pollRef.current = setInterval(() => {
          void pollJob(response.job_id!);
        }, JOB_POLL_MS);
        void pollJob(response.job_id);
        message.info("Job đang chạy nền — trang này sẽ tự cập nhật.");
      } else {
        setResult(response);
        setRunning(false);
        message.success(
          t("admin.developer.nomCrawlSuccess", { defaultValue: "Crawl Nom Foundation hoàn tất." }),
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Không thể crawl volume";
      setError(msg);
      setResult(null);
      setRunning(false);
    }
  };

  const jobStatusColor = (status: string) => {
    if (status === "done") return "success";
    if (status === "error") return "error";
    if (status === "running") return "processing";
    return "default";
  };

  const progressLabel = job?.progress
    ? Object.entries(job.progress)
        .filter(([, v]) => v != null && v !== "")
        .map(([k, v]) => `${k}: ${String(v)}`)
        .join(" · ")
    : null;

  return (
    <Space direction="vertical" size="large" className="w-full">
      <div>
        <Typography.Title level={4} className="!mb-1">
          {t("admin.developer.nomCrawlTitle", { defaultValue: "Crawl Nom Foundation" })}
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="!mb-0">
          {t("admin.developer.nomCrawlDesc", {
            defaultValue:
              "Tải ảnh scan từ lib.nomfoundation.org. Volume lớn (208: 79 trang, 855: 42 trang, 1255: 6 trang, 1256: 42 trang) nên chia page_start/page_end hoặc bật job nền.",
          })}
        </Typography.Paragraph>
      </div>

      {error && <Alert type="error" showIcon message={error} closable onClose={() => setError(null)} />}

      <Card title={t("admin.developer.nomCrawlForm", { defaultValue: "Tham số crawl" })} extra={<CloudDownloadOutlined />}>
        <Form form={form} layout="vertical" initialValues={DEFAULT_VALUES} onFinish={handleSubmit}>
          <Row gutter={16}>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Collection ID" name="collectionId" rules={[{ required: true }]}>
                <InputNumber min={1} className="w-full" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item
                label="Volume ID"
                name="volumeId"
                rules={[{ required: true }]}
                extra="VD: 1255, 1256, 208"
              >
                <InputNumber min={1} className="w-full" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Trang từ" name="pageStart">
                <InputNumber min={1} className="w-full" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Trang đến" name="pageEnd" extra="Để trống = hết volume">
                <InputNumber min={1} className="w-full" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Delay (giây)" name="delaySeconds">
                <InputNumber min={0} max={5} step={0.1} className="w-full" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Max pages" name="maxPages">
                <InputNumber min={1} max={200} className="w-full" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Ảnh" name="imageVariant">
                <Select
                  options={[
                    { value: "large", label: "large (OCR)" },
                    { value: "jpeg", label: "jpeg (nhanh)" },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={12}>
              <Form.Item
                label={t("admin.developer.nomTreeId", { defaultValue: "Tree ID (tùy chọn)" })}
                name="treeId"
                extra={t("admin.developer.nomTreeIdHint", { defaultValue: "Để trống → nom-{volumeId}" })}
              >
                <Input placeholder="nom-1255" allowClear />
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Space size="large" wrap>
                <Form.Item name="saveToSystem" valuePropName="checked" className="!mb-0">
                  <Checkbox>Lưu MinIO + tạo cây gia phả</Checkbox>
                </Form.Item>
                <Form.Item name="syncPipeline" valuePropName="checked" className="!mb-0">
                  <Checkbox>Đồng bộ pipeline step ②</Checkbox>
                </Form.Item>
                <Form.Item name="runOcr" valuePropName="checked" className="!mb-0">
                  <Checkbox>OCR sau attach (mặc định bật, cần token)</Checkbox>
                </Form.Item>
                <Form.Item name="runAnalyze" valuePropName="checked" className="!mb-0">
                  <Checkbox>Phân tích OCR ghép → balkan_nodes (Gemini)</Checkbox>
                </Form.Item>
                <Form.Item name="background" valuePropName="checked" className="!mb-0">
                  <Checkbox>Chạy job nền (tránh timeout)</Checkbox>
                </Form.Item>
              </Space>
            </Col>
            <Col xs={24}>
              <Space size="large" wrap>
                <Form.Item name="crawlOnly" valuePropName="checked" className="!mb-0">
                  <Checkbox>Chỉ crawl local (không MinIO)</Checkbox>
                </Form.Item>
                <Form.Item name="attachOnly" valuePropName="checked" className="!mb-0">
                  <Checkbox>Chỉ attach ảnh local đã có</Checkbox>
                </Form.Item>
              </Space>
            </Col>
          </Row>
          <Button type="primary" htmlType="submit" icon={<PlayCircleOutlined />} loading={running}>
            {t("familyTree.run", { defaultValue: "Chạy" })}
          </Button>
        </Form>
      </Card>

      {job && (
        <Card title="Job nền" extra={<SyncOutlined spin={job.status === "running" || job.status === "queued"} />}>
          <Space direction="vertical" className="w-full">
            <Space>
              <Typography.Text>Job ID:</Typography.Text>
              <Typography.Text code>{job.job_id}</Typography.Text>
              <Tag color={jobStatusColor(job.status)}>{job.status}</Tag>
            </Space>
            {(job.status === "running" || job.status === "queued") && (
              <Progress percent={99} status="active" showInfo={false} />
            )}
            {progressLabel && (
              <Typography.Text type="secondary">{progressLabel}</Typography.Text>
            )}
            {job.error && <Alert type="error" showIcon message={job.error} />}
          </Space>
        </Card>
      )}

      {result && (
        <Card title={t("admin.developer.crawlResult", { defaultValue: "Kết quả" })}>
          <Row gutter={16} className="mb-4">
            <Col xs={6}>
              <Statistic title="Ảnh tải" value={result.downloaded_pages} />
            </Col>
            <Col xs={6}>
              <Statistic title="Tổng trang" value={result.page_count} />
            </Col>
            <Col xs={6}>
              <Statistic title="Lỗi crawl" value={result.errors} />
            </Col>
            <Col xs={6}>
              <Statistic title="OCR" value={result.ocr_processed ?? 0} suffix={result.ocr_errors ? `(${result.ocr_errors} lỗi)` : undefined} />
            </Col>
            <Col xs={6}>
              <Statistic title="Ghép trang" value={result.merged_pages ?? 0} />
            </Col>
          </Row>
          {(result.analyze_node_count != null && result.analyze_node_count > 0) || result.analyze_error ? (
            <Row gutter={16} className="mb-4">
              <Col xs={12}>
                <Statistic title="Nodes phân tích" value={result.analyze_node_count ?? 0} />
              </Col>
              {result.analyze_error && (
                <Col xs={12}>
                  <Alert type="warning" showIcon message={result.analyze_error} />
                </Col>
              )}
            </Row>
          ) : null}
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Output">{result.output_dir}</Descriptions.Item>
            <Descriptions.Item label="Volume">
              collection/{result.collection_id}/volume/{result.volume_id}
              {(result.page_start || result.page_end) && (
                <> — trang {result.page_start ?? 1}–{result.page_end ?? "cuối"}</>
              )}
            </Descriptions.Item>
            {result.title && <Descriptions.Item label="Tên">{result.title}</Descriptions.Item>}
            {result.catalog_slug && (
              <Descriptions.Item label="Catalog slug">{result.catalog_slug}</Descriptions.Item>
            )}
            {result.tree_id && (
              <Descriptions.Item label="Cây gia phả">
                <a href={`/admin/gia-pha/${result.tree_id}?tab=documents`}>{result.tree_id}</a>
              </Descriptions.Item>
            )}
            {result.images_document_id != null && (
              <Descriptions.Item label="Document ảnh">
                <a href={`/admin/documents/${result.images_document_id}/edit`}>
                  #{result.images_document_id}
                </a>{" "}
                ({result.images_attached ?? 0} file)
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      )}
    </Space>
  );
};

export default NomFoundationCrawlPage;
