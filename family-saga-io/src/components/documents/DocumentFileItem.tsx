import { DeleteOutlined, HolderOutlined, FileOutlined } from "@ant-design/icons";
import { Button, Tag, Typography } from "antd";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { formatFileSize } from "@/components/documents/constants";
import type { DocumentFile } from "@/types/document";

type Props = {
  file: DocumentFile;
  deleting?: boolean;
  onDelete: (fileId: number) => void;
};

export function DocumentFileItem({ file, deleting = false, onDelete }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: file.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.85 : 1,
  };

  const isImage = file.file_type.startsWith("image/");

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-3 rounded-xl border border-border bg-card px-3 py-3"
    >
      <button
        type="button"
        className="cursor-grab text-muted-foreground hover:text-foreground active:cursor-grabbing"
        aria-label="Kéo để sắp xếp"
        {...attributes}
        {...listeners}
      >
        <HolderOutlined />
      </button>

      {isImage && file.download_url ? (
        <img
          src={file.download_url}
          alt={file.file_name}
          className="h-12 w-12 rounded-lg object-cover border border-border"
        />
      ) : (
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-primary">
          <FileOutlined />
        </div>
      )}

      <div className="min-w-0 flex-1">
        <Typography.Text strong className="block truncate">
          {file.file_name}
        </Typography.Text>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>{formatFileSize(file.size)}</span>
          <Tag>{file.file_type}</Tag>
          <span>Vị trí #{file.position + 1}</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {file.download_url && (
          <Button size="small" href={file.download_url} target="_blank" rel="noreferrer">
            Tải
          </Button>
        )}
        <Button
          size="small"
          danger
          icon={<DeleteOutlined />}
          loading={deleting}
          onClick={() => onDelete(file.id)}
        >
          Xóa
        </Button>
      </div>
    </div>
  );
}
