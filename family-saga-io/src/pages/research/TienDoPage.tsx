import { useQuery } from "@tanstack/react-query";
import { Alert, Badge, Card, Col, Progress, Row, Statistic, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link } from "react-router-dom";

import { getOverview, getTienDo, type BookSummary, type StudentSummary, type TienDoCuon, type TrangThai } from "@/lib/doiChieuApi";

/** Trang tự gọi lại máy chủ sau ngần này mili giây. */
export const REFRESH_MS = 5000;
/** Số liệu dóng hàng đổi chậm hơn khung (soát tay, nộp bài) nên làm mới thưa hơn. */
export const ALIGN_REFRESH_MS = 15000;
/** Cuốn có trang khung mới trong khoảng này được đánh dấu "đang chạy". */
const LIVE_MS = 3 * 60 * 1000;

const num = (n: number) => n.toLocaleString("vi-VN");
const pct = (part: number, whole: number) => (whole > 0 ? Math.round((part / whole) * 1000) / 10 : 0);

export const tuLuc = (iso: string | null, now: number): string => {
  if (!iso) return "—";
  const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
  if (s < 60) return "vừa xong";
  if (s < 3600) return `${Math.floor(s / 60)} phút trước`;
  if (s < 86400) return `${Math.floor(s / 3600)} giờ trước`;
  return new Date(iso).toLocaleDateString("vi-VN");
};

const columns = (now: number): ColumnsType<TienDoCuon> => [
  {
    title: "Cuốn",
    key: "book",
    render: (_, r) => (
      <Link to={xemCuon(r.student, r.book)}>
        {r.ten ? `${r.ten} (${r.book})` : r.book}
      </Link>
    ),
  },
  {
    title: "Trang có khung",
    key: "trang",
    render: (_, r) => (
      <>
        {num(r.trang_khung)} / {num(r.trang_anh)}
        <Progress percent={pct(r.trang_khung, r.trang_anh)} size="small" showInfo={false} />
      </>
    ),
  },
  { title: "Chữ có khung", dataIndex: "chu", align: "right", render: num },
  { title: "Chữ chưa có khung", dataIndex: "thieu", align: "right", render: num },
  {
    title: "Đủ khung",
    key: "du",
    width: 160,
    render: (_, r) => <Progress percent={pct(r.chu, r.chu + r.thieu)} size="small" />,
  },
  {
    title: "Cập nhật",
    key: "cap_nhat",
    render: (_, r) =>
      r.cap_nhat && now - Date.parse(r.cap_nhat) < LIVE_MS ? (
        <Tag color="green">đang chạy · {tuLuc(r.cap_nhat, now)}</Tag>
      ) : (
        tuLuc(r.cap_nhat, now)
      ),
  },
];

const xemCuon = (student: string, book: string) =>
  `/nghien-cuu/doi-chieu?sv=${encodeURIComponent(student)}&cuon=${encodeURIComponent(book)}`;

type CuonDongHang = BookSummary & { student: string };

const dongHangColumns: ColumnsType<CuonDongHang> = [
  {
    title: "Cuốn",
    key: "book",
    render: (_, b) => <Link to={xemCuon(b.student, b.id)}>{b.ten ? `${b.ten} (${b.id})` : b.id}</Link>,
  },
  { title: "Cặp đã soát", key: "da_soat", align: "right", render: (_, b) => num(b.bo?.da_soat ?? 0) },
  { title: "Cặp máy, chưa soát", key: "may", align: "right", render: (_, b) => num(b.bo?.may ?? 0) },
  {
    title: "Trang đã soát",
    key: "trang",
    width: 170,
    render: (_, b) => (
      <>
        {num(b.bo?.trang_da_soat ?? 0)} / {num(b.bo?.trang ?? 0)}
        <Progress percent={pct(b.bo?.trang_da_soat ?? 0, b.bo?.trang ?? 0)} size="small" />
      </>
    ),
  },
  {
    title: "Chấm mẫu",
    key: "cham",
    render: (_, b) =>
      b.cham.checked === 0 ? (
        <Typography.Text type="secondary">chưa chấm</Typography.Text>
      ) : (
        <>
          {num(b.cham.checked)}/{num(b.cham.sample)} cặp · lỗi {b.cham.rate === null ? "—" : `${Math.round(b.cham.rate * 1000) / 10}%`}{" "}
          {b.cham.dat && <Tag color="green">đạt</Tag>}
        </>
      ),
  },
  { title: "", key: "xem", render: (_, b) => <Link to={xemCuon(b.student, b.id)}>Xem kết quả →</Link> },
];

const svColumns = (target: number): ColumnsType<StudentSummary> => [
  { title: "Sinh viên", dataIndex: "ten" },
  { title: "Cuốn đã nộp", key: "nop", render: (_, s) => `${s.submitted} / ${s.books.length}` },
  { title: "Cặp hợp lệ", dataIndex: "valid", align: "right", render: num },
  {
    title: `Cặp đạt chất lượng / chỉ tiêu ${num(target)}`,
    key: "dat",
    width: 260,
    render: (_, s) => (
      <>
        {num(s.quality_pairs)}
        <Progress percent={pct(s.quality_pairs, target)} size="small" />
      </>
    ),
  },
];

