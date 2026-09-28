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
      ? new Date(uploadedAt).toLocaleString("vi-VN", {
          hour: "2-digit",
          minute: "2-digit",
          day: "numeric",
          month: "numeric",
          year: "numeric",
        })
      : null;

  return (
    <Alert
      type="success"
      showIcon
      icon={<CheckCircleOutlined />}
      className={className}
      message={
        timeLabel
          ? t("flow.serverSavedAt", { time: timeLabel })
          : t("flow.serverSaved")
      }
    />
  );
}
