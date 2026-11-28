import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Card, Input, Select, Space, Statistic, Table, Tag, Typography, message } from "antd";
import { useCallback, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";
import { exportLlmReviewed, getLlmDataset, getLlmDatasets, type LlmDatasetSummary, type LlmSample } from "@/lib/llmSoatApi";

import { checkAnswer, currentAnswer, filterSamples, type SampleFilter } from "./llmSoat/check";
import SampleEditor from "./llmSoat/SampleEditor";
import { STATUS_COLOR, STATUS_LABEL } from "./llmSoat/ui";

/** Hỏi máy chủ mỗi ngần này mili giây; file .jsonl mới hoặc sinh lại sẽ tự hiện. */
export const REFRESH_MS = 3000;
const FILTER_KEYS = ["q", "st", "rel", "warn"] as const;

/**
 * Soát nhãn LLM (persons/relations) cho bộ tổng hợp và bộ VGP văn xuôi.
 * URL: ?bo=<id> chọn bộ, &mau=<idx> mở một mẫu, q/st/rel/warn là bộ lọc.
 */
export default function SoatLlmPage() {
  const { isAdmin } = useAuth();
  const [sp, setSp] = useSearchParams();
  const qc = useQueryClient();
  const bo = sp.get("bo");
  const mau = sp.get("mau");

  const list = useQuery({ queryKey: ["llm-soat"], queryFn: getLlmDatasets, refetchInterval: REFRESH_MS, enabled: isAdmin });
  const version = list.data?.version;
  const ds = useQuery({
    queryKey: ["llm-soat", bo, version],
    queryFn: () => getLlmDataset(bo!),
    enabled: isAdmin && !!bo && !!version,
    placeholderData: (prev) => prev,
  });
  const refresh = useCallback(() => void qc.invalidateQueries({ queryKey: ["llm-soat"] }), [qc]);

  const filter: SampleFilter = Object.fromEntries(FILTER_KEYS.map((k) => [k, sp.get(k) ?? undefined]));
  const filtered = useMemo(() => filterSamples(ds.data?.samples ?? [], filter), [ds.data, filter.q, filter.st, filter.rel, filter.warn]); // eslint-disable-line react-hooks/exhaustive-deps
  const setParam = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(sp);
    Object.entries(patch).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    setSp(next);
  };

  if (!isAdmin) {
    return <Alert type="info" showIcon title="Soát nhãn LLM" description="Trang này cần đăng nhập tài khoản admin." />;
  }
  if (list.error) return <Alert type="error" showIcon title="Không tải được danh sách bộ dữ liệu" description={String(list.error)} />;

  const header = (
    <Typography.Paragraph type="secondary">
      Nhãn soát lưu ở <code>&lt;file&gt;.reviews.json</code> cạnh file gốc, file gốc không bị sửa. Thêm hoặc sinh lại file
      <code> .jsonl</code> thì trang tự cập nhật.
    </Typography.Paragraph>
  );

  // ---------- danh sách bộ ----------
  if (!bo) {
    const groups = [...new Set((list.data?.datasets ?? []).map((d) => d.group))];
    return (
      <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
        <Typography.Title level={3} style={{ margin: 0 }}>Soát nhãn LLM</Typography.Title>
        {header}
        {list.data && !list.data.datasets.length && (
          <Alert type="info" showIcon title="Chưa có bộ dữ liệu"
            description="Chạy research/llm_extraction/generate_synthetic.py hoặc build_vgp_dataset.py; máy chủ cần thấy thư mục data/ (hoặc đặt LLM_SOAT_DIRS)." />
        )}
        {groups.map((g) => (
          <Card key={g} size="small" title={g}>
            <Table<LlmDatasetSummary>
              size="small"
              pagination={false}
              rowKey="id"
              loading={list.isLoading}
              dataSource={list.data?.datasets.filter((d) => d.group === g)}
              columns={[
                { title: "File", render: (_, d) => <Link to={`?bo=${d.id}`}>{d.label}</Link> },
                { title: "Mẫu", dataIndex: "mau" },
                { title: "Có quan hệ", dataIndex: "co_quan_he" },
                { title: "Người / mẫu", dataIndex: "nguoi_tb" },
                { title: "Đã soát", dataIndex: "da_soat" },
                { title: "Cần xem lại", dataIndex: "xem_lai" },
                { title: "Đã sửa nhãn", dataIndex: "da_sua" },
                { title: "Sửa lúc", render: (_, d) => new Date(d.mtime * 1000).toLocaleString("vi-VN") },
              ]}
            />
          </Card>
        ))}
      </Space>
    );
  }

  const samples = ds.data?.samples ?? [];
  const crumbs = (
    <Typography.Text>
      <Link to="?">Soát nhãn LLM</Link> / {mau == null ? ds.data?.label : <Link to={`?${withoutMau(sp)}`}>{ds.data?.label}</Link>}
      {mau != null && ` / mẫu ${Number(mau) + 1}`}
    </Typography.Text>
  );
  if (ds.error) return <Alert type="error" showIcon title="Không tải được bộ dữ liệu" description={String(ds.error)} />;

  // ---------- một mẫu ----------
  if (mau != null) {
    const sample = samples[Number(mau)];
    if (!sample) return <>{crumbs}</>;
    const pos = filtered.findIndex((s) => s.idx === sample.idx);
    const go = (s: LlmSample | undefined) => (s ? () => setParam({ mau: String(s.idx) }) : null);
    return (
      <Space orientation="vertical" size="small" style={{ width: "100%" }}>
        {crumbs}
        {pos >= 0 && <Typography.Text type="secondary">{pos + 1}/{filtered.length} theo bộ lọc</Typography.Text>}
        <SampleEditor key={sample.key} datasetId={bo} sample={sample} onSaved={refresh} onPrev={go(filtered[pos - 1])} onNext={go(filtered[pos + 1])} />
      </Space>
    );
  }

  // ---------- bảng mẫu ----------
  const reviewed = samples.filter((s) => s.review?.status === "da").length;
  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      {crumbs}
      <Typography.Text type="secondary" copyable>{ds.data?.path}</Typography.Text>
      <Space size="large" wrap>
        <Statistic title="Mẫu" value={samples.length} />
        <Statistic title="Có quan hệ" value={samples.filter((s) => currentAnswer(s)?.relations.length).length} />
        <Statistic title="Có cảnh báo" value={samples.filter((s) => checkAnswer(currentAnswer(s), s.input).length).length} />
        <Statistic title="Đã soát" value={reviewed} />
        <Statistic title="Đã sửa nhãn" value={samples.filter((s) => s.review?.answer).length} />
      </Space>
      <Space wrap>
        <Input.Search allowClear placeholder="Tìm chữ hoặc tên người" defaultValue={filter.q} onSearch={(v) => setParam({ q: v || null })} style={{ width: 280 }} />
        <Select style={{ width: 170 }} value={filter.st ?? ""} onChange={(v) => setParam({ st: v || null })}
          options={[{ value: "", label: "Mọi trạng thái" }, ...Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))]} />
        <Select style={{ width: 170 }} value={filter.rel ?? ""} onChange={(v) => setParam({ rel: v || null })}
          options={[{ value: "", label: "Có/không quan hệ" }, { value: "1", label: "Có quan hệ" }, { value: "0", label: "Không có quan hệ" }]} />
        <Select style={{ width: 190 }} value={filter.warn ?? ""} onChange={(v) => setParam({ warn: v || null })}
          options={[{ value: "", label: "Mọi mẫu" }, { value: "1", label: "Chỉ mẫu có cảnh báo" }]} />
        <Typography.Text type="secondary">{filtered.length} mẫu khớp</Typography.Text>
        <Button
          onClick={async () => {
            try {
              const r = await exportLlmReviewed(bo);
              message.success(`Đã ghi ${r.count} mẫu (${r.edited} đã sửa) → ${r.path}`, 6);
            } catch (e) {
              message.error(e instanceof Error ? e.message : "Xuất lỗi");
            }
          }}
        >
          Xuất bản đã soát (.reviewed.jsonl)
        </Button>
      </Space>
      {header}
      <Table<LlmSample>
        size="small"
        rowKey="idx"
        loading={ds.isLoading}
        dataSource={filtered}
        pagination={{ pageSize: 50, showSizeChanger: false }}
        columns={[
          { title: "#", width: 60, render: (_, s) => <Link to={`?${withParam(sp, "mau", String(s.idx))}`}>{s.idx + 1}</Link> },
          {
            title: "Đoạn văn",
            render: (_, s) => (
              <Link to={`?${withParam(sp, "mau", String(s.idx))}`} style={{ color: "inherit" }}>
                {s.input.slice(0, 160)}{s.input.length > 160 ? "…" : ""}
                {typeof s.meta?.tree_id === "number" && <Tag style={{ marginLeft: 6 }}>cây {s.meta.tree_id}</Tag>}
              </Link>
            ),
          },
          { title: "Người", width: 70, render: (_, s) => currentAnswer(s)?.persons.length ?? "–" },
          { title: "Quan hệ", width: 80, render: (_, s) => currentAnswer(s)?.relations.length ?? "–" },
          {
            title: "Cảnh báo",
            width: 90,
            render: (_, s) => {
              const n = checkAnswer(currentAnswer(s), s.input).length;
              return n ? <Tag color="orange">{n}</Tag> : null;
            },
          },
          {
            title: "Trạng thái",
            width: 170,
            render: (_, s) => {
              const st = s.review?.status ?? "chua";
              return (
                <>
                  <Tag color={STATUS_COLOR[st]}>{STATUS_LABEL[st]}</Tag>
                  {s.review?.answer && <Tag>đã sửa</Tag>}
                </>
              );
            },
          },
        ]}
      />
    </Space>
  );
}

function withParam(sp: URLSearchParams, k: string, v: string): string {
  const n = new URLSearchParams(sp);
  n.set(k, v);
  return n.toString();
}

function withoutMau(sp: URLSearchParams): string {
  const n = new URLSearchParams(sp);
  n.delete("mau");
  return n.toString();
}
