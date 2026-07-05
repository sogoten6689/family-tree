import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { Empty, Spin, Typography } from "antd";

import { DocumentFileItem } from "@/components/documents/DocumentFileItem";
import { sortDocumentFiles } from "@/components/documents/constants";
import type { DocumentFile } from "@/types/document";

type Props = {
  files: DocumentFile[];
  loading?: boolean;
  reordering?: boolean;
  deletingFileId?: number | null;
  onReorder: (files: DocumentFile[]) => void | Promise<void>;
  onDelete: (fileId: number) => void | Promise<void>;
};

export function DocumentFileList({
  files,
  loading = false,
  reordering = false,
  deletingFileId = null,
  onReorder,
  onDelete,
}: Props) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const sortedFiles = sortDocumentFiles(files);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = sortedFiles.findIndex((item) => item.id === active.id);
    const newIndex = sortedFiles.findIndex((item) => item.id === over.id);
    if (oldIndex < 0 || newIndex < 0) return;

    const reordered = arrayMove(sortedFiles, oldIndex, newIndex).map((item, index) => ({
      ...item,
      position: index,
    }));
    void onReorder(reordered);
  };

  if (loading) {
    return (
      <div className="py-10 flex justify-center">
        <Spin />
      </div>
    );
  }

  if (sortedFiles.length === 0) {
    return <Empty description="Chưa có file nào trong tài liệu này." />;
  }

  return (
    <div className="space-y-3">
      <Typography.Text type="secondary" className="text-xs">
        Kéo thả để thay đổi thứ tự hiển thị. Thay đổi sẽ được lưu tự động.
      </Typography.Text>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={sortedFiles.map((item) => item.id)} strategy={verticalListSortingStrategy}>
          <div className={`space-y-3 ${reordering ? "opacity-70 pointer-events-none" : ""}`}>
            {sortedFiles.map((file) => (
              <DocumentFileItem
                key={file.id}
                file={file}
                deleting={deletingFileId === file.id}
                onDelete={onDelete}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}
