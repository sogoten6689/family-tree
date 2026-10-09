import { useEffect, useRef, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Alert, Button, Empty, Input, Select, Space, Table, Tag, Typography } from "antd";
import { BranchesOutlined, ClearOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { listGiaPha, type GiaPhaItem } from "@/lib/giaPhaApi";
import {
  EMPTY_FILTERS,
  type CodeFilter,
  type GiaPhaFilters,
  type SourceFilter,
  type StatusFilter,
} from "@/lib/giaPhaSearch";
import { formatTreeDate } from "@/lib/familyTreeUtils";

export type GiaPhaListScope = "public" | "user" | "admin";

interface GiaPhaListPageProps {
  scope: GiaPhaListScope;
}

/**
 * Danh sách "Gia phả" hợp nhất dùng chung cho cả 3 vai trò — mỗi dòng là 1
 * "bộ gia phả" (UserScan chưa dựng cây hoặc FamilyTree đã dựng xong), gọi
 * chung 1 API `/api/gia-pha` (backend tự scope theo auth). `scope` chỉ quyết
 * định UI hiện gì (nút tải lên ẩn ở public), không gửi lên server.
 */
const PAGE_SIZE = 10;
const SEARCH_DEBOUNCE_MS = 300;
const STALE_MS = 15_000;

const GiaPhaListPage = ({ scope }: GiaPhaListPageProps) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [searchParams, setSearchParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);

  // Từ khoá giữ trên URL (?q=) để chia sẻ link; bộ lọc chỉ trong trang.
  const [filters, setFilters] = useState<GiaPhaFilters>({
    ...EMPTY_FILTERS,
    q: searchParams.get("q") ?? "",
  });
  // Gõ tới đâu cập nhật ô tìm tới đó, nhưng chỉ hỏi backend sau khi ngừng gõ 300 ms.
  const [debouncedQ, setDebouncedQ] = useState(filters.q);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQ(filters.q), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [filters.q]);

  const hasActiveFilter =
    filters.q.trim() !== "" || filters.status !== "all" || filters.code !== "all" || filters.source !== "all";

  const syncQueryToUrl = (q: string) => {
    const next = new URLSearchParams(searchParams);
    if (q.trim()) next.set("q", q);
    else next.delete("q");
    setSearchParams(next, { replace: true });
  };
  const updateFilters = (patch: Partial<GiaPhaFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
    if (patch.q !== undefined) syncQueryToUrl(patch.q);
  };
  const clearFilters = () => {
    setFilters(EMPTY_FILTERS);
    setDebouncedQ("");
    setPage(1);
    syncQueryToUrl("");
  };

  // Phân trang + tìm kiếm + lọc do backend làm; React Query giữ cache theo từng tổ hợp tham số
  // (quay lại trang cũ hiện ngay) và giữ dữ liệu cũ trong lúc tải trang mới.
  const forceRefresh = useRef(false);
  const { data, error, isFetching, refetch } = useQuery({
    queryKey: ["gia-pha", scope, { page, pageSize, q: debouncedQ.trim(), status: filters.status, code: filters.code, source: filters.source }],
    queryFn: () => {
      const refresh = forceRefresh.current;
      forceRefresh.current = false;
      return listGiaPha({
        page,
        pageSize,
        q: debouncedQ,
        status: filters.status,
        code: filters.code,
        source: filters.source,
        refresh,
      });
    },
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalAll = data?.total_all ?? total;
  const loading = isFetching;
  const errorMessage = error ? (error instanceof Error ? error.message : "Không tải được danh sách gia phả") : null;
  const reload = () => {
    forceRefresh.current = true;
    void refetch();
  };

  const detailBase = scope === "admin" ? "/admin/gia-pha" : scope === "user" ? "/user/gia-pha" : "/gia-pha";
  const uploadPath = scope === "public" ? "/" : "/user/document-reader";

  const goToDetail = (item: GiaPhaItem) => {
    if (item.status === "built" && item.tree_id) {
      navigate(`${detailBase}/${item.tree_id}`);
      return;
    }
    if (item.status === "pending" && item.scan_id != null) {
      navigate(`/user/documents/${item.scan_id}`);
    }
  };

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <Typography.Title level={4} className="!mb-1">
            {t("giaPhaList.title", { defaultValue: "Gia phả" })}
          </Typography.Title>
        </div>
        <div className="flex gap-2">
          <Button icon={<ReloadOutlined />} onClick={reload} loading={loading}>
            {t("familyTree.reload", { defaultValue: "Tải lại" })}
          </Button>
          {scope !== "public" && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate(uploadPath)}>
              {t("giaPhaList.uploadNew", { defaultValue: "Tải lên mới" })}
            </Button>
          )}
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input.Search
          allowClear
          className="max-w-md"
          value={filters.q}
          onChange={(event) => updateFilters({ q: event.target.value })}
          placeholder={t("giaPhaList.searchPlaceholder", { defaultValue: "Tìm theo mã, tên, họ…" })}
          aria-label={t("giaPhaList.search", { defaultValue: "Tìm kiếm gia phả" })}
        />
        <Select<StatusFilter>
          value={filters.status}
          onChange={(status) => updateFilters({ status })}
          aria-label={t("giaPhaList.filterStatus", { defaultValue: "Trạng thái" })}
          style={{ minWidth: 150 }}
          options={[
            { value: "all", label: t("giaPhaList.allStatus", { defaultValue: "Mọi trạng thái" }) },
            { value: "built", label: t("giaPhaList.statusBuilt", { defaultValue: "Đã dựng cây" }) },
            { value: "pending", label: t("giaPhaList.statusPending", { defaultValue: "Chờ dựng cây" }) },
          ]}
        />
        <Select<CodeFilter>
          value={filters.code}
          onChange={(code) => updateFilters({ code })}
          aria-label={t("giaPhaList.filterCode", { defaultValue: "Mã định danh" })}
          style={{ minWidth: 150 }}
          options={[
            { value: "all", label: t("giaPhaList.allCode", { defaultValue: "Có/chưa có mã" }) },
            { value: "has", label: t("giaPhaList.hasCode", { defaultValue: "Đã có mã" }) },
            { value: "none", label: t("giaPhaList.pendingCode", { defaultValue: "Chưa có mã chính thức" }) },
          ]}
        />
        <Select<SourceFilter>
          value={filters.source}
          onChange={(source) => updateFilters({ source })}
          aria-label={t("giaPhaList.filterSource", { defaultValue: "Nguồn mã" })}
          style={{ minWidth: 150 }}
          options={[
            { value: "all", label: t("giaPhaList.allSource", { defaultValue: "Mọi nguồn mã" }) },
            { value: "catalogue", label: t("maDinhDanh.sourceCatalogue", { defaultValue: "Đã chốt" }) },
            { value: "gemini", label: t("maDinhDanh.sourceGemini", { defaultValue: "Tự tạo (Gemini)" }) },
          ]}
        />
        <Typography.Text type="secondary">
          {t("giaPhaList.resultCount", {
            defaultValue: "{{shown}}/{{total}} bộ",
            shown: total,
            total: totalAll,
          })}
        </Typography.Text>
        {hasActiveFilter && (
          <Button icon={<ClearOutlined />} onClick={clearFilters}>
            {t("giaPhaList.clearFilters", { defaultValue: "Xoá bộ lọc" })}
          </Button>
        )}
      </div>

      {errorMessage && <Alert type="warning" showIcon className="mb-6" message={errorMessage} />}

      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        pagination={{
          current: page,
          total,
          pageSize,
          onChange: (nextPage, nextSize) => {
            setPage(nextSize !== pageSize ? 1 : nextPage);
            setPageSize(nextSize);
          },
          showSizeChanger: true,
          pageSizeOptions: ["10", "20", "50"],
        }}
        locale={{
          emptyText: (
            <Empty
              description={
                totalAll > 0
                  ? t("giaPhaList.noMatch", { defaultValue: "Không có bộ nào khớp tìm kiếm/bộ lọc" })
                  : t("giaPhaList.empty", { defaultValue: "Chưa có bộ gia phả nào" })
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ),
        }}
        onRow={(record) => ({ onClick: () => goToDetail(record) })}
        rowClassName={() => "cursor-pointer"}
        columns={[
          ...(scope === "admin"
            ? [
                {
                  title: t("giaPhaList.columnPages", { defaultValue: "Trang" }).toUpperCase(),
                  key: "page_count",
                  width: 80,
                  align: "right" as const,
                  render: () => "—",
                },
              ]
            : []),
          {
            title: t("giaPhaList.columnId", { defaultValue: "Mã" }).toUpperCase(),
            dataIndex: "id",
            width: 220,
            render: (_: string, record: GiaPhaItem) => (
              <div className="flex items-center gap-2">
                <BranchesOutlined className="text-primary" />
                <div>
                  <div className="font-mono text-xs">{record.id}</div>
                  {record.ma_dinh_danh_nguon === "gemini" && (
                    <Tag color="gold" className="!text-[10px] !leading-4 !mt-0.5">
                      {t("maDinhDanh.sourceGemini", { defaultValue: "Tự tạo (Gemini)" })}
                    </Tag>
                  )}
                  {record.ma_dinh_danh_pending && (
                    <div className="text-[11px] text-muted-foreground">
                      {t("giaPhaList.pendingCode", { defaultValue: "Chưa có mã chính thức" })}
                    </div>
                  )}
                </div>
              </div>
            ),
          },
          {
            title: t("giaPhaList.columnTitle", { defaultValue: "Tên" }).toUpperCase(),
            dataIndex: "title",
          },
          ...(scope === "admin"
            ? [
                {
                  title: t("giaPhaList.columnOcrStatus", { defaultValue: "OCR" }).toUpperCase(),
                  key: "ocr_status",
                  width: 120,
                  render: (_: unknown, record: GiaPhaItem) => {
                    const versionStatus = record.current_version?.status || "";
                    if (versionStatus.includes("ocr")) {
                      return <Tag color="blue">{t("giaPhaList.ocr", { defaultValue: "OCR" })}</Tag>;
                    }
                    return <Tag>{t("giaPhaList.pending", { defaultValue: "Chờ" })}</Tag>;
                  },
                },
              ]
            : []),
          {
            title: t("giaPhaList.columnStatus", { defaultValue: "Trạng thái" }).toUpperCase(),
            dataIndex: "status",
            width: 160,
            render: (status: GiaPhaItem["status"]) =>
              status === "built" ? (
                <Tag color="green">{t("giaPhaList.statusBuilt", { defaultValue: "Đã dựng cây" })}</Tag>
              ) : (
                <Tag color="gold">{t("giaPhaList.statusPending", { defaultValue: "Chờ dựng cây" })}</Tag>
              ),
          },
          {
            title: t("giaPhaList.columnUpdated", { defaultValue: "Cập nhật" }).toUpperCase(),
            dataIndex: "updated_at",
            width: 140,
            render: (value: string) => formatTreeDate(value),
          },
          {
            title: t("giaPhaList.columnActions", { defaultValue: "Hành động" }).toUpperCase(),
            key: "actions",
            width: 200,
            align: "right",
            render: (_: unknown, record: GiaPhaItem) => (
              <Space size={0}>
                <Button
                  type="link"
                  onClick={(event) => {
                    event.stopPropagation();
                    goToDetail(record);
                  }}
                >
                  {t("giaPhaList.detail", { defaultValue: "Chi tiết" })}
                </Button>
                {scope !== "public" && record.scan_id != null && (
                  <Button
                    type="link"
                    onClick={(event) => {
                      event.stopPropagation();
                      navigate(`/user/documents/${record.scan_id}?tab=versions`);
                    }}
                  >
                    {t("giaPhaList.versions", { defaultValue: "Phiên bản" })}
                  </Button>
                )}
              </Space>
            ),
          },
        ]}
      />
    </div>
  );
};

export default GiaPhaListPage;
