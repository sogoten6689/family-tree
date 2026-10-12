import { useEffect, useState } from "react";
import { Button, Tooltip, Typography } from "antd";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

import { getDocumentNeighbors, type DocumentNeighbor, type DocumentNeighbors } from "@/lib/userWorkspaceApi";

type DocumentNeighborNavProps = {
  scanId: number;
  /** Đi tới tài liệu khác (trang chi tiết giữ nguyên tab đang xem). */
  onGo: (id: number) => void;
};

/** Nút "Trước / Sau" để chuyển nhanh giữa các tài liệu (theo ID tăng dần), kèm vị trí "k/n". */
export function DocumentNeighborNav({ scanId, onGo }: DocumentNeighborNavProps) {
  const { t } = useTranslation();
  const [neighbors, setNeighbors] = useState<DocumentNeighbors | null>(null);

  useEffect(() => {
    let cancelled = false;
    setNeighbors(null);
    getDocumentNeighbors(scanId)
      .then((data) => !cancelled && setNeighbors(data))
      .catch(() => !cancelled && setNeighbors(null)); // lỗi/không có quyền: ẩn nút, không chặn trang
    return () => {
      cancelled = true;
    };
  }, [scanId]);

  if (!neighbors || neighbors.total < 2) return null;

  const label = (target: DocumentNeighbor | null) => (target ? `#${target.id} · ${target.title}` : "");

  return (
    <div className="flex items-center gap-1" data-testid="doc-neighbors">
      <Tooltip title={label(neighbors.prev)}>
        <Button
          size="small"
          icon={<LeftOutlined />}
          disabled={!neighbors.prev}
          onClick={() => neighbors.prev && onGo(neighbors.prev.id)}
        >
          {t("documentNav.prev", { defaultValue: "Trước" })}
        </Button>
      </Tooltip>
      <Typography.Text type="secondary" className="px-1 text-xs">
        {neighbors.position}/{neighbors.total}
      </Typography.Text>
      <Tooltip title={label(neighbors.next)}>
        <Button size="small" disabled={!neighbors.next} onClick={() => neighbors.next && onGo(neighbors.next.id)}>
          {t("documentNav.next", { defaultValue: "Sau" })} <RightOutlined />
        </Button>
      </Tooltip>
    </div>
  );
}
