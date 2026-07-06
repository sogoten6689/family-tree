import { CopyOutlined } from "@ant-design/icons";
import { Button, Space, Typography, message } from "antd";

interface CodeBlockProps {
  code: string;
  language?: string;
}

const CodeBlock = ({ code, language = "text" }: CodeBlockProps) => {
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      message.success("Đã copy vào clipboard");
    } catch {
      message.error("Không thể copy");
    }
  };

  return (
    <div className="rounded-lg border border-border bg-muted/40 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-card">
        <Typography.Text type="secondary" className="text-xs uppercase">
          {language}
        </Typography.Text>
        <Button size="small" icon={<CopyOutlined />} onClick={handleCopy}>
          Copy nhanh
        </Button>
      </div>
      <pre className="m-0 p-4 overflow-x-auto text-xs leading-relaxed">
        <Typography.Text code className="!bg-transparent !text-inherit whitespace-pre-wrap break-all">
          {code}
        </Typography.Text>
      </pre>
    </div>
  );
};

export default CodeBlock;
