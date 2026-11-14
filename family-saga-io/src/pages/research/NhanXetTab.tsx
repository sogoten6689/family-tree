import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Card, Empty, Input, InputNumber, Select, Space, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";

import { getNhanXet, saveNhanXet, type BookDetail, type LoaiNhanXet, type MucNhanXet, type NhanXet } from "@/lib/doiChieuApi";

import { LOAI_LABEL, TRANG_THAI_LABEL, buildMessage } from "./nhanXet";

const TRANG_THAI_COLOR: Record<NhanXet["trang_thai"], string> = { nhap: "default", da_duyet: "blue", da_gui: "green" };

/** Nhận xét gửi sinh viên cho cuốn đang xem: soạn, duyệt, sao chép tin nhắn. Chỉ admin thấy thẻ này. */
const NhanXetTab = ({ detail, onShowLine }: { detail: BookDetail; onShowLine: (line: number) => void }) => {
  const { student, book } = detail;
  const queryClient = useQueryClient();
  const { data, error, isLoading } = useQuery({ queryKey: ["nhan-xet", student, book], queryFn: () => getNhanXet(student, book) });
  const [draft, setDraft] = useState<NhanXet | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (data && !dirty) setDraft(data);
  }, [data, dirty]);

  const pairsByLine = useMemo(() => new Map(detail.pairs.map((p) => [p.line, p])), [detail.pairs]);

  if (error) return <Alert type="error" showIcon title="Không tải được nhận xét" description={String(error)} />;
  if (isLoading || !draft) return <Card loading />;

  const edit = (patch: Partial<NhanXet>) => {
    setDraft({ ...draft, ...patch });
    setDirty(true);
    setCopied(false);
  };
  const editItem = (i: number, patch: Partial<MucNhanXet>) => edit({ muc: draft.muc.map((m, j) => (j === i ? { ...m, ...patch } : m)) });

  const save = async () => {
    setSaving(true);
    setProblem(null);
    try {
      const muc = draft.muc.filter((m) => m.noi_dung.trim());
      const saved = await saveNhanXet(student, book, { ...draft, muc });
      queryClient.setQueryData(["nhan-xet", student, book], saved);
      setDraft(saved);
      setDirty(false);
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const message = buildMessage(draft);
  const copy = async () => {
    await navigator.clipboard.writeText(message);
    setCopied(true);
  };

  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <Space wrap>
        <Select<NhanXet["trang_thai"]>
          aria-label="Trạng thái nhận xét"
          value={draft.trang_thai}
          onChange={(v) => edit({ trang_thai: v })}
          style={{ width: 200 }}
          options={(Object.keys(TRANG_THAI_LABEL) as NhanXet["trang_thai"][]).map((v) => ({ value: v, label: TRANG_THAI_LABEL[v] }))}
        />
        <Button type="primary" onClick={save} loading={saving} disabled={!dirty}>
          Lưu nhận xét
        </Button>
        <Button onClick={copy} disabled={!message}>
          {copied ? "Đã sao chép" : "Sao chép tin nhắn"}
        </Button>
        <Tag color={TRANG_THAI_COLOR[draft.trang_thai]}>{TRANG_THAI_LABEL[draft.trang_thai]}</Tag>
        {draft.luu_luc && (
          <Typography.Text type="secondary">
            Lưu lúc {new Date(draft.luu_luc).toLocaleString("vi-VN")}
            {draft.nguoi_sua ? ` · ${draft.nguoi_sua}` : ""}
          </Typography.Text>
        )}
        {dirty && <Typography.Text type="warning">Chưa lưu</Typography.Text>}
      </Space>
      {problem && <Alert type="error" showIcon title={problem} />}
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Chỉ admin xem được nhận xét; trang đối chiếu công khai không hiện phần này. Mục có số dòng sẽ kèm cặp câu tương ứng; bấm "Xem trong
        bảng" để nhảy tới cặp đó.
      </Typography.Paragraph>

      <Typography.Text strong>Mở đầu</Typography.Text>
      <Input.TextArea aria-label="Mở đầu" autoSize={{ minRows: 2 }} value={draft.mo_dau} onChange={(e) => edit({ mo_dau: e.target.value })} />

      <Typography.Text strong>Cần sửa ({draft.muc.length})</Typography.Text>
      {draft.muc.length === 0 && <Empty description="Chưa có mục nào" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
      {draft.muc.map((m, i) => {
        const pair = m.dong ? pairsByLine.get(m.dong) : undefined;
        return (
          <Card key={i} size="small" data-testid="muc-nhan-xet" title={`Mục ${i + 1}`}
            extra={
              <Button size="small" danger type="text" onClick={() => edit({ muc: draft.muc.filter((_, j) => j !== i) })}>
                Xoá
              </Button>
            }
          >
            <Space orientation="vertical" style={{ width: "100%" }}>
              <Space wrap>
                <InputNumber
                  aria-label={`Dòng của mục ${i + 1}`}
                  placeholder="Dòng"
                  min={1}
                  value={m.dong ?? null}
                  onChange={(v) => editItem(i, { dong: v ?? null })}
                />
                <Select<LoaiNhanXet>
                  aria-label={`Loại lỗi của mục ${i + 1}`}
                  value={m.loai}
                  onChange={(v) => editItem(i, { loai: v })}
                  style={{ width: 200 }}
                  options={(Object.keys(LOAI_LABEL) as LoaiNhanXet[]).map((v) => ({ value: v, label: LOAI_LABEL[v] }))}
                />
                {m.dong && pair && (
                  <Button size="small" onClick={() => onShowLine(m.dong!)}>
                    Xem trong bảng
                  </Button>
                )}
              </Space>
              {m.dong && !pair && <Typography.Text type="warning">Bài nộp không có dòng {m.dong}.</Typography.Text>}
              {pair && (
                <div style={{ background: "#fafafa", padding: 8, borderRadius: 4 }}>
                  <div lang="zh-Hant" style={{ fontSize: 16 }}>
                    {pair.han}
                  </div>
                  <Typography.Text type="secondary">{pair.viet}</Typography.Text>
                </div>
              )}
              <Input.TextArea
                aria-label={`Nội dung mục ${i + 1}`}
                autoSize={{ minRows: 2 }}
                value={m.noi_dung}
                onChange={(e) => editItem(i, { noi_dung: e.target.value })}
              />
            </Space>
          </Card>
        );
      })}
      <Button onClick={() => edit({ muc: [...draft.muc, { dong: null, loai: "khac", noi_dung: "" }] })}>+ Thêm mục</Button>

      <Typography.Text strong>Lời kết</Typography.Text>
      <Input.TextArea aria-label="Lời kết" autoSize={{ minRows: 1 }} value={draft.ket} onChange={(e) => edit({ ket: e.target.value })} />

      <Typography.Text strong>Tin nhắn sẽ gửi</Typography.Text>
      <Card size="small">
        <div data-testid="tin-nhan" style={{ whiteSpace: "pre-wrap" }}>
          {message || <Typography.Text type="secondary">Chưa có nội dung.</Typography.Text>}
        </div>
      </Card>
    </Space>
  );
};

export default NhanXetTab;
