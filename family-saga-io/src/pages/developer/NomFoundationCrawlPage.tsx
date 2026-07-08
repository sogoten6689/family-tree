import { CloudDownloadOutlined, PlayCircleOutlined } from "@ant-design/icons";
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
  linkTreeId?: string;
};

type CrawlResult = {
  collection_id: number;
  volume_id: number;
  output_dir: string;
  downloaded_pages: number;
  page_count: number;
  errors: number;
};

const DEFAULT_VALUES: FormValues = {
  collectionId: 1,
  volumeId: 429,
  delaySeconds: 0.3,
  maxPages: 20,
  linkTreeId: "",
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
          link_tree_id: values.linkTreeId?.trim() || null,
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
              "Tải metadata và ảnh scan từ lib.nomfoundation.org (ví dụ volume 429 — Thuỵ Ứng gia phả).",
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
            <Col xs={24} sm={12} md={12}>
              <Form.Item
                label={t("admin.developer.linkTreeId", { defaultValue: "Gắn cây (vgp-100)" })}
                name="linkTreeId"
              >
                <Input placeholder="vgp-100" allowClear />
              </Form.Item>
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
          </Descriptions>
        </Card>
      )}
    </Space>
  );
};

export default NomFoundationCrawlPage;
