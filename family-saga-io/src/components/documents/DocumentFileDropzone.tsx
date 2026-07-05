import { InboxOutlined } from "@ant-design/icons";
import { Upload, Typography } from "antd";
import type { UploadProps } from "antd";

type Props = {
  uploading?: boolean;
  onUpload: (files: File[]) => void | Promise<void>;
};

export function DocumentFileDropzone({ uploading = false, onUpload }: Props) {
  const uploadProps: UploadProps = {
    multiple: true,
    showUploadList: false,
    beforeUpload: () => false,
    disabled: uploading,
    onChange: (info) => {
      const selected = info.fileList
        .map((item) => item.originFileObj)
        .filter((file): file is File => file instanceof File);
      if (selected.length > 0) {
        void onUpload(selected);
      }
    },
  };

  return (
    <Upload.Dragger {...uploadProps} className="!bg-[#fafafa]">
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <Typography.Text strong className="block">
        Kéo thả file vào đây hoặc bấm để chọn
      </Typography.Text>
      <Typography.Paragraph type="secondary" className="!mb-0 mt-2 text-xs">
        File sẽ được upload ngay lên MinIO và thêm vào danh sách.
      </Typography.Paragraph>
    </Upload.Dragger>
  );
}
