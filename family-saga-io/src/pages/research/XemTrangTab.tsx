import { useQuery } from "@tanstack/react-query";
import { Alert, Col, Pagination, Row, Segmented, Space, Table, Tag, Tooltip, Typography } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";

import { getXemTrang, pageImageUrl, type AmChu, type BookDetail, type CapTrang } from "@/lib/doiChieuApi";

import { draftChars } from "./lopPhu";
import { ACTIVE_FILL } from "./oChu";
import SoatOverlay from "./SoatOverlay";

type Mode = "anh" | "song";
type Cap = CapTrang & { key: number };

const HAN_FONT = '"Noto Serif TC", "Songti TC", "SimSun", serif';

/** Âm Hán Việt của cả vế, giữ dấu câu; chữ nhiều âm gạch chấm, rê chuột thấy các âm khác; chữ chưa có âm hiện "?". */
export const AmHanViet = ({ am }: { am: AmChu[] }) => {
  const parts: React.ReactNode[] = [];
  am.forEach((x, i) => {
    const isHan = x.a !== undefined || /[㐀-䶿一-鿿豈-﫿\u{20000}-\u{3ffff}]/u.test(x.c);
    if (!isHan) {
      if (x.c.trim()) parts.push(<span key={i}>{x.c}</span>);
      return;
    }
    if (parts.length) parts.push(" ");
    if (!x.a) {
      parts.push(
        <Tooltip key={i} title={`Chưa có âm cho chữ ${x.c}`}>
          <span data-testid="am-thieu" style={{ color: "#8c8c8c" }}>
            ?
          </span>
        </Tooltip>,
      );
    } else if (x.k?.length) {
      parts.push(
        <Tooltip key={i} title={`${x.c}: còn đọc ${x.k.join(", ")}`}>
          <span data-testid="am-nhieu" style={{ textDecoration: "underline dotted #8c8c8c", textUnderlineOffset: 3 }}>
            {x.a}
          </span>
        </Tooltip>,
      );
    } else {
      parts.push(<span key={i}>{x.a}</span>);
    }
  });
  return <>{parts}</>;
};

