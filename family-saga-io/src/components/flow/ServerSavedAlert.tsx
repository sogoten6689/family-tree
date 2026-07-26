import { CheckCircleOutlined } from "@ant-design/icons";
import { Alert } from "antd";
import { useTranslation } from "react-i18next";

type Props = {
  uploadedAt?: string;
  className?: string;
};

export function ServerSavedAlert({ uploadedAt, className }: Props) {
  const { t } = useTranslation();
  const timeLabel =
    uploadedAt != null
      ? new Date(uploadedAt).toLocaleString("vi-VN")
      : null;

  return (
    <Alert
      type="success"
      showIcon
      icon={<CheckCircleOutlined />}
      className={className}
      message={t("flow.serverSaved", { defaultValue: "Đã lưu trên server" })}
      description={
        timeLabel
          ? t("flow.serverSavedAt", {
              defaultValue: "Tài liệu được lưu lúc {{time}} — an toàn khi đổi trình duyệt.",
              time: timeLabel,
            })
          : t("flow.serverSavedHint", {
              defaultValue: "Dữ liệu được lưu trên server, không chỉ trên trình duyệt này.",
            })
      }
    />
  );
}
