import { CloudServerOutlined, DatabaseOutlined, ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Descriptions, Space, Spin, Tabs, Tag, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";

import { getBackendBaseUrl } from "@/lib/apiClient";

interface HealthPayload {
  status?: string;
  auth_storage?: string;
  tree_storage?: string;
}

const DOCKER_SERVICES = [
  { name: "family-tree-nginx", port: "87", role: "Reverse proxy Docker" },
  { name: "family-tree-frontend", port: "5174", role: "SPA static" },
  { name: "family-tree-backend", port: "8002", role: "FastAPI" },
  { name: "family-tree-mysql", port: "3309", role: "MySQL 8.4" },
  { name: "family-tree-minio", port: "9002 / 9003", role: "MinIO API / Console" },
];

const StoragePage = () => {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const minioPublic = import.meta.env.VITE_MINIO_PUBLIC_ENDPOINT ?? "(qua backend presigned URL)";
  const backendUrl = getBackendBaseUrl() || window.location.origin;

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    setHealthError(null);
    try {
      const response = await fetch(`${backendUrl}/health`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setHealth((await response.json()) as HealthPayload);
    } catch (error) {
      setHealth(null);
      setHealthError(error instanceof Error ? error.message : "Không thể kết nối backend");
    } finally {
      setLoading(false);
    }
  }, [backendUrl]);

  useEffect(() => {
    void fetchHealth();
  }, [fetchHealth]);

  return (
    <Space direction="vertical" size="large" className="w-full">
      <Alert
        type="warning"
        showIcon
        message="Thông tin hạ tầng"
        description="Trang này hiển thị cấu hình tham chiếu và trạng thái backend. Trạng thái Docker container chi tiết cần SSH vào VPS (docker compose ps)."
      />

      <Tabs
        items={[
          {
            key: "minio",
            label: "MinIO / S3",
            children: (
              <Card title="Kết nối lưu trữ" extra={<DatabaseOutlined />}>
                <Descriptions bordered column={1}>
                  <Descriptions.Item label="MINIO_PUBLIC_ENDPOINT">{minioPublic}</Descriptions.Item>
                  <Descriptions.Item label="MINIO_BUCKET">family-tree-docs</Descriptions.Item>
                  <Descriptions.Item label="Backend proxy">{backendUrl}</Descriptions.Item>
                  <Descriptions.Item label="Upload API">
                    POST /api/documents/&#123;id&#125;/upload-files
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
          {
            key: "backend",
            label: "Backend Health",
            children: (
              <Card
                title="Trạng thái API"
                extra={
                  <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void fetchHealth()}>
                    Làm mới
                  </Button>
                }
              >
                {loading && !health ? (
                  <Spin />
                ) : healthError ? (
                  <Alert type="error" message={healthError} />
                ) : (
                  <Descriptions bordered column={1}>
                    <Descriptions.Item label="status">
                      <Tag color="green">{health?.status ?? "unknown"}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="auth_storage">{health?.auth_storage}</Descriptions.Item>
                    <Descriptions.Item label="tree_storage">{health?.tree_storage}</Descriptions.Item>
                  </Descriptions>
                )}
              </Card>
            ),
          },
          {
            key: "docker",
            label: "Docker (VPS)",
            children: (
              <Card title="Stack docker-compose" extra={<CloudServerOutlined />}>
                <Typography.Paragraph type="secondary">
                  Kiểm tra trên VPS:{" "}
                  <Typography.Text code>docker compose ps -a</Typography.Text>
                </Typography.Paragraph>
                <Descriptions bordered column={2} size="small">
                  {DOCKER_SERVICES.map((svc) => (
                    <Descriptions.Item key={svc.name} label={svc.name} span={2}>
                      Port {svc.port} — {svc.role}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
            ),
          },
        ]}
      />
    </Space>
  );
};

export default StoragePage;