/** Một trang của bộ song song sạch: ảnh gốc có khung từng chữ, đặt cạnh bảng Hán | Âm Hán Việt | Nghĩa. Chỉ đọc. */
const XemTrangTab = ({ detail }: { detail: BookDetail }) => {
  const [index, setIndex] = useState(0);
  const [mode, setMode] = useState<Mode>("anh");
  const [active, setActive] = useState<number | null>(null);
  const table = useRef<HTMLDivElement>(null);
  const page = detail.pages[index];
  const { data, error, isLoading } = useQuery({
    queryKey: ["doi-chieu", detail.student, detail.book, "trang", page],
    queryFn: () => getXemTrang(detail.student, detail.book, page),
    enabled: Boolean(page),
    // Khung được đẩy lên theo từng trang (tools/dong_bo_khung.py): trang đang mở tự hiện khung mới, không cần tải lại.
    refetchInterval: 15000,
  });

  const rows: Cap[] = useMemo(() => (data?.cap ?? []).map((r, i) => ({ ...r, key: i })), [data]);
  const draft = useMemo(() => draftChars(rows.map((r) => ({ key: r.key, trang: page, han: r.han, viet: r.viet, bo: false }))), [rows, page]);
  const overlayRows = useMemo(() => rows.map((r) => ({ key: r.key, viet: r.viet, bo: false })), [rows]);

  useEffect(() => setActive(null), [page]);
  useEffect(() => {
    if (active === null) return;
    table.current?.querySelector(`[data-row-key="${active}"]`)?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [active]);

  if (!page) return <Typography.Text type="secondary">Chưa có ảnh trang trên máy chủ.</Typography.Text>;

  const pick = (key: number) => setActive((cur) => (cur === key ? null : key));
  const khung = data?.khung ?? null;
  const placedShare = khung ? khung.chu.length / Math.max(1, khung.chu.length + khung.thieu) : 0;

  const columns = [
    { title: "#", key: "n", width: 40, render: (_: unknown, r: Cap) => r.key + 1 },
    {
      title: "Hán",
      key: "han",
      width: "26%",
      render: (_: unknown, r: Cap) => (
        <Space orientation="vertical" size={2}>
          <span style={{ fontFamily: HAN_FONT, fontSize: 18, lineHeight: 1.5 }}>{r.han}</span>
          {r.sua_chu && (
            <Tooltip title="Đã sửa chữ theo vote OCR, có đối chiếu ảnh">
              <Tag color="orange">sửa chữ</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    { title: "Âm Hán Việt", key: "am", width: "30%", render: (_: unknown, r: Cap) => <AmHanViet am={r.am} /> },
    {
      title: "Nghĩa",
      key: "viet",
      render: (_: unknown, r: Cap) => (
        <Space orientation="vertical" size={2}>
          <span>{r.viet}</span>
          <Space size={4}>
            {r.dich_lai && <Tag color="blue">dịch lại</Tag>}
            {r.nguon === "da_soat" && <Tag color="green">đã soát</Tag>}
          </Space>
        </Space>
      ),
    },
  ];

  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <Space wrap>
        <Pagination simple current={index + 1} total={detail.pages.length} pageSize={1} onChange={(n) => setIndex(n - 1)} showSizeChanger={false} />
        <Typography.Text type="secondary">Trang {page}</Typography.Text>
        <Segmented<Mode>
          size="small"
          aria-label="Cách xem ảnh"
          value={mode}
          onChange={setMode}
          options={[
            { value: "anh", label: "Ảnh có khung chữ" },
            { value: "song", label: "Ảnh + chữ phục dựng" },
          ]}
        />
        {khung && (
          <Typography.Text type="secondary" data-testid="do-phu-khung">
            Định vị {khung.chu.length}/{khung.chu.length + khung.thieu} chữ ({Math.round(placedShare * 100)}%)
          </Typography.Text>
        )}
      </Space>
      {error && <Alert type="error" showIcon title="Không tải được trang" description={String(error)} />}
      {data && !khung && <Alert type="info" showIcon title="Trang này chưa có khung chữ; chỉ hiện ảnh gốc." />}
      <Row gutter={16}>
        <Col xs={24} lg={mode === "song" ? 24 : 11}>
          <div style={{ position: "sticky", top: 8 }}>
            <SoatOverlay
              mode={mode}
              imageUrl={pageImageUrl(detail.student, detail.book, page)}
              khung={khung}
              banTam=""
              draft={draft}
              rows={overlayRows}
              marks
              page={page}
              activeKey={active}
              onPick={pick}
              onPickTranslation={pick}
            />
          </div>
        </Col>
        <Col xs={24} lg={mode === "song" ? 24 : 13} ref={table}>
          <Table<Cap>
            rowKey="key"
            size="small"
            loading={isLoading}
            pagination={false}
            columns={columns}
            dataSource={rows}
            locale={{ emptyText: "Trang này không có cặp nào trong bộ song song sạch." }}
            onRow={(r) => ({
              onClick: () => pick(r.key),
              style: { cursor: "pointer", background: r.key === active ? ACTIVE_FILL : undefined },
            })}
          />
        </Col>
      </Row>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Khung chữ do PaddleOCR định vị trên máy của lab: nét liền là tách được từ nét mực, nét đứt là ước lượng. Số xanh trên ảnh là số dòng
        trong bảng; bấm khung hoặc dòng để làm sáng phần tương ứng. Âm Hán Việt tra từng chữ theo Hán Việt tự điển (Thiều Chửu). Chữ nhiều âm:
        nếu vế Việt của cặp có một âm của chữ thì lấy âm đó (辰 trong "Mậu Thìn" đọc "thìn"), không thì lấy âm thường dùng; chữ gạch chấm
        là còn âm khác, rê chuột để xem. Đây là tra từ điển, chưa phải phiên âm theo ngữ cảnh đầy đủ.
      </Typography.Paragraph>
    </Space>
  );
};

export default XemTrangTab;
