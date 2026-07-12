import { CloudDownloadOutlined, PlayCircleOutlined } from "@ant-design/icons";
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
  Row,
  Select,
  Space,
  Statistic,
  Typography,
  message,
} from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { apiRequest } from "@/lib/apiClient";

type FormValues = {
  collectionId: number;
  volumeId: number;
  delaySeconds: number;
  maxPages: number;
  imageVariant: "large" | "jpeg";
  saveToSystem: boolean;
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
};

const DEFAULT_VALUES: FormValues = {
  collectionId: 2,
  volumeId: 1255,
  delaySeconds: 0.3,
  maxPages: 100,
  imageVariant: "large",
  saveToSystem: true,
  treeId: "",
  syncPipeline: true,
};

const NomFoundationCrawlPage = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm<FormValues>();
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CrawlResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (values: FormValues) => {
    setRunning(true);
    setError(null);
    try {
      const response = await apiRequest<CrawlResult>("/api/nomfoundation/crawl-volume", {
        method: "POST",
        body: JSON.stringify({
          collection_id: values.collectionId,
          volume_id: values.volumeId,
          delay_seconds: values.delaySeconds,
          max_pages: values.maxPages,
          image_variant: values.imageVariant,
          save_to_system: values.saveToSystem,
          tree_id: values.treeId?.trim() || null,
          sync_pipeline: values.syncPipeline,
        }),
      });
      setResult(response);
      message.success(
        t("admin.developer.nomCrawlSuccess", { defaultValue: "Crawl Nom Foundation hoàn tất." }),
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Không thể crawl volume";
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
          {t("admin.developer.nomCrawlTitle", { defaultValue: "Crawl Nom Foundation" })}
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="!mb-0">
          {t("admin.developer.nomCrawlDesc", {
            defaultValue:
              "Tải ảnh scan, lưu MinIO và tạo cây gia phả (nom-{volume}) từ lib.nomfoundation.org. (208, 855, 1255, 1256",
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
              <Form.Item label="Volume ID" name="volumeId" rules={[{ required: true }]}>
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
              <Space size="large">
                <Form.Item name="saveToSystem" valuePropName="checked" className="!mb-0">
                  <Checkbox>
                    {t("admin.developer.nomSaveToSystem", { defaultValue: "Lưu MinIO + tạo cây gia phả" })}
                  </Checkbox>
                </Form.Item>
                <Form.Item name="syncPipeline" valuePropName="checked" className="!mb-0">
                  <Checkbox>
                    {t("admin.developer.nomSyncPipeline", { defaultValue: "Đồng bộ pipeline step ②" })}
                  </Checkbox>
                </Form.Item>
              </Space>
            </Col>
          </Row>
          <Button type="primary" htmlType="submit" icon={<PlayCircleOutlined />} loading={running}>
            {t("familyTree.run", { defaultValue: "Chạy" })}
          </Button>
        </Form>
      </Card>

      {result && (
        <Card title={t("admin.developer.crawlResult", { defaultValue: "Kết quả" })}>
          <Row gutter={16} className="mb-4">
            <Col xs={8}>
              <Statistic title="Ảnh tải" value={result.downloaded_pages} />
            </Col>
            <Col xs={8}>
              <Statistic title="Tổng trang" value={result.page_count} />
            </Col>
            <Col xs={8}>
              <Statistic title="Lỗi" value={result.errors} />
            </Col>
          </Row>
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Output">{result.output_dir}</Descriptions.Item>
            <Descriptions.Item label="Volume">
              collection/{result.collection_id}/volume/{result.volume_id}
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
                #{result.images_document_id} ({result.images_attached ?? 0} file)
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      )}
    </Space>
  );
};

export default NomFoundationCrawlPage;
