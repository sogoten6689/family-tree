import { useEffect, useState } from "react";
import { Button, Card, Col, Row, Statistic, Typography } from "antd";
import { LinkOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { PageState } from "@/components/ui/PageState";
import { getAdminStats, type AdminStats } from "@/lib/userWorkspaceApi";

interface HannomProgressData {
  total_books: number;
  total_pages: number;
  pages_with_ocr: number;
  pages_with_transliteration: number;
  pages_with_translation: number;
  ocr_percent: number;
  transliteration_percent: number;
  translation_percent: number;
}

const AdminDashboardPage = () => {
  const { t } = useTranslation();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [hannomStats, setHannomStats] = useState<HannomProgressData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [adminData, hannomData] = await Promise.all([
        getAdminStats(),
        fetch("/api/public/hannom-progress").then((r) => r.json()),
      ]);
      setStats(adminData);
      setHannomStats(hannomData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được thống kê");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const statCards = [
    { title: t("adminDashboard.totalTrees", { defaultValue: "Tổng cây gia phả" }), value: stats?.total_trees ?? 0 },
    { title: t("adminDashboard.publicTrees", { defaultValue: "Gia phả công khai" }), value: stats?.public_trees ?? 0 },
    { title: t("adminDashboard.totalUsers", { defaultValue: "Người dùng" }), value: stats?.total_users ?? 0 },
    { title: t("adminDashboard.totalScans", { defaultValue: "Tài liệu đã scan" }), value: stats?.total_scans ?? 0 },
    { title: t("adminDashboard.historyTotal", { defaultValue: "Lịch sử truy vấn" }), value: stats?.history_total ?? 0 },
  ];

  return (
    <div className="space-y-6">
      <Typography.Title level={3}>
        {t("adminDashboard.title", { defaultValue: "Dashboard quản trị" })}
      </Typography.Title>

      <PageState loading={loading} error={error} onRetry={load}>
        <Row gutter={[16, 16]}>
          {statCards.map((item) => (
            <Col xs={24} sm={12} md={8} key={item.title}>
              <Card>
                <Statistic title={item.title} value={item.value} />
              </Card>
            </Col>
          ))}
        </Row>

        {hannomStats && (
          <>
            <Typography.Title level={4} className="!mt-8">
              {t("admin.hannom.title", { defaultValue: "Tiến độ Hán-Nôm" })}
            </Typography.Title>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title={t("admin.hannom.books", { defaultValue: "Cuốn" })}
                    value={hannomStats.total_books}
                    suffix="/ 28"
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title={t("admin.hannom.pages", { defaultValue: "Trang" })}
                    value={hannomStats.total_pages}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title={t("admin.hannom.ocr", { defaultValue: "OCR" })}
                    value={hannomStats.ocr_percent}
                    suffix="%"
                    precision={1}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <div className="flex justify-between items-center">
                    <Statistic
                      title={t("admin.hannom.translit", { defaultValue: "Phiên âm" })}
                      value={hannomStats.transliteration_percent}
                      suffix="%"
                      precision={1}
                    />
                  </div>
                  <Link to="/admin/gia-pha">
                    <Button type="link" size="small" icon={<LinkOutlined />}>
                      {t("admin.hannom.viewDetail", { defaultValue: "Xem chi tiết" })}
                    </Button>
                  </Link>
                </Card>
              </Col>
            </Row>
          </>
        )}
      </PageState>
    </div>
  );
};

export default AdminDashboardPage;
