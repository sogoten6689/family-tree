import { Card, Space, Tabs, Typography } from "antd";

import CodeBlock from "@/components/developer/CodeBlock";
import { getBackendBaseUrl } from "@/lib/apiClient";

const baseUrl = getBackendBaseUrl() || "https://giapha.kimtudien.com.vn";

const OCR_CURL = `curl -X POST "${baseUrl}/api/documents/1/ocr-transliterate" \\
  -H "Authorization: Bearer <JWT_ADMIN>" \\
  -F "image=@/path/to/giapha-hannom.jpg"`;

const OCR_RESPONSE = `{
  "source_document_id": 1,
  "result_document_id": 12,
  "ocr_text": "… chữ Hán Nôm …",
  "ocr_lines": ["dòng 1", "dòng 2"],
  "transcription_lines": ["dòng quốc ngữ 1"],
  "transcription_text": "dòng quốc ngữ 1",
  "saved_file": {
    "id": 45,
    "file_name": "giapha_transcription.txt",
    "file_type": "text/plain; charset=utf-8"
  },
  "result_document": { "id": 12, "type": "ket_qua_van_ban" }
}`;

const UPLOAD_CURL = `curl -X POST "${baseUrl}/api/documents/1/upload-files" \\
  -H "Authorization: Bearer <JWT_ADMIN>" \\
  -F "files=@scan-page-01.jpg" \\
  -F "files=@scan-page-02.jpg"`;

const HEALTH_CURL = `curl -s "${baseUrl}/health" | jq`;

const CRAWL_CURL = `curl -X POST "${baseUrl}/api/vietnamgiapha/crawl-sync" \\
  -H "Authorization: Bearer <JWT_ADMIN>" \\
  -H "Content-Type: application/json" \\
  -d '{"start_id":100,"end_id":200,"delay_seconds":0.2,"sync_db":true}'`;

const CRAWL_RESPONSE = `{
  "start_id": 100,
  "end_id": 200,
  "output_dir": "/app/data/vietnamgiapha",
  "crawl_success": 42,
  "crawl_errors": 3,
  "sync_upserted": 40,
  "sync_errors": 0
}`;

const HANNOM_PIPELINE = `// Pipeline backend (3 bước)
POST /api/web/clc-sinonom/image-upload      // form-data: image_file
POST /api/web/clc-sinonom/image-ocr         // JSON: ocr_id, lang_type, file_name
POST /api/web/clc-sinonom/sinonom-transliteration  // JSON: text, font_type, lang_type`;

const DocsPage = () => (
  <Space direction="vertical" size="large" className="w-full">
    <Typography.Paragraph type="secondary">
      CURL và schema JSON để test nhanh endpoint. Thay <Typography.Text code>JWT_ADMIN</Typography.Text> bằng token sau{" "}
      <Typography.Text code>POST /api/login</Typography.Text>.
    </Typography.Paragraph>

    <Tabs
      items={[
        {
          key: "ocr",
          label: "OCR & Phiên âm",
          children: (
            <Card title="POST /api/documents/{document_id}/ocr-transliterate">
              <Space direction="vertical" size="middle" className="w-full">
                <div>
                  <Typography.Title level={5}>CURL</Typography.Title>
                  <CodeBlock code={OCR_CURL} language="bash" />
                </div>
                <div>
                  <Typography.Title level={5}>Response 200 (schema)</Typography.Title>
                  <CodeBlock code={OCR_RESPONSE} language="json" />
                </div>
              </Space>
            </Card>
          ),
        },
        {
          key: "upload",
          label: "Upload file",
          children: (
            <Card title="POST /api/documents/{document_id}/upload-files">
              <CodeBlock code={UPLOAD_CURL} language="bash" />
            </Card>
          ),
        },
        {
          key: "health",
          label: "Health check",
          children: (
            <Card title="GET /health">
              <CodeBlock code={HEALTH_CURL} language="bash" />
            </Card>
          ),
        },
        {
          key: "crawl",
          label: "Crawl VietnamGiaPha",
          children: (
            <Card title="POST /api/vietnamgiapha/crawl-sync">
              <Space direction="vertical" size="middle" className="w-full">
                <Typography.Paragraph type="secondary">
                  UI: <Typography.Text code>/admin/developer/vietnamgiapha-crawl</Typography.Text>
                </Typography.Paragraph>
                <div>
                  <Typography.Title level={5}>CURL</Typography.Title>
                  <CodeBlock code={CRAWL_CURL} language="bash" />
                </div>
                <div>
                  <Typography.Title level={5}>Response 200 (schema)</Typography.Title>
                  <CodeBlock code={CRAWL_RESPONSE} language="json" />
                </div>
              </Space>
            </Card>
          ),
        },
        {
          key: "hannom",
          label: "Kim Hán Nôm upstream",
          children: (
            <Card title="Pipeline fit.hcmus.edu.vn (server-side)">
              <CodeBlock code={HANNOM_PIPELINE} language="text" />
            </Card>
          ),
        },
      ]}
    />
  </Space>
);

export default DocsPage;
