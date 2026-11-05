import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Checkbox, Input, Popconfirm, Segmented, Select, Space, Tag, Typography } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";

import { getKhung, getSoat, nopSoat, pageImageUrl, saveSoat, type BookDetail, type NopResult } from "@/lib/doiChieuApi";

import { draftChars } from "./lopPhu";
import SoatOverlay, { BAN_TAM_KEY, type OverlayMode } from "./SoatOverlay";
import { countSubmittable, mergeWithNext, newRow, splitRow, stripKeys, withKeys, type EditRow } from "./soatRows";

type Carets = Record<number, { han?: number; viet?: number }>;

const rowInputId = (key: number) => `soat-han-${key}`;
const rowVietId = (key: number) => `soat-viet-${key}`;

const SoatTab = ({ detail }: { detail: BookDetail }) => {
  const { student, book } = detail;
  const queryClient = useQueryClient();
  const { data, error, isLoading } = useQuery({
    queryKey: ["soat", student, book],
    queryFn: () => getSoat(student, book),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    retry: false,
  });

  const [rows, setRows] = useState<EditRow[] | null>(null);
  const [confirmed, setConfirmed] = useState<string[]>([]);
  const [version, setVersion] = useState(0);
  const [banTam, setBanTam] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [result, setResult] = useState<NopResult | null>(null);
  const [view, setView] = useState<OverlayMode>("anh");
  const [marks, setMarks] = useState(true);
  const carets = useRef<Carets>({});

  useEffect(() => {
    if (!data || rows) return;
    const loaded = withKeys(data.rows);
    setRows(loaded);
    setConfirmed(data.da_soat);
    setVersion(data.phien_ban);
    setBanTam(data.ban_tam ?? {});
    setPage(detail.pages[0] ?? loaded[0]?.trang ?? null);
  }, [data, rows, detail.pages]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const pages = useMemo(() => {
    const seen = new Set(detail.pages);
    (rows ?? []).forEach((r) => seen.add(r.trang));
    return [...seen].sort();
  }, [detail.pages, rows]);

  const { data: khung } = useQuery({
    queryKey: ["soat-khung", student, book, page],
    queryFn: () => getKhung(student, book, page as string),
    enabled: !!page,
    staleTime: Infinity,
    retry: false,
  });

  // Gồm cả trang kề để theo được câu đã ghép qua trang.
  const overlayDraft = useMemo(() => {
    const i = page ? pages.indexOf(page) : -1;
    const near = new Set(pages.slice(Math.max(i - 1, 0), i + 2));
    return draftChars((rows ?? []).filter((r) => near.has(r.trang)));
  }, [rows, page, pages]);

  if (isLoading) return <Typography.Text type="secondary">Đang tải nháp…</Typography.Text>;
  if (error) return <Alert type="error" showIcon title="Không mở được thẻ Soát" description={String(error)} />;
  if (!rows) return null;
  if (!rows.length && !detail.pages.length) return <Typography.Text type="secondary">Cuốn này chưa có bản máy để soát.</Typography.Text>;

  const edit = (next: EditRow[]) => {
    setRows(next);
    setDirty(true);
  };
  const patch = (key: number, change: Partial<EditRow>) => edit(rows.map((r) => (r.key === key ? { ...r, ...change } : r)));

  const persist = async (): Promise<boolean> => {
    if (!dirty) return true;
    setBusy(true);
    try {
      const saved = await saveSoat(student, book, { rows: stripKeys(rows), da_soat: confirmed, phien_ban: version, ban_tam: banTam });
      setVersion(saved.phien_ban);
      setDirty(false);
      setProblem(null);
      return true;
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const goTo = async (next: string) => {
    if (await persist()) setPage(next);
  };

  const submit = async () => {
    setResult(null);
    if (!(await persist())) return;
    setBusy(true);
    try {
      setResult(await nopSoat(student, book));
      await queryClient.invalidateQueries({ queryKey: ["doi-chieu"] });
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const pageIndex = page ? pages.indexOf(page) : -1;
  const pageRows = rows.filter((r) => r.trang === page);
  const isConfirmed = page != null && confirmed.includes(page);
  const toSubmit = countSubmittable(rows, confirmed);
  const machineBanTam = khung?.ban_tam?.text;
  const pageBanTam = (page != null ? banTam[page] : undefined) ?? machineBanTam ?? "";
  const gutterMissing = khung?.ban_tam?.thieu ?? 0;

  const addRowToPage = () => {
    if (!page) return;
    const lastIndex = rows.map((r) => r.trang).lastIndexOf(page);
    const before = rows.filter((r) => r.trang <= page).length;
    const at = lastIndex >= 0 ? lastIndex + 1 : before;
    edit([...rows.slice(0, at), newRow(page), ...rows.slice(at)]);
  };

  return (
    <Space orientation="vertical" style={{ width: "100%" }} size="middle">
      <Space wrap>
        <Button disabled={pageIndex <= 0 || busy} onClick={() => void goTo(pages[pageIndex - 1])}>
          ← Trang trước
        </Button>
        <Select
          aria-label="Chọn trang"
          value={page}
          disabled={busy}
          style={{ width: 210 }}
          onChange={(p) => void goTo(p)}
          options={pages.map((p) => ({
            value: p,
            label: `Trang ${p} · ${rows.filter((r) => r.trang === p).length} dòng${confirmed.includes(p) ? " ✓" : ""}`,
          }))}
        />
        <Button disabled={pageIndex < 0 || pageIndex >= pages.length - 1 || busy} onClick={() => void goTo(pages[pageIndex + 1])}>
          Trang sau →
        </Button>
        <Button onClick={() => void persist()} disabled={!dirty || busy}>
          {dirty ? "Lưu nháp" : "Đã lưu"}
        </Button>
        <Popconfirm
          title={`Nộp ${toSubmit} cặp từ ${confirmed.length} trang đã xác nhận?`}
          description="Trang chưa xác nhận không được tính. Có thể sửa và nộp lại, bản cũ vẫn được giữ."
          okText="Nộp"
          cancelText="Chưa"
          disabled={!toSubmit || busy}
          onConfirm={() => void submit()}
        >
          <Button type="primary" disabled={!toSubmit || busy}>
            Nộp {toSubmit} cặp
          </Button>
        </Popconfirm>
      </Space>

      {problem && <Alert type="error" showIcon closable title={problem} onClose={() => setProblem(null)} />}
      {result?.nop && <Alert type="success" showIcon title={`Đã nộp ${result.so_cap} cặp vào ${result.tsv}.`} />}
      {result && !result.nop && (
        <Alert
          type="warning"
          showIcon
          title={result.ly_do ?? "Chưa nộp được."}
          description={
            result.loi.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {result.loi.map((e, i) => (
                  <li key={i}>
                    <Button type="link" size="small" style={{ padding: 0 }} onClick={() => void goTo(e.trang)}>
                      Trang {e.trang}
                    </Button>{" "}
                    <span lang="zh-Hant">{e.han.slice(0, 24) || "(vế Hán trống)"}</span>: {e.loi.join("; ")}
                  </li>
                ))}
              </ul>
            )
          }
        />
      )}

      {page && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-start" }}>
          <div
            style={{
              flex: view === "song" ? "1 1 100%" : view === "anh" ? "1 1 380px" : "2 1 560px",
              minWidth: 0,
              position: view === "song" ? "static" : "sticky",
              top: 8,
            }}
          >
            <Space wrap style={{ marginBottom: 8 }}>
              <Segmented<OverlayMode>
                value={view}
                onChange={setView}
                options={[
                  { value: "anh", label: "Ảnh gốc" },
                  { value: "keo", label: "Kéo so sánh" },
                  { value: "song", label: "Xem song song" },
                  { value: "dich", label: "Kéo bản dịch" },
                ]}
              />
              <Checkbox checked={marks} onChange={(e) => setMarks(e.target.checked)}>
                Hiện ô chữ và số dòng
              </Checkbox>
            </Space>
            {!detail.pages.includes(page) ? (
              <Typography.Text type="secondary">Trang này không có ảnh.</Typography.Text>
            ) : (
              <>
                {khung === null && view !== "anh" && view !== "dich" && (
                  <Alert type="info" showIcon style={{ marginBottom: 8 }} title="Trang này chưa có dữ liệu vị trí chữ." />
                )}
                {khung && (
                  <Typography.Paragraph type="secondary" style={{ margin: "0 0 8px" }}>
                    Ô chữ do máy tách, ảnh gốc vẫn là chuẩn; ô nét đứt là vị trí ước lượng. Số màu xanh là số dòng ở phần soát.
                    {(view === "keo" || view === "song") && (
                      <>
                        {" "}Chữ <span style={{ color: "#d4380d" }}>đỏ</span> là chữ đã sửa so với bản máy. Bấm vào chữ để tới dòng của nó.
                      </>
                    )}
                    {view === "dich" && " Bấm vào một dòng dịch để tới ô tiếng Việt của dòng đó."}
                    {khung.thieu + gutterMissing > 0 && ` Còn ${khung.thieu + gutterMissing} chữ chưa định vị được nên không có ô.`}
                  </Typography.Paragraph>
                )}
                <SoatOverlay
                  mode={khung || view === "anh" || view === "dich" ? view : "anh"}
                  imageUrl={pageImageUrl(student, book, page)}
                  khung={khung}
                  banTam={pageBanTam}
                  draft={overlayDraft}
                  rows={pageRows}
                  marks={marks}
                  page={page}
                  onPick={(key) => document.getElementById(rowInputId(key))?.focus()}
                  onPickTranslation={(key) => document.getElementById(rowVietId(key))?.focus()}
                />
              </>
            )}
          </div>
          <Space orientation="vertical" style={{ flex: "1 1 460px", minWidth: 0 }} size="small">
            {machineBanTam !== undefined && (
              <div style={{ borderBottom: "1px solid rgba(128,128,128,0.3)", paddingBottom: 8 }}>
                <Typography.Text type="secondary">Bản tâm (cột in giữa ảnh, không tính vào số cặp)</Typography.Text>
                <Input.TextArea
                  id={rowInputId(BAN_TAM_KEY)}
                  aria-label="Bản tâm"
                  lang="zh-Hant"
                  autoSize
                  maxLength={500}
                  value={pageBanTam}
                  style={{ fontSize: 16, marginTop: 4 }}
                  onChange={(e) => {
                    setBanTam({ ...banTam, [page]: e.target.value });
                    setDirty(true);
                  }}
                />
              </div>
            )}
            {pageRows.length === 0 && <Typography.Text type="secondary">Trang này không có dòng nào của máy.</Typography.Text>}
            {pageRows.map((r, i) => {
              const isLast = rows[rows.length - 1].key === r.key;
              const crosses = i === pageRows.length - 1 && !isLast;
              return (
                <div key={r.key} style={{ borderBottom: "1px solid rgba(128,128,128,0.3)", paddingBottom: 8, opacity: r.bo ? 0.45 : 1 }}>
                  <Input.TextArea
                    id={rowInputId(r.key)}
                    aria-label={`Hán dòng ${i + 1}`}
                    lang="zh-Hant"
                    autoSize
                    value={r.han}
                    disabled={r.bo}
                    style={{ fontSize: 16, marginBottom: 4 }}
                    onChange={(e) => patch(r.key, { han: e.target.value })}
                    onSelect={(e) => {
                      carets.current[r.key] = { ...carets.current[r.key], han: e.currentTarget.selectionStart };
                    }}
                  />
                  <Input.TextArea
                    id={rowVietId(r.key)}
                    aria-label={`Việt dòng ${i + 1}`}
                    autoSize
                    value={r.viet}
                    disabled={r.bo}
                    style={{ marginBottom: 4 }}
                    onChange={(e) => patch(r.key, { viet: e.target.value })}
                    onSelect={(e) => {
                      carets.current[r.key] = { ...carets.current[r.key], viet: e.currentTarget.selectionStart };
                    }}
                  />
                  <Space size={4} wrap>
                    <Tag>{i + 1}</Tag>
                    {!isLast && (
                      <Button size="small" disabled={r.bo} onClick={() => edit(mergeWithNext(rows, r.key))}>
                        {crosses ? "Ghép với dòng đầu trang sau" : "Ghép với dòng dưới"}
                      </Button>
                    )}
                    <Button
                      size="small"
                      disabled={r.bo}
                      title="Phần sau con trỏ trong mỗi ô sẽ sang dòng mới"
                      onClick={() => {
                        const c = carets.current[r.key] ?? {};
                        edit(splitRow(rows, r.key, c.han ?? r.han.length, c.viet ?? r.viet.length));
                      }}
                    >
                      Tách tại con trỏ
                    </Button>
                    <Button size="small" onClick={() => patch(r.key, { bo: !r.bo })}>
                      {r.bo ? "Dùng lại" : "Bỏ dòng này"}
                    </Button>
                  </Space>
                </div>
              );
            })}
            <Button size="small" onClick={addRowToPage}>
              Thêm dòng
            </Button>
            <Checkbox
              checked={isConfirmed}
              onChange={(e) => {
                setConfirmed(e.target.checked ? [...confirmed, page] : confirmed.filter((p) => p !== page));
                setDirty(true);
              }}
            >
              Tôi đã soát xong trang này
            </Checkbox>
            <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
              Chỉ trang đã đánh dấu mới được tính khi nộp. Nháp tự lưu khi chuyển trang; đóng tab thì bấm Lưu nháp trước.
            </Typography.Paragraph>
          </Space>
        </div>
      )}
    </Space>
  );
};

export default SoatTab;