/** Dóng hàng Hán–Việt: bộ song song của nhóm chưa giao (cặp đã soát / máy chưa soát) và bài nộp của từng sinh viên. */
const DongHang = () => {
  const { data, error } = useQuery({ queryKey: ["doi-chieu"], queryFn: getOverview, refetchInterval: ALIGN_REFRESH_MS });
  if (error && !data) return <Alert type="error" showIcon title="Không tải được số liệu dóng hàng" description={String(error)} />;
  const students = data?.students ?? [];
  // Bộ song song sạch chỉ có ở nhóm chưa giao; nhóm đó xem theo từng cuốn, sinh viên xem theo người.
  const books: CuonDongHang[] = students.flatMap((s) => s.books.filter((b) => b.bo).map((b) => ({ ...b, student: s.id })));
  const svs = students.filter((s) => !s.books.some((b) => b.bo));
  const total = (k: "da_soat" | "may" | "trang_da_soat" | "trang") => books.reduce((a, b) => a + (b.bo?.[k] ?? 0), 0);
  return (
    <Card title="Dóng hàng Hán – Việt" loading={!data} style={{ marginTop: 16 }}>
      <Typography.Paragraph type="secondary">
        Mỗi câu chữ Hán được ghép với câu dịch tiếng Việt thành một "cặp". Cặp đã soát là cặp người đã đối chiếu ảnh và xác nhận; cặp
        máy là bản OCR + dịch máy, chưa ai soát. Tự làm mới mỗi {ALIGN_REFRESH_MS / 1000} giây.
      </Typography.Paragraph>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} md={6}>
          <Statistic title="Cặp đã soát" value={num(total("da_soat"))} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="Cặp máy, chưa soát" value={num(total("may"))} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="Trang đã soát" value={`${num(total("trang_da_soat"))} / ${num(total("trang"))}`} />
        </Col>
        <Col xs={12} md={6}>
          <Statistic title="Tổng cặp" value={num(total("da_soat") + total("may"))} />
        </Col>
      </Row>
      <Table rowKey={(b) => `${b.student}/${b.id}`} size="small" pagination={false} scroll={{ x: true }} columns={dongHangColumns} dataSource={books} />
      {svs.length > 0 && (
        <>
          <Typography.Title level={5} style={{ marginTop: 24 }}>
            Bài nộp của sinh viên
          </Typography.Title>
          <Table rowKey="id" size="small" pagination={false} scroll={{ x: true }} columns={svColumns(data?.target ?? 2000)} dataSource={svs} />
        </>
      )}
    </Card>
  );
};

const Muc = ({ title, items, color }: { title: string; items: string[]; color: string }) => (
  <Card size="small" title={<span style={{ color }}>{title}</span>} style={{ height: "100%" }}>
    {items.length ? (
      <ul style={{ margin: 0, paddingLeft: 18 }}>
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    ) : (
      <Typography.Text type="secondary">Không có</Typography.Text>
    )}
  </Card>
);

const TrangThaiCard = ({ s }: { s: TrangThai }) => (
  <>
    <Row gutter={[12, 12]}>
      <Col xs={24} md={8}>
        <Muc title="✅ Đã xong" items={s.xong} color="#389e0d" />
      </Col>
      <Col xs={24} md={8}>
        <Muc title="🔄 Đang làm" items={s.dang_lam} color="#1677ff" />
      </Col>
      <Col xs={24} md={8}>
        <Muc title="⏳ Chờ anh Lâm quyết" items={s.cho_quyet} color="#d46b08" />
      </Col>
    </Row>
    {s.cap_nhat && (
      <Typography.Text type="secondary" style={{ display: "block", marginTop: 4 }}>
        Ghi chú cập nhật: {s.cap_nhat}
      </Typography.Text>
    )}
  </>
);

/** Tiến độ khung chữ của các cuốn, tự làm mới vài giây một lần: trang khung nào vừa lên máy chủ là thấy ngay. */
const TienDoPage = () => {
  const { data, error, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ["doi-chieu", "tien-do"],
    queryFn: getTienDo,
    refetchInterval: REFRESH_MS,
  });
  const now = dataUpdatedAt || Date.now();
  const books = data?.cuon ?? [];
  const sum = (k: "trang_anh" | "trang_khung" | "chu" | "thieu") => books.reduce((a, b) => a + b[k], 0);

  return (
    <div style={{ maxWidth: 1280, margin: "0 auto", width: "100%" }}>
      <Typography.Title level={2}>Tiến độ khung chữ và dóng hàng</Typography.Title>
      <Typography.Paragraph type="secondary">
        <Badge status={error ? "error" : "processing"} text={error ? "Mất kết nối, đang thử lại" : "Trực tiếp"} /> · tự làm mới mỗi{" "}
        {REFRESH_MS / 1000} giây · lần cuối {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString("vi-VN") : "—"}. "Khung" là ô bao
        quanh từng chữ Hán trên ảnh; bấm tên cuốn để xem ảnh có khung. <Link to="/nghien-cuu/quan-ly">← Thông tin nghiên cứu</Link>
      </Typography.Paragraph>

      {error && !data && <Alert type="error" showIcon title="Không tải được tiến độ" description={String(error)} />}
      {data?.trang_thai && <TrangThaiCard s={data.trang_thai} />}

      <Card title="Khung chữ trên ảnh" loading={isLoading && !data} style={{ marginTop: 16 }}>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} md={6}>
            <Statistic title="Số cuốn có khung" value={books.length} />
          </Col>
          <Col xs={12} md={6}>
            <Statistic title="Trang có khung" value={`${num(sum("trang_khung"))} / ${num(sum("trang_anh"))}`} />
          </Col>
          <Col xs={12} md={6}>
            <Statistic title="Chữ có khung" value={num(sum("chu"))} />
          </Col>
          <Col xs={12} md={6}>
            <Statistic title="Đủ khung" value={pct(sum("chu"), sum("chu") + sum("thieu"))} suffix="%" />
          </Col>
        </Row>
        <Table rowKey={(r) => `${r.student}/${r.book}`} size="small" pagination={false} scroll={{ x: true }} columns={columns(now)} dataSource={books} />
      </Card>
      <DongHang />
    </div>
  );
};

export default TienDoPage;
