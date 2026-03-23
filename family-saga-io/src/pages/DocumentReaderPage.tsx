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
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '@/components/LanguageSwitcher';
import ThemeToggle from '@/components/ThemeToggle';

type PreviewType = 'image' | 'docx' | 'unsupported' | null;

type MammothModule = typeof import('mammoth/mammoth.browser');
type DetectedLanguageCode = 'vi' | 'en' | 'unknown';
type DetectionMethod = 'text-heuristic' | 'filename-heuristic' | 'unavailable';

type LanguageDetection = {
  code: DetectedLanguageCode;
  confidence: number;
  method: DetectionMethod;
};

const supportedFormats = ['.docx', '.doc', '.png', '.jpg', '.jpeg', '.webp'];
const viMarkRegex = /[\u00c0-\u1ef9\u0110\u0111]/g;
const viKeywords = ['gia', 'pha', 'phả', 'dong', 'dòng', 'ho', 'họ', 'ong', 'ông', 'ba', 'bà', 'con', 'chau', 'cháu', 'nam', 'năm', 'sinh', 'mat', 'mất'];
const enKeywords = ['family', 'tree', 'lineage', 'ancestor', 'generation', 'born', 'died', 'child', 'children', 'name', 'year', 'father', 'mother'];

const countKeywordHits = (text: string, keywords: string[]) => {
  const tokens = text
    .toLowerCase()
    .replace(/[^\p{L}\s]/gu, ' ')
    .split(/\s+/)
    .filter(Boolean);

  return tokens.reduce((sum, token) => sum + (keywords.includes(token) ? 1 : 0), 0);
};

const detectLanguageFromFilename = (name: string): LanguageDetection => {
  const lowerName = name.toLowerCase();

  if (/([._-]vi[._-])|vietnamese|tieng-viet|tiếng-việt/.test(lowerName)) {
    return { code: 'vi', confidence: 0.62, method: 'filename-heuristic' };
  }

  if (/([._-]en[._-])|english/.test(lowerName)) {
    return { code: 'en', confidence: 0.62, method: 'filename-heuristic' };
  }

  return { code: 'unknown', confidence: 0.2, method: 'unavailable' };
};

const detectLanguage = (text: string, fileName: string): LanguageDetection => {
  const normalized = text.trim();
  if (normalized.length < 40) {
    return detectLanguageFromFilename(fileName);
  }

  const viMarks = (normalized.match(viMarkRegex) ?? []).length;
  const viHits = countKeywordHits(normalized, viKeywords);
  const enHits = countKeywordHits(normalized, enKeywords);
  const viScore = viMarks * 2 + viHits;
  const enScore = enHits;

  if (viScore >= enScore + 2) {
    const confidence = Math.min(0.96, 0.55 + (viScore - enScore) * 0.05);
    return { code: 'vi', confidence, method: 'text-heuristic' };
  }

  if (enScore >= viScore + 2) {
    const confidence = Math.min(0.94, 0.55 + (enScore - viScore) * 0.05);
    return { code: 'en', confidence, method: 'text-heuristic' };
  }

  const fallback = detectLanguageFromFilename(fileName);
  if (fallback.code !== 'unknown') {
    return fallback;
  }

  return { code: 'unknown', confidence: 0.3, method: 'text-heuristic' };
};

const DocumentReaderPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [activeFile, setActiveFile] = useState<File | null>(null);
  const [previewType, setPreviewType] = useState<PreviewType>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [documentText, setDocumentText] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [languageDetection, setLanguageDetection] = useState<LanguageDetection | null>(null);

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
    setLanguageDetection(null);
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
    setLanguageDetection(null);

    const lowerName = file.name.toLowerCase();

    if (file.type.startsWith('image/') || /\.(png|jpe?g|webp)$/i.test(lowerName)) {
      setPreviewType('image');
      setImageUrl(URL.createObjectURL(file));
      setLanguageDetection(detectLanguageFromFilename(file.name));
      setStatusMessage(t('docReader.msgImageSuccess'));
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

        setDocumentText(normalizedText || t('docReader.msgEmptyDocx'));
        setLanguageDetection(detectLanguage(normalizedText, file.name));
        setStatusMessage(t('docReader.msgDocxSuccess'));
      } catch (error) {
        setErrorMessage(t('docReader.errDocxParse'));
      } finally {
        setIsParsing(false);
      }

      return;
    }

    if (/\.doc$/i.test(lowerName)) {
      setPreviewType('unsupported');
      setLanguageDetection(detectLanguageFromFilename(file.name));
      setErrorMessage(t('docReader.errDocOld'));
      return;
    }

    setPreviewType('unsupported');
    setLanguageDetection(detectLanguageFromFilename(file.name));
    setErrorMessage(t('docReader.errUnsupported'));
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
            {t('common.backHome')}
          </Button>
          <div className="section-divider w-px h-6 mx-2" style={{ width: 1, background: 'hsl(36, 30%, 80%)' }} />
          <div>
            <h1 className="text-2xl font-display font-bold text-foreground">{t('docReader.pageTitle')}</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {t('docReader.pageSubtitle')}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Tag color="gold">{t('docReader.tagFormats')}</Tag>
          <Tag color="red">{t('docReader.tagDragDrop')}</Tag>
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </header>

      <section className="gold-gradient px-6 py-5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 text-parchment">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-parchment/80">{t('docReader.bannerLabel')}</p>
            <h2 className="text-3xl font-display font-bold mt-2">{t('docReader.bannerTitle')}</h2>
          </div>
          <div className="max-w-xl text-sm text-parchment/90 leading-6">
            {t('docReader.bannerDesc')}
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
                  {t('docReader.dropTitle')}
                </Typography.Title>
                <Typography.Paragraph style={{ color: 'hsl(20, 15%, 45%)', marginBottom: 20 }}>
                  {t('docReader.dropDesc')}
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
                    {t('docReader.btnChooseFile')}
                  </Button>
                  <Button icon={<ReloadOutlined />} size="large" onClick={resetPreview}>
                    {t('docReader.btnReset')}
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
                {t('docReader.workflowTitle')}
              </Typography.Title>
              <div className="space-y-3 text-sm text-muted-foreground leading-6">
                <p>{t('docReader.step1')}</p>
                <p>{t('docReader.step2')}</p>
                <p>{t('docReader.step3')}</p>
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
                  {t('docReader.previewAreaTitle')}
                </Typography.Title>
                <Typography.Text type="secondary">
                  {t('docReader.previewAreaSubtitle')}
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
                message={t('docReader.successTitle')}
                description={
                  <div>
                    <div>{statusMessage}</div>
                    {languageDetection && (
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <Tag color="processing">
                          {t('docReader.detectedLanguage', { lang: t(`docReader.lang.${languageDetection.code}`) })}
                        </Tag>
                        <Tag>
                          {t('docReader.detectedBy', { method: t(`docReader.method.${languageDetection.method}`) })}
                        </Tag>
                      </div>
                    )}
                  </div>
                }
                style={{ marginBottom: 16 }}
              />
            )}

            {errorMessage && (
              <Alert
                showIcon
                type="warning"
                message={t('docReader.warningTitle')}
                description={errorMessage}
                style={{ marginBottom: 16 }}
              />
            )}

            {isParsing ? (
              <div className="h-[520px] flex items-center justify-center rounded-2xl" style={{ background: 'hsl(39, 50%, 96%)' }}>
                <div className="text-center">
                  <Spin size="large" />
                  <Typography.Paragraph style={{ marginTop: 16, marginBottom: 0, color: 'hsl(20, 15%, 45%)' }}>
                    {t('docReader.parsing')}
                  </Typography.Paragraph>
                </div>
              </div>
            ) : !activeFile ? (
              <div className="h-[520px] flex items-center justify-center rounded-2xl border border-dashed" style={{ borderColor: 'hsl(36, 30%, 80%)', background: 'hsl(39, 50%, 96%)' }}>
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={t('docReader.noDocument')}
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
                        <EyeOutlined /> {t('docReader.tabPreview')}
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
                            <Empty description={t('docReader.noPreview')} />
                          </div>
                        )}
                      </div>
                    ),
                  },
                  {
                    key: 'info',
                    label: (
                      <span>
                        <FileTextOutlined /> {t('docReader.tabInfo')}
                      </span>
                    ),
                    children: activeFile ? (
                      <Card bordered={false} style={{ background: 'hsl(39, 50%, 96%)' }}>
                        <Descriptions column={1} bordered size="middle">
                          <Descriptions.Item label={t('docReader.fileInfoName')}>{activeFile.name}</Descriptions.Item>
                          <Descriptions.Item label={t('docReader.fileInfoType')}>{activeFile.type || t('docReader.unknownType')}</Descriptions.Item>
                          <Descriptions.Item label={t('docReader.fileInfoSize')}>
                            {(activeFile.size / 1024 / 1024).toFixed(2)} MB
                          </Descriptions.Item>
                          <Descriptions.Item label={t('docReader.fileInfoMode')}>
                            {previewType === 'image'
                              ? t('docReader.modeImage')
                              : previewType === 'docx'
                                ? t('docReader.modeDocx')
                                : t('docReader.modeUnsupported')}
                          </Descriptions.Item>
                          <Descriptions.Item label={t('docReader.fileInfoLanguage')}>
                            {languageDetection ? t(`docReader.lang.${languageDetection.code}`) : t('docReader.lang.unknown')}
                          </Descriptions.Item>
                          <Descriptions.Item label={t('docReader.fileInfoDetectionMethod')}>
                            {languageDetection ? t(`docReader.method.${languageDetection.method}`) : t('docReader.method.unavailable')}
                          </Descriptions.Item>
                          <Descriptions.Item label={t('docReader.fileInfoDetectionConfidence')}>
                            {languageDetection ? `${Math.round(languageDetection.confidence * 100)}%` : '-'}
                          </Descriptions.Item>
                        </Descriptions>

                        <div className="grid gap-4 md:grid-cols-2 mt-6">
                          <Card size="small" style={{ background: 'hsl(39, 40%, 93%)' }}>
                            <div className="flex items-center gap-3 mb-2">
                              <FileImageOutlined style={{ color: 'hsl(36, 70%, 42%)' }} />
                              <span className="font-medium">{t('docReader.cardImageTitle')}</span>
                            </div>
                            <p className="mb-0 text-sm text-muted-foreground leading-6">
                              {t('docReader.cardImageDesc')}
                            </p>
                          </Card>

                          <Card size="small" style={{ background: 'hsl(39, 40%, 93%)' }}>
                            <div className="flex items-center gap-3 mb-2">
                              <FileTextOutlined style={{ color: 'hsl(0, 45%, 35%)' }} />
                              <span className="font-medium">{t('docReader.cardDocxTitle')}</span>
                            </div>
                            <p className="mb-0 text-sm text-muted-foreground leading-6">
                              {t('docReader.cardDocxDesc')}
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