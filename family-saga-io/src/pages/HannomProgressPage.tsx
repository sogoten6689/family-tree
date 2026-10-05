import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Table, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";

import { PageState } from "@/components/ui/PageState";

interface HannomBook {
  doc_id: string;
  title_vn: string;
  page_count: number;
  has_ocr: boolean;
  has_transliteration: boolean;
  has_translation: boolean;
  ma_dinh_danh: string | null;
  flags: string[];
}

interface HannomProgressData {
  total_books: number;
  total_pages: number;
  pages_with_ocr: number;
  pages_with_transliteration: number;
  pages_with_translation: number;
  ocr_percent: number;
  transliteration_percent: number;
  translation_percent: number;
  books: HannomBook[];
}

const HannomProgressPage = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<HannomProgressData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/public/hannom-progress");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const json = (await response.json()) as HannomProgressData;
      setData(json);
    } catch (err) {
      setData(null);
      setError(err instanceof Error ? err.message : "Không tải được dữ liệu");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const getStatusTags = (book: HannomBook) => {
    const tags = [];
    if (book.has_ocr) tags.push(<Tag key="ocr" color="blue">OCR</Tag>);
    if (book.has_transliteration) tags.push(<Tag key="trans" color="green">Phiên âm</Tag>);
    if (book.has_translation) tags.push(<Tag key="translt" color="orange">Dịch</Tag>);
    if (tags.length === 0) tags.push(<Tag key="draft" color="default">Draft</Tag>);
    return tags;
  };

  const columns = [
    {
      title: "Mã",
      dataIndex: "doc_id",
      key: "doc_id",
      width: 120,
      render: (text: string) => <code className="text-xs">{text}</code>,
    },
    {
      title: "Tên",
      dataIndex: "title_vn",
      key: "title_vn",
      ellipsis: true,
    },
    {
      title: "Trang",
      dataIndex: "page_count",
      key: "page_count",
      width: 80,
      align: "right" as const,
    },
    {
      title: "Mã định danh",
      dataIndex: "ma_dinh_danh",
      key: "ma_dinh_danh",
      width: 140,
      render: (text: string | null) =>
        text ? <code className="text-xs">{text}</code> : <span className="text-gray-400">—</span>,
    },
    {
      title: "Trạng thái",
      key: "status",
      width: 180,
      render: (_: unknown, record: HannomBook) => (
        <div className="flex flex-wrap gap-1">{getStatusTags(record)}</div>
      ),
    },
  ];

  return (
    <div className="max-w-7xl mx-auto py-8 md:py-10 px-4 sm:px-6">
      <Typography.Title level={2} className="!text-2xl sm:!text-3xl">
        {t("hannomProgress.title", { defaultValue: "Thống kê Hán-Nôm" })}
      </Typography.Title>
      <Typography.Paragraph type="secondary" className="!mb-8">
        {t("hannomProgress.subtitle", {
          defaultValue: "Tiến độ xử lý 28 cuốn gia phả Hán-Nôm",
        })}
      </Typography.Paragraph>

      <PageState loading={loading} error={error} onRetry={load} empty={false}>
        {data && (
          <>
            <Row gutter={[16, 16]} className="mb-8">
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title="Tổng cuốn"
                    value={data.total_books}
                    suffix="/ 28"
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title="Tổng trang"
                    value={data.total_pages}
                    valueStyle={{ color: "#595959" }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title="OCR"
                    value={data.ocr_percent}
                    suffix="%"
                    precision={1}
                    valueStyle={{ color: "#1890ff" }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title="Phiên âm"
                    value={data.transliteration_percent}
                    suffix="%"
                    precision={1}
                    valueStyle={{ color: "#52c41a" }}
                  />
                </Card>
              </Col>
            </Row>

            <Row gutter={[16, 16]}>
              <Col xs={24}>
                <Card>
                  <Typography.Title level={4} className="!mb-4">
                    Danh mục 28 cuốn
                  </Typography.Title>
                  <Table
                    columns={columns}
                    dataSource={data.books.map((b, i) => ({ ...b, key: i }))}
                    size="small"
                    pagination={{ pageSize: 20, showTotal: (t) => `${t} cuốn` }}
                  />
                </Card>
              </Col>
            </Row>
          </>
        )}
      </PageState>
    </div>
  );
};

export default HannomProgressPage;
