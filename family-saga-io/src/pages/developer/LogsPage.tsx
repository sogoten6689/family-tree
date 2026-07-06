import { DeleteOutlined, ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useMemo, useState } from "react";

import {
  type DeveloperApiLogEntry,
  clearDeveloperLogs,
  loadDeveloperLogs,
} from "@/lib/developerSettings";

const LogsPage = () => {
  const [logs, setLogs] = useState<DeveloperApiLogEntry[]>(() => loadDeveloperLogs());

  const refresh = useCallback(() => {
    setLogs(loadDeveloperLogs());
  }, []);

  const errorLogs = useMemo(() => logs.filter((item) => item.status >= 400), [logs]);

  const columns: ColumnsType<DeveloperApiLogEntry> = [
    {
      title: "Thời gian",
      dataIndex: "timestamp",
      width: 190,
      render: (value: string) => new Date(value).toLocaleString("vi-VN"),
    },
    {
      title: "Method",
      dataIndex: "method",
      width: 90,
    },
    {
      title: "Path",
      dataIndex: "path",
      ellipsis: true,
    },
    {
      title: "Status",
      dataIndex: "status",
      width: 90,
      render: (status: number) => (
        <Tag color={status >= 500 ? "red" : status >= 400 ? "orange" : "green"}>{status}</Tag>
      ),
    },
    {
      title: "API code",
      dataIndex: "apiCode",
      width: 100,
      render: (value?: string) => value ?? "—",
    },
    {
      title: "Message",
      dataIndex: "message",
      ellipsis: true,
    },
  ];

  const renderTable = (data: DeveloperApiLogEntry[]) => (
    <Table
      rowKey="id"
      size="small"
      columns={columns}
      dataSource={data}
      pagination={{ pageSize: 10, showSizeChanger: true }}
      locale={{ emptyText: "Chưa có log. Log sẽ được ghi khi gọi API OCR từ frontend." }}
    />
  );

  return (
    <Space direction="vertical" size="large" className="w-full">
      <Alert
        type="info"
        showIcon
        message="Developer logs (local)"
        description="Lưu tối đa 200 bản ghi gần nhất trên trình duyệt. Dùng để debug nhanh HTTP 400/502 từ pipeline Kim Hán Nôm."
      />

      <Card
        title="Lịch sử request OCR / API"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={refresh}>
              Làm mới
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                clearDeveloperLogs();
                refresh();
              }}
            >
              Xóa log
            </Button>
          </Space>
        }
      >
        <Tabs
          items={[
            { key: "all", label: `Tất cả (${logs.length})`, children: renderTable(logs) },
            {
              key: "errors",
              label: `Lỗi (${errorLogs.length})`,
              children: renderTable(errorLogs),
            },
          ]}
        />
        <Typography.Paragraph type="secondary" className="!mb-0 mt-4">
          Ghi log từ code:{" "}
          <Typography.Text code>appendDeveloperLog(&#123; method, path, status, message &#125;)</Typography.Text>
        </Typography.Paragraph>
      </Card>
    </Space>
  );
};

export default LogsPage;
