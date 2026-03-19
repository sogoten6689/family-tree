import { useEffect, useRef, useState } from 'react';
import {
  ArrowLeftOutlined,
  EyeOutlined,
  FileImageOutlined,
  FileTextOutlined,
  InboxOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { Alert, Button, Card, Descriptions, Empty, Spin, Tabs, Tag, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

type PreviewType = 'image' | 'docx' | 'unsupported' | null;

type MammothModule = typeof import('mammoth/mammoth.browser');

const supportedFormats = ['.docx', '.doc', '.png', '.jpg', '.jpeg', '.webp'];

const DocumentReaderPage = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [activeFile, setActiveFile] = useState<File | null>(null);
  const [previewType, setPreviewType] = useState<PreviewType>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [documentText, setDocumentText] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [imageUrl]);

  const resetPreview = () => {
    if (imageUrl) {
      URL.revokeObjectURL(imageUrl);
    }

    setActiveFile(null);
    setPreviewType(null);
    setImageUrl(null);
    setDocumentText('');
    setStatusMessage(null);
    setErrorMessage(null);
    setIsParsing(false);
  };

  const loadFile = async (file: File) => {
    if (imageUrl) {
      URL.revokeObjectURL(imageUrl);
    }

    setActiveFile(file);
    setErrorMessage(null);
    setStatusMessage(null);
    setDocumentText('');
    setImageUrl(null);
    setIsParsing(false);

    const lowerName = file.name.toLowerCase();

    if (file.type.startsWith('image/') || /\.(png|jpe?g|webp)$/i.test(lowerName)) {
      setPreviewType('image');
      setImageUrl(URL.createObjectURL(file));
      setStatusMessage('Da tai anh len thanh cong. Ban co the phong to va doi chieu noi dung gia pha truc tiep.');
      return;
    }

    if (/\.docx$/i.test(lowerName)) {
      setPreviewType('docx');
      setIsParsing(true);

      try {
        const mammothModule: MammothModule = await import('mammoth/mammoth.browser');
        const arrayBuffer = await file.arrayBuffer();
        const result = await mammothModule.extractRawText({ arrayBuffer });
        const normalizedText = result.value.replace(/\n{3,}/g, '\n\n').trim();

        setDocumentText(normalizedText || 'Khong trich xuat duoc noi dung van ban tu tep nay.');
        setStatusMessage('Da doc noi dung Word va chuyen sang che do doc van ban thuan de ban ra soat thong tin.');
      } catch (error) {
        setErrorMessage('Khong the doc tep Word nay. Hay thu tep .docx khac hoac chuyen sang anh scan.');
      } finally {
        setIsParsing(false);
      }

      return;
    }

    if (/\.doc$/i.test(lowerName)) {
      setPreviewType('unsupported');
      setErrorMessage('Tep .doc cu chua duoc trich xuat truc tiep tren trinh duyet. Hay chuyen sang .docx de doc noi dung.');
      return;
    }

    setPreviewType('unsupported');
    setErrorMessage('Dinh dang chua duoc ho tro. Hay dung tep Word .docx hoac anh scan.');
  };

  const handleSelectedFiles = async (files: FileList | File[]) => {
    const firstFile = Array.from(files)[0];
    if (!firstFile) {
      return;
    }

    await loadFile(firstFile);
  };

  const handleDrop: React.DragEventHandler<HTMLDivElement> = async (event) => {
    event.preventDefault();
    setIsDragging(false);
    await handleSelectedFiles(event.dataTransfer.files);
  };

  return (
    <div className="min-h-screen bg-background">
      <header
        className="px-6 py-4 flex items-center justify-between border-b"
        style={{ borderColor: 'hsl(36, 30%, 80%)' }}
      >
        <div className="flex items-center gap-4">
          <Button
            icon={<ArrowLeftOutlined />}
            type="text"
            onClick={() => navigate('/')}
            style={{ color: 'hsl(36, 70%, 42%)' }}
          >
            Trang chu
          </Button>
          <div className="section-divider w-px h-6 mx-2" style={{ width: 1, background: 'hsl(36, 30%, 80%)' }} />
          <div>
            <h1 className="text-2xl font-display font-bold text-foreground">Phong doc tu lieu gia pha</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Keo tha tep Word hoac anh scan de doc tu lieu goc truoc khi trich xuat cay gia pha.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Tag color="gold">Word va anh</Tag>
          <Tag color="red">Ho tro keo tha</Tag>
        </div>
      </header>

      <section className="gold-gradient px-6 py-5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 text-parchment">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-parchment/80">Khoi tiep nhan tai lieu</p>
            <h2 className="text-3xl font-display font-bold mt-2">Doc nhanh van ban phien am va anh scan gia pha</h2>
          </div>
          <div className="max-w-xl text-sm text-parchment/90 leading-6">
            Giao dien nay phu hop cho giai doan soat tai lieu: xem anh, doc noi dung Word, doi chieu du lieu truoc khi dua vao quy trinh phan tich.
          </div>
        </div>
      </section>

      <main className="px-6 py-8">
        <div className="max-w-7xl mx-auto grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
          <div className="space-y-6">
            <Card
              bordered={false}
              style={{
                background: isDragging ? 'hsl(39, 60%, 88%)' : 'hsl(39, 40%, 93%)',
                boxShadow: isDragging ? '0 20px 60px hsl(36 70% 42% / 0.16)' : '0 12px 36px hsl(20 40% 25% / 0.08)',
              }}
              styles={{ body: { padding: 24 } }}
            >
              <div
                className="rounded-2xl border-2 border-dashed p-8 text-center transition-all"
                style={{
                  borderColor: isDragging ? 'hsl(0, 45%, 35%)' : 'hsl(36, 45%, 58%)',
                  background: isDragging ? 'hsl(39, 60%, 92%)' : 'hsl(39, 50%, 96%)',
                }}
                onDragEnter={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={(event) => {
                  event.preventDefault();
                  setIsDragging(false);
                }}
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDrop={handleDrop}
              >
                <div
                  className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-full"
                  style={{ background: 'linear-gradient(135deg, hsl(36 70% 42%), hsl(0 45% 35%))', color: 'hsl(39 50% 96%)' }}
                >
                  <InboxOutlined style={{ fontSize: 34 }} />
                </div>

                <Typography.Title level={4} style={{ marginBottom: 8, fontFamily: 'var(--font-display)' }}>
                  Tha tep vao day
                </Typography.Title>
                <Typography.Paragraph style={{ color: 'hsl(20, 15%, 45%)', marginBottom: 20 }}>
                  Ho tro xem anh scan va doc noi dung Word phuc vu nghien cuu gia pha Hán Nôm.
                </Typography.Paragraph>

                <div className="flex flex-wrap justify-center gap-2 mb-6">
                  {supportedFormats.map((format) => (
                    <Tag key={format} style={{ paddingInline: 10, paddingBlock: 4 }}>
                      {format}
                    </Tag>
                  ))}
                </div>

                <div className="flex justify-center gap-3 flex-wrap">
                  <Button type="primary" size="large" onClick={() => fileInputRef.current?.click()}>
                    Chon tep de doc
                  </Button>
                  <Button icon={<ReloadOutlined />} size="large" onClick={resetPreview}>
                    Lam moi
                  </Button>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".doc,.docx,image/png,image/jpeg,image/webp"
                  className="hidden"
                  onChange={async (event) => {
                    if (event.target.files) {
                      await handleSelectedFiles(event.target.files);
                      event.target.value = '';
                    }
                  }}
                />
              </div>
            </Card>

            <Card bordered={false} style={{ background: 'hsl(39, 40%, 93%)' }}>
              <Typography.Title level={4} style={{ fontFamily: 'var(--font-display)', marginBottom: 16 }}>
                Luong su dung de xuat
              </Typography.Title>
              <div className="space-y-3 text-sm text-muted-foreground leading-6">
                <p>1. Tha anh scan gia pha neu ban muon doi chieu truc tiep voi ban goc.</p>
                <p>2. Tha tep .docx neu ban da co ban phien am hoac da danh may.</p>
                <p>3. Ra soat noi dung, sau do chuyen sang buoc trich xuat thong tin thanh vien va quan he.</p>
              </div>
            </Card>
          </div>

          <Card
            bordered={false}
            style={{ background: 'linear-gradient(180deg, hsl(39 50% 96%), hsl(39 40% 93%))', minHeight: 640 }}
            styles={{ body: { padding: 24, height: '100%' } }}
          >
            <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
              <div>
                <Typography.Title level={3} style={{ marginBottom: 4, fontFamily: 'var(--font-display)' }}>
                  Khu vuc doc tai lieu
                </Typography.Title>
                <Typography.Text type="secondary">
                  Xem truoc tep goc va lay noi dung de phan tich gia pha.
                </Typography.Text>
              </div>

              {activeFile && (
                <Tag color="processing" style={{ paddingInline: 10, paddingBlock: 6 }}>
                  {activeFile.name}
                </Tag>
              )}
            </div>

            {statusMessage && (
              <Alert
                showIcon
                type="success"
                message="Tai lieu da duoc nap"
                description={statusMessage}
                style={{ marginBottom: 16 }}
              />
            )}

            {errorMessage && (
              <Alert
                showIcon
                type="warning"
                message="Can luu y"
                description={errorMessage}
                style={{ marginBottom: 16 }}
              />
            )}

            {isParsing ? (
              <div className="h-[520px] flex items-center justify-center rounded-2xl" style={{ background: 'hsl(39, 50%, 96%)' }}>
                <div className="text-center">
                  <Spin size="large" />
                  <Typography.Paragraph style={{ marginTop: 16, marginBottom: 0, color: 'hsl(20, 15%, 45%)' }}>
                    Dang doc va trich xuat noi dung Word...
                  </Typography.Paragraph>
                </div>
              </div>
            ) : !activeFile ? (
              <div className="h-[520px] flex items-center justify-center rounded-2xl border border-dashed" style={{ borderColor: 'hsl(36, 30%, 80%)', background: 'hsl(39, 50%, 96%)' }}>
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="Chua co tai lieu nao duoc mo"
                />
              </div>
            ) : (
              <Tabs
                defaultActiveKey="preview"
                items={[
                  {
                    key: 'preview',
                    label: (
                      <span>
                        <EyeOutlined /> Xem truoc
                      </span>
                    ),
                    children: (
                      <div className="rounded-2xl border overflow-hidden" style={{ borderColor: 'hsl(36, 30%, 80%)' }}>
                        {previewType === 'image' && imageUrl ? (
                          <div className="max-h-[620px] overflow-auto bg-[hsl(39,50%,96%)] p-4">
                            <img
                              src={imageUrl}
                              alt={activeFile.name}
                              className="mx-auto max-w-full rounded-xl shadow-lg"
                            />
                          </div>
                        ) : previewType === 'docx' ? (
                          <div className="h-[620px] overflow-auto bg-[hsl(39,50%,96%)] px-8 py-6">
                            <article className="mx-auto max-w-4xl whitespace-pre-wrap text-[15px] leading-8 text-foreground">
                              {documentText}
                            </article>
                          </div>
                        ) : (
                          <div className="h-[520px] flex items-center justify-center bg-[hsl(39,50%,96%)]">
                            <Empty description="Khong co xem truoc cho dinh dang nay" />
                          </div>
                        )}
                      </div>
                    ),
                  },
                  {
                    key: 'info',
                    label: (
                      <span>
                        <FileTextOutlined /> Thong tin tep
                      </span>
                    ),
                    children: activeFile ? (
                      <Card bordered={false} style={{ background: 'hsl(39, 50%, 96%)' }}>
                        <Descriptions column={1} bordered size="middle">
                          <Descriptions.Item label="Ten tep">{activeFile.name}</Descriptions.Item>
                          <Descriptions.Item label="Loai tep">{activeFile.type || 'Khong xac dinh'}</Descriptions.Item>
                          <Descriptions.Item label="Dung luong">
                            {(activeFile.size / 1024 / 1024).toFixed(2)} MB
                          </Descriptions.Item>
                          <Descriptions.Item label="Che do doc">
                            {previewType === 'image'
                              ? 'Xem anh scan'
                              : previewType === 'docx'
                                ? 'Doc van ban Word'
                                : 'Chi luu tep, chua phan tich'}
                          </Descriptions.Item>
                        </Descriptions>

                        <div className="grid gap-4 md:grid-cols-2 mt-6">
                          <Card size="small" style={{ background: 'hsl(39, 40%, 93%)' }}>
                            <div className="flex items-center gap-3 mb-2">
                              <FileImageOutlined style={{ color: 'hsl(36, 70%, 42%)' }} />
                              <span className="font-medium">Anh scan</span>
                            </div>
                            <p className="mb-0 text-sm text-muted-foreground leading-6">
                              Phu hop voi tu lieu chup, scan trang gia pha, can doi chieu bo cuc va ky tu goc.
                            </p>
                          </Card>

                          <Card size="small" style={{ background: 'hsl(39, 40%, 93%)' }}>
                            <div className="flex items-center gap-3 mb-2">
                              <FileTextOutlined style={{ color: 'hsl(0, 45%, 35%)' }} />
                              <span className="font-medium">Van ban Word</span>
                            </div>
                            <p className="mb-0 text-sm text-muted-foreground leading-6">
                              Phu hop voi ban phien am hoac danh may, giup lay text nhanh de dua vao pipeline trich xuat.
                            </p>
                          </Card>
                        </div>
                      </Card>
                    ) : null,
                  },
                ]}
              />
            )}
          </Card>
        </div>
      </main>
    </div>
  );
};

export default DocumentReaderPage;