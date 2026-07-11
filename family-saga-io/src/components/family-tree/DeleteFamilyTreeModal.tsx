import { ExclamationCircleOutlined } from "@ant-design/icons";
import { Input, Modal, Typography } from "antd";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

type Props = {
  open: boolean;
  treeId: string;
  treeName?: string | null;
  loading?: boolean;
  onCancel: () => void;
  onConfirm: () => void | Promise<void>;
};

export function DeleteFamilyTreeModal({
  open,
  treeId,
  treeName,
  loading = false,
  onCancel,
  onConfirm,
}: Props) {
  const { t } = useTranslation();
  const [confirmId, setConfirmId] = useState("");

  useEffect(() => {
    if (!open) {
      setConfirmId("");
    }
  }, [open]);

  const idMatches = confirmId.trim() === treeId;

  return (
    <Modal
      open={open}
      title={
        <span className="text-[var(--ant-color-error)]">
          <ExclamationCircleOutlined className="mr-2" />
          {t("familyTree.deleteTreeTitle", { defaultValue: "Xóa gia phả" })}
        </span>
      }
      okText={t("familyTree.delete", { defaultValue: "Xóa vĩnh viễn" })}
      okButtonProps={{ danger: true, disabled: !idMatches, loading }}
      cancelText={t("familyTree.cancel", { defaultValue: "Hủy" })}
      onCancel={onCancel}
      onOk={() => void onConfirm()}
      destroyOnClose
    >
      <Typography.Paragraph>
        {t("familyTree.deleteTreeConfirmTyped", {
          defaultValue:
            "Hành động này xóa cây gia phả, pipeline, tài liệu MinIO và metadata crawl. Không thể hoàn tác.",
        })}
      </Typography.Paragraph>
      {treeName && (
        <Typography.Paragraph className="!mb-2">
          <strong>{treeName}</strong>
        </Typography.Paragraph>
      )}
      <Typography.Paragraph type="secondary" className="!mb-2">
        {t("familyTree.deleteTreeTypeId", {
          defaultValue: "Nhập mã gia phả để xác nhận:",
        })}{" "}
        <Typography.Text code copyable>
          {treeId}
        </Typography.Text>
      </Typography.Paragraph>
      <Input
        value={confirmId}
        onChange={(event) => setConfirmId(event.target.value)}
        placeholder={treeId}
        autoComplete="off"
        status={confirmId && !idMatches ? "error" : undefined}
        onPressEnter={() => {
          if (idMatches && !loading) {
            void onConfirm();
          }
        }}
      />
    </Modal>
  );
}
