import { useState } from "react";
import { Button, Card, Input, Row, Col, Space, Spin, message, Statistic, Tabs, Table, Typography, Empty, Tag, Divider } from "antd";
import { CopyOutlined, ClearOutlined, ThunderboltOutlined, FileTextOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

const { TextArea } = Input;
const { Title, Paragraph, Text } = Typography;

interface GenealogyResult {
  persons: string[];
  person_years: Record<string, number>;
  relations: Array<{
    head: string;
    type: string;
    tail: string;
    confidence: number;
  }>;
  statistics: {
    person_count: number;
    relation_count: number;
  };
}

const EXAMPLE_TEXTS = {
  example1: `Ông Nguyễn Văn An sinh năm 1945, kết hôn với bà Trần Thị Hạnh sinh năm 1948.
Ông Nguyễn Văn An và bà Trần Thị Hạnh có con là Nguyễn Văn Bình sinh năm 1972, Nguyễn Thị Lan sinh năm 1975.
Nguyễn Văn Bình cưới Lê Thị Hoa năm 1998.
Nguyễn Văn Bình và Lê Thị Hoa có con là Nguyễn Minh Đức sinh năm 2000.
Nguyễn Thị Lan là con của Nguyễn Văn An và Trần Thị Hạnh.
Nguyễn Minh Đức, cha là Nguyễn Văn Bình, mẹ là Lê Thị Hoa.
Nguyễn Văn Bình và Nguyễn Thị Lan là anh em trong gia đình.`,

  example2: `Bà Phạm Thị H (sinh năm 1930) kết hôn với ông Trần Văn K. Bà H mất năm 2001.`,

  example3: `Ông Trần Văn A sinh năm 1940, kết hôn với bà Ngô Thị B sinh năm 1945.
Họ có ba con: Trần Văn C (1965), Trần Thị D (1968), Trần Văn E (1970).
Trần Văn C cưới Hoàng Thị F năm 1990, có con là Trần Huy G (1992).
Trần Thị D lấy Lý Văn H, sinh con Lý Công I (1995).`,
};

export default function GenealogyExtractorPage() {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [result, setResult] = useState<GenealogyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("persons");

  const handleExtract = async () => {
    if (!text.trim()) {
      message.error("Vui lòng nhập văn bản gia phả");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch("/api/genealogy/extract", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          language: "vietnamese",
        }),
      });

      if (!response.ok) {
        throw new Error("Lỗi trích xuất gia phả");
      }

      const data = await response.json();
      setResult(data);
      message.success("Trích xuất gia phả thành công!");
    } catch (error) {
      message.error(`Lỗi: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadExample = (exampleKey: keyof typeof EXAMPLE_TEXTS) => {
    setText(EXAMPLE_TEXTS[exampleKey]);
  };

  const handleClear = () => {
    setText("");
    setResult(null);
  };

  const relationColumns = [
    {
      title: "Người thứ nhất",
      dataIndex: "head",
      key: "head",
      width: 200,
    },
    {
      title: "Quan hệ",
      dataIndex: "type",
      key: "type",
      render: (type: string) => {
        const typeMap = { spouse: "Vợ/Chồng", parent: "Cha/Mẹ", sibling: "Anh/Chị/Em" };
        const typeLabel = typeMap[type as keyof typeof typeMap] || type;
        const colorMap = { spouse: "cyan", parent: "blue", sibling: "green" };
        return (
          <Tag color={colorMap[type as keyof typeof colorMap] || "default"}>
            {typeLabel}
          </Tag>
        );
      },
      width: 120,
    },
    {
      title: "Người thứ hai",
      dataIndex: "tail",
      key: "tail",
      width: 200,
    },
    {
      title: "Độ tin cậy",
      dataIndex: "confidence",
      key: "confidence",
      render: (confidence: number) => `${Math.round(confidence * 100)}%`,
      width: 100,
    },
  ];

  return (
    <div style={{ padding: "24px", maxWidth: "1200px", margin: "0 auto" }}>
      <Title level={2}>
        <FileTextOutlined /> Trích Xuất Gia Phả
      </Title>
      <Paragraph>
        Dán văn bản gia phả tiếng Việt để tự động trích xuất nhân vật, quan hệ gia đình và năm sinh/mất.
      </Paragraph>

      <Row gutter={[24, 24]}>
        {/* Input Section */}
        <Col xs={24} lg={12}>
          <Card title="📝 Nhập Văn Bản" bordered>
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <TextArea
                rows={10}
                placeholder="Dán văn bản gia phả tiếng Việt..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={loading}
              />

              <Space wrap>
                <Button
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  onClick={handleExtract}
                  loading={loading}
                  size="large"
                >
                  Trích xuất
                </Button>
                <Button icon={<ClearOutlined />} onClick={handleClear} disabled={loading}>
                  Xóa
                </Button>
              </Space>

              <Divider />

              <Title level={5}>📚 Ví Dụ Test</Title>
              <Space wrap>
                <Button
                  type="dashed"
                  onClick={() => handleLoadExample("example1")}
                  disabled={loading}
                  size="small"
                >
                  Test 1: Gia đình Nguyễn
                </Button>
                <Button
                  type="dashed"
                  onClick={() => handleLoadExample("example2")}
                  disabled={loading}
                  size="small"
                >
                  Test 2: Cặp vợ chồng
                </Button>
                <Button
                  type="dashed"
                  onClick={() => handleLoadExample("example3")}
                  disabled={loading}
                  size="small"
                >
                  Test 3: 3+ thế hệ
                </Button>
              </Space>
            </Space>
          </Card>
        </Col>

        {/* Result Section */}
        <Col xs={24} lg={12}>
          <Card title="📊 Kết Quả" bordered>
            {loading ? (
              <Spin tip="Đang xử lý..." />
            ) : result ? (
              <Space direction="vertical" style={{ width: "100%" }} size="large">
                <Row gutter={16}>
                  <Col xs={12}>
                    <Statistic
                      title="Nhân vật"
                      value={result.statistics.person_count}
                      valueStyle={{ color: "#1890ff" }}
                    />
                  </Col>
                  <Col xs={12}>
                    <Statistic
                      title="Quan hệ"
                      value={result.statistics.relation_count}
                      valueStyle={{ color: "#52c41a" }}
                    />
                  </Col>
                </Row>

                <Tabs
                  activeKey={activeTab}
                  onChange={setActiveTab}
                  items={[
                    {
                      key: "persons",
                      label: "Nhân vật",
                      children: (
                        <div>
                          {result.persons.length > 0 ? (
                            <Space direction="vertical" style={{ width: "100%" }}>
                              {result.persons.map((person) => (
                                <div key={person} style={{ wordBreak: "break-word" }}>
                                  <Text strong>{person}</Text>
                                  {result.person_years[person] && (
                                    <Text type="secondary" style={{ marginLeft: "8px" }}>
                                      (sinh {result.person_years[person]})
                                    </Text>
                                  )}
                                </div>
                              ))}
                            </Space>
                          ) : (
                            <Empty description="Không tìm thấy nhân vật" />
                          )}
                        </div>
                      ),
                    },
                    {
                      key: "relations",
                      label: "Quan hệ",
                      children: (
                        <Table
                          columns={relationColumns}
                          dataSource={result.relations}
                          rowKey={(record) =>
                            `${record.head}-${record.type}-${record.tail}`
                          }
                          pagination={false}
                          size="small"
                          scroll={{ x: true }}
                        />
                      ),
                    },
                    {
                      key: "json",
                      label: "JSON",
                      children: (
                        <div
                          style={{
                            background: "rgba(0, 0, 0, 0.05)",
                            padding: "12px",
                            borderRadius: "4px",
                            maxHeight: "400px",
                            overflow: "auto",
                            fontFamily: "monospace",
                            fontSize: "12px",
                            color: "currentColor",
                          }}
                        >
                          <pre style={{ margin: 0, color: "currentColor" }}>{JSON.stringify(result, null, 2)}</pre>
                        </div>
                      ),
                    },
                  ]}
                />
              </Space>
            ) : (
              <Empty description="Nhập văn bản để xem kết quả" />
            )}
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: "24px" }}>
        <Title level={5}>ℹ️ Thông Tin</Title>
        <Paragraph>
          <strong>Độ chính xác:</strong> 60% trên dữ liệu gia phả đa dạng (phiên bản MVP)
        </Paragraph>
        <Paragraph>
          <strong>Hỗ trợ:</strong> Tiếng Việt (Vietnamese only)
        </Paragraph>
        <Paragraph>
          <strong>Tốc độ:</strong> &lt;1ms per document
        </Paragraph>
        <Paragraph>
          <strong>Giới hạn:</strong> Parser dựa trên regex - hiệu suất giảm trên văn bản phức tạp. Sẽ được nâng cấp
          thành phiên bản ML-based cho độ chính xác 90%+ trong tương lai.
        </Paragraph>
      </Card>
    </div>
  );
}
