import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, Input, InputNumber, Row, Select, Space, Table, Tag, Typography, message } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getLlmPhaHe,
  putLlmReview,
  REL_TYPES,
  type Gender,
  type LlmAnswer,
  type LlmPerson,
  type LlmSample,
  type RelType,
  type ReviewStatus,
} from "@/lib/llmSoatApi";

import { addInverse, checkAnswer, removePerson, renamePerson } from "./check";
import TreeView, { Highlight } from "./TreeView";
import { STATUS_COLOR, STATUS_LABEL } from "./ui";

const EMPTY: LlmAnswer = { persons: [], relations: [] };
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

interface Props {
  datasetId: string;
  sample: LlmSample;
  onSaved: () => void;
  onPrev: (() => void) | null;
  onNext: (() => void) | null;
}

/** Soát một mẫu: tô tên, vẽ cây, đối chiếu sơ đồ gốc, sửa người/quan hệ, lưu vào <file>.reviews.json. */
export default function SampleEditor({ datasetId, sample, onSaved, onPrev, onNext }: Props) {
  const original = sample.answer ?? EMPTY;
  const saved = sample.review?.answer ?? original;
  const savedStatus = sample.review?.status ?? "chua";
  const savedNote = sample.review?.note ?? "";
  const [ans, setAns] = useState<LlmAnswer>(saved);
  const [status, setStatus] = useState<ReviewStatus>(savedStatus);
  const [note, setNote] = useState(savedNote);
  const [focus, setFocus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const dirty = !same(ans, saved) || status !== savedStatus || note !== savedNote;

  // Dữ liệu trên máy chủ đổi (tự làm mới) mà chưa sửa gì thì nhận bản mới; đang sửa thì giữ.
  useEffect(() => {
    if (!dirty) {
      setAns(saved);
      setStatus(savedStatus);
      setNote(savedNote);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sample.review?.updated_at, sample.answer]);

  const warns = useMemo(() => checkAnswer(ans, sample.input), [ans, sample.input]);
  const names = ans.persons.map((p) => p.name);
  const treeId = typeof sample.meta?.tree_id === "number" ? sample.meta.tree_id : null;
  const phaHe = useQuery({
    queryKey: ["llm-pha-he", datasetId, treeId, names.join("|")],
    queryFn: () => getLlmPhaHe(datasetId, treeId!, names),
    enabled: treeId != null && names.length > 0,
  });
  const psrc = sample.meta?.person_src ?? {};
  const rsrc = sample.meta?.relation_src ?? {};

  const save = useCallback(
    async (st: ReviewStatus, go?: (() => void) | null) => {
      setSaving(true);
      try {
        await putLlmReview(datasetId, sample.key, { status: st, note: note || null, answer: same(ans, original) ? null : ans });
        setStatus(st);
        message.success("Đã lưu");
        onSaved();
        go?.();
      } catch (e) {
        message.error(e instanceof Error ? e.message : "Lưu lỗi");
      } finally {
        setSaving(false);
      }
    },
    [ans, original, note, datasetId, sample.key, onSaved],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = (e.target as HTMLElement | null)?.closest("input,textarea,.ant-select");
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        void save(status);
      } else if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        void save("da", onNext);
      } else if (!typing && e.altKey && e.key === "ArrowRight") onNext?.();
      else if (!typing && e.altKey && e.key === "ArrowLeft") onPrev?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [save, status, onNext, onPrev]);

  const setPerson = (i: number, patch: Partial<LlmPerson>) =>
    setAns((a) => ({ ...a, persons: a.persons.map((p, k) => (k === i ? { ...p, ...patch } : p)) }));
  const addPerson = (name = "") =>
    setAns((a) => ({
      ...a,
      persons: [...a.persons, { name, birth: null, death: null, generation: null, gender: / thị /i.test(` ${name} `) ? "female" : null }],
    }));
  const addFromSelection = () => {
    const s = window.getSelection()?.toString().trim().replace(/\s+/g, " ");
    if (!s) message.info("Hãy bôi đen một tên trong đoạn văn trước");
    else if (names.includes(s)) message.info("Người này đã có");
    else addPerson(s);
  };
  const setRel = (i: number, patch: Partial<{ from: string; to: string; type: RelType }>) =>
    setAns((a) => ({ ...a, relations: a.relations.map((r, k) => (k === i ? { ...r, ...patch } : r)) }));

  const nameOptions = names.map((n) => ({ value: n, label: n }));

  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Space wrap>
        <Button onClick={onPrev ?? undefined} disabled={!onPrev}>← Trước</Button>
        <Button onClick={onNext ?? undefined} disabled={!onNext}>Sau →</Button>
        <Tag color={STATUS_COLOR[status]}>{STATUS_LABEL[status]}</Tag>
        {sample.review?.answer && <Tag>nhãn đã sửa</Tag>}
        {treeId != null && <Tag>cây VGP {treeId}</Tag>}
        {dirty && <Typography.Text type="warning">● chưa lưu</Typography.Text>}
        <Button onClick={() => save(status)} disabled={!dirty} loading={saving} title="Ctrl/⌘ + S">Lưu</Button>
        <Button onClick={() => save("xem_lai")} loading={saving}>Cần xem lại</Button>
        <Button type="primary" onClick={() => save("da", onNext)} loading={saving} title="Ctrl/⌘ + Enter">
          ✓ Đã soát, sang mẫu sau
        </Button>
        <Button type="text" onClick={() => setAns(original)} disabled={same(ans, original)}>Khôi phục nhãn gốc</Button>
      </Space>

      <Row gutter={16}>
        <Col xs={24} xl={12}>
          <Card size="small" title="Đoạn văn" extra={<Button size="small" onClick={addFromSelection}>+ Thêm người từ chữ bôi đen</Button>}>
            <Highlight text={sample.input} persons={ans.persons} focus={focus} />
          </Card>
          {treeId != null && (
            <Card size="small" title="Sơ đồ gốc (pha_he) có nhắc các tên này" style={{ marginTop: 16 }}>
              {phaHe.error ? (
                <Typography.Text type="secondary">Không đọc được sơ đồ gốc.</Typography.Text>
              ) : (
                <>
                  <Typography.Text type="secondary">
                    {phaHe.data ? `${phaHe.data.lines.length} / ${phaHe.data.total} dòng · số đầu dòng = đời.thứ tự` : "Đang tải…"}
                  </Typography.Text>
                  <pre style={{ fontSize: 13, whiteSpace: "pre-wrap", maxHeight: 260, overflow: "auto", margin: "8px 0 0" }}>
                    {phaHe.data?.lines.join("\n") || ""}
                  </pre>
                </>
              )}
            </Card>
          )}
          <Input.TextArea style={{ marginTop: 16 }} rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ghi chú khi soát (tùy chọn)" />
        </Col>
        <Col xs={24} xl={12}>
          <Card size="small" title="Cây">
            <div style={{ overflow: "auto", maxHeight: 560 }}>
              <TreeView answer={ans} focus={focus} onPick={setFocus} />
            </div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              <span style={{ color: "#2f6fb5" }}>━ cha</span> · <span style={{ color: "#c2417a" }}>━ mẹ</span> ·{" "}
              <span style={{ color: "#b8860b" }}>┅ vợ chồng</span> · bấm vào ô để tô tên trong đoạn văn
            </Typography.Text>
          </Card>
          {warns.length > 0 && (
            <Alert style={{ marginTop: 16 }} type="warning" showIcon title={`Cảnh báo (${warns.length})`}
              description={<ul style={{ margin: 0, paddingLeft: 18 }}>{warns.map((w) => <li key={w}>{w}</li>)}</ul>} />
          )}
        </Col>
      </Row>

      <Card size="small" title={`Người (${ans.persons.length})`} extra={<Button size="small" onClick={() => addPerson()}>+ Thêm người</Button>}>
        <Table<LlmPerson & { _i: number }>
          size="small"
          pagination={false}
          rowKey="_i"
          scroll={{ x: "max-content" }}
          dataSource={ans.persons.map((p, i) => ({ ...p, _i: i }))}
          onRow={(r) => ({ onMouseEnter: () => setFocus(r.name) })}
          columns={[
            { title: "Họ tên", render: (_, r) => <Input style={{ minWidth: 220 }} value={r.name} onChange={(e) => setAns((a) => renamePerson(a, r._i, e.target.value))} /> },
            ...(["birth", "death", "generation"] as const).map((f) => ({
              title: { birth: "Sinh", death: "Mất", generation: "Đời" }[f],
              width: 90,
              render: (_: unknown, r: LlmPerson & { _i: number }) => (
                <InputNumber value={r[f]} style={{ width: 80 }} onChange={(v) => setPerson(r._i, { [f]: v ?? null })} />
              ),
            })),
            {
              title: "Giới",
              width: 100,
              render: (_, r) => (
                <Select value={r.gender ?? ""} style={{ width: 84 }} onChange={(v) => setPerson(r._i, { gender: (v || null) as Gender })}
                  options={[{ value: "", label: "?" }, { value: "male", label: "nam" }, { value: "female", label: "nữ" }]} />
              ),
            },
            { title: "Nguồn", width: 100, render: (_, r) => (psrc[r.name] ? <Tag>{psrc[r.name]}</Tag> : null) },
            {
              width: 48,
              render: (_, r) => (
                <Button type="text" danger title="Xoá người và các quan hệ của người này" onClick={() => setAns((a) => removePerson(a, r._i))}>✕</Button>
              ),
            },
          ]}
        />
      </Card>

      <Card
        size="small"
        title={`Quan hệ (${ans.relations.length})`}
        extra={
          <Space>
            <Button size="small" disabled={names.length < 2}
              onClick={() => setAns((a) => ({ ...a, relations: [...a.relations, { from: names[0], to: names[1], type: "father" }] }))}>
              + Thêm quan hệ
            </Button>
            <Button size="small" onClick={() => setAns(addInverse)} title="Từ father/mother sinh son/daughter (cần biết giới tính của con)">
              Tự thêm quan hệ ngược
            </Button>
          </Space>
        }
      >
        <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
          Đọc là: «Từ» là «quan hệ» của «Đến». Ví dụ A father B = A là cha của B.
        </Typography.Paragraph>
        <Table
          size="small"
          pagination={false}
          rowKey={(_, i) => String(i)}
          dataSource={ans.relations.map((r, i) => ({ ...r, _i: i }))}
          columns={[
            { title: "Từ", render: (_, r) => <Select value={r.from} style={{ minWidth: 200 }} options={nameOptions} onChange={(v) => setRel(r._i, { from: v })} /> },
            { title: "là … của", width: 130, render: (_, r) => <Select value={r.type} style={{ width: 116 }} options={REL_TYPES.map((t) => ({ value: t, label: t }))} onChange={(v) => setRel(r._i, { type: v })} /> },
            { title: "Đến", render: (_, r) => <Select value={r.to} style={{ minWidth: 200 }} options={nameOptions} onChange={(v) => setRel(r._i, { to: v })} /> },
            { title: "Nguồn", width: 130, render: (_, r) => { const s = rsrc[`${r.from}|${r.to}|${r.type}`]; return s ? <Tag>{s}</Tag> : null; } },
            {
              width: 48,
              render: (_, r) => (
                <Button type="text" danger onClick={() => setAns((a) => ({ ...a, relations: a.relations.filter((_, k) => k !== r._i) }))}>✕</Button>
              ),
            },
          ]}
        />
      </Card>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        Phím tắt: Ctrl/⌘ S lưu · Ctrl/⌘ Enter đã soát và sang mẫu sau · Alt ←/→ mẫu trước/sau
      </Typography.Text>
    </Space>
  );
}
