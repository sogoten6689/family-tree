import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Empty, Segmented, Space, Table, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";

import { getGeminiUsage, thinkingShare, type GeminiUsageSummary, type GeminiUsageTask } from "@/lib/settingsApi";

const TASK_LABELS: Record<string, string> = {
  ocr_vision: "OCR ảnh",
  translate: "Dịch nghĩa",
  tree_extract: "Dựng cây",
  ma_dinh_danh: "Trích mã định danh",
  generic: "Khác",
};

const fmt = (n: number) => n.toLocaleString("vi-VN");

/**
 * Số token Gemini theo loại việc (bảng gemini_usage — mỗi lần gọi Gemini được
 * ghi lại). Dùng để đo chi phí thật trước khi tối ưu: tỉ lệ token thinking cao
 * → nên giảm/tắt thinking cho việc máy móc. Chỉ Admin.
 */
export function GeminiUsageCard() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<GeminiUsageSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getGeminiUsage(days));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được số liệu Gemini");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    void load();
  }, [load]);

  const share = data ? thinkingShare(data) : null;

  return (
    <Card
      title="Chi phí Gemini (token)"
      extra={
        <Space>
          <Segmented
            value={days}
            onChange={(value) => setDays(Number(value))}
            options={[
              { label: "7 ngày", value: 7 },
              { label: "30 ngày", value: 30 },
              { label: "90 ngày", value: 90 },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading} aria-label="Tải lại số liệu" />
        </Space>
      }
    >
      {error && <Alert type="warning" showIcon className="mb-4" message={error} />}
      {data && data.total_calls === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={`Chưa có lượt gọi Gemini nào trong ${data.days} ngày (bắt đầu ghi từ 03/10/2026).`}
        />
      ) : data ? (
        <Space direction="vertical" className="w-full">
          <Typography.Text>
            {fmt(data.total_calls)} lượt gọi · {fmt(data.total_tokens)} token
            {share !== null && (
              <>
                {" · "}
                <Typography.Text strong={share >= 0.3} type={share >= 0.3 ? "warning" : undefined}>
                  thinking chiếm {Math.round(share * 100)}%
                </Typography.Text>
              </>
            )}
          </Typography.Text>
          <Table<GeminiUsageTask>
            rowKey="task"
            size="small"
            pagination={false}
            loading={loading}
            dataSource={data.tasks}
            scroll={{ x: true }}
            columns={[
              { title: "Việc", dataIndex: "task", render: (task: string) => TASK_LABELS[task] ?? task },
              { title: "Lượt gọi", dataIndex: "calls", align: "right", render: fmt },
              {
                title: "Lỗi",
                dataIndex: "errors",
                align: "right",
                render: (n: number) => (n > 0 ? <Typography.Text type="danger">{fmt(n)}</Typography.Text> : 0),
              },
              { title: "Đầu vào", dataIndex: "prompt_tokens", align: "right", render: fmt },
              { title: "Đầu ra", dataIndex: "output_tokens", align: "right", render: fmt },
              { title: "Thinking", dataIndex: "thinking_tokens", align: "right", render: fmt },
              { title: "Tổng", dataIndex: "total_tokens", align: "right", render: (n: number) => <strong>{fmt(n)}</strong> },
              { title: "TB/lượt", dataIndex: "avg_tokens_per_call", align: "right", render: fmt },
              {
                title: "Thời gian TB",
                dataIndex: "avg_duration_ms",
                align: "right",
                render: (ms: number) => `${(ms / 1000).toFixed(1)} s`,
              },
            ]}
          />
          <Typography.Text type="secondary" className="text-xs">
            Số token lấy từ usage_metadata của Gemini. Giá tiền không tính ở đây — đối chiếu bảng giá hiện tại của
            Google cho model đang dùng.
          </Typography.Text>
        </Space>
      ) : null}
    </Card>
  );
}
