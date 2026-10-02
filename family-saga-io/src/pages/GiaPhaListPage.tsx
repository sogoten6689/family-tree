import { useEffect, useState } from "react";
import { Alert, Button, Empty, Space, Table, Tag, Typography } from "antd";
import { BranchesOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { listGiaPha, type GiaPhaItem } from "@/lib/giaPhaApi";
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
const GiaPhaListPage = ({ scope }: GiaPhaListPageProps) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [items, setItems] = useState<GiaPhaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const detailBase = scope === "admin" ? "/admin/gia-pha" : scope === "user" ? "/user/gia-pha" : "/gia-pha";
  const uploadPath = scope === "public" ? "/" : "/user/document-reader";

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listGiaPha();
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được danh sách gia phả");
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope]);

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
    <div className="max-w-7xl mx-auto">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <Typography.Title level={4} className="!mb-1">
            {t("giaPhaList.title", { defaultValue: "Gia phả" })}
          </Typography.Title>
        </div>
        <div className="flex gap-2">
          <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>
            {t("familyTree.reload", { defaultValue: "Tải lại" })}
          </Button>
          {scope !== "public" && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate(uploadPath)}>
              {t("giaPhaList.uploadNew", { defaultValue: "Tải lên mới" })}
            </Button>
          )}
        </div>
      </div>

      {error && (
        <Alert
          type="warning"
          showIcon
          className="mb-6"
          message={error}
          closable
          onClose={() => setError(null)}
        />
      )}

      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 10, showSizeChanger: true, pageSizeOptions: ["10", "20", "50"] }}
        locale={{
          emptyText: (
            <Empty
              description={t("giaPhaList.empty", { defaultValue: "Chưa có bộ gia phả nào" })}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ),
        }}
        onRow={(record) => ({ onClick: () => goToDetail(record) })}
        rowClassName={() => "cursor-pointer"}
        columns={[
          {
            title: t("giaPhaList.columnId", { defaultValue: "Mã" }).toUpperCase(),
            dataIndex: "id",
            width: 220,
            render: (_: string, record: GiaPhaItem) => (
              <div className="flex items-center gap-2">
                <BranchesOutlined className="text-primary" />
                <div>
                  <div className="font-mono text-xs">{record.id}</div>
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
