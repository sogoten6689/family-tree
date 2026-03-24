import { useEffect, useRef, useState } from 'react';
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileImageOutlined,
  FileTextOutlined,
  HistoryOutlined,
  InboxOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { Alert, Button, Card, Descriptions, Empty, Modal, Spin, Tabs, Tag, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '@/components/LanguageSwitcher';
import ThemeToggle from '@/components/ThemeToggle';

type PreviewType = 'image' | 'docx' | 'text' | 'unsupported' | null;

type MammothModule = typeof import('mammoth/mammoth.browser');
type DetectedLanguageCode = 'vi' | 'en' | 'unknown';
type DetectionMethod = 'text-heuristic' | 'filename-heuristic' | 'unavailable';

type FamilyAnalyzeResponse = {
  request_id?: string;
  created_at?: string;
  source: string;
  metadata: Record<string, unknown>;
  people_count: number;
  relationship_count: number;
  warnings: string[];
  extraction: Record<string, unknown>;
  tree_architecture: Record<string, unknown>;
  tree: Array<Record<string, unknown>>;
};

type AnalyzedTreeNode = {
  id: string;
  full_name?: string;
  birth_year?: number | null;
  death_year?: number | null;
  children?: AnalyzedTreeNode[];
};

type LanguageDetection = {
  code: DetectedLanguageCode;
  confidence: number;
  method: DetectionMethod;
};

type HistoryItem = {
  request_id: string;
  created_at: string;
  source: string;
  metadata: Record<string, unknown>;
  people_count: number;
  relationship_count: number;
  warning_count: number;
};

type HistoryResponse = {
  total: number;
  items: HistoryItem[];
};

const supportedFormats = ['.docx', '.txt', '.doc', '.png', '.jpg', '.jpeg', '.webp'];
const backendBaseUrl = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000';
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
  const [analysisResult, setAnalysisResult] = useState<FamilyAnalyzeResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isResultModalOpen, setIsResultModalOpen] = useState(false);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selectedHistoryRequestId, setSelectedHistoryRequestId] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [imageUrl]);

  const fetchHistory = async () => {
    setIsHistoryLoading(true);
    setHistoryError(null);

    try {
      const response = await fetch(`${backendBaseUrl}/api/family-tree/history?limit=10`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = (await response.json()) as HistoryResponse;
      setHistoryItems(payload.items ?? []);
      setHistoryTotal(payload.total ?? 0);
    } catch {
      setHistoryError(t('docReader.historyLoadFailed'));
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleClearHistory = async () => {
    setIsHistoryLoading(true);
    setHistoryError(null);

    try {
      const response = await fetch(`${backendBaseUrl}/api/family-tree/history`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      setHistoryItems([]);
      setHistoryTotal(0);
      setSelectedHistoryRequestId(null);
      setStatusMessage(t('docReader.historyCleared'));
    } catch {
      setHistoryError(t('docReader.historyClearFailed'));
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleLoadHistoryDetail = async (requestId: string) => {
    setIsHistoryLoading(true);
    setHistoryError(null);
    setSelectedHistoryRequestId(requestId);

    try {
      const response = await fetch(`${backendBaseUrl}/api/family-tree/history/${requestId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = (await response.json()) as FamilyAnalyzeResponse;
      setAnalysisResult(payload);
      setIsResultModalOpen(true);
      localStorage.setItem('family-tree.analysis', JSON.stringify(payload));
      setStatusMessage(
        t('docReader.historyLoaded', {
          requestId,
          members: payload.people_count,
          relations: payload.relationship_count,
        }),
      );
    } catch {
      setHistoryError(t('docReader.historyDetailLoadFailed'));
    } finally {
      setIsHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    setAnalysisResult(null);
    setAnalysisError(null);
    setIsAnalyzing(false);
    setIsResultModalOpen(false);
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
    setAnalysisResult(null);
    setAnalysisError(null);
    setIsAnalyzing(false);
    setIsResultModalOpen(false);

    const lowerName = file.name.toLowerCase();

    if (file.type.startsWith('image/') || /\.(png|jpe?g|webp)$/i.test(lowerName)) {
      setPreviewType('image');
      setImageUrl(URL.createObjectURL(file));
      setLanguageDetection(detectLanguageFromFilename(file.name));
      setStatusMessage(t('docReader.msgImageSuccess'));
      return;
    }

    if (/\.txt$/i.test(lowerName)) {
      setPreviewType('text');
      setIsParsing(true);

      try {
        const rawText = await file.text();
        const normalizedText = rawText.replace(/\n{3,}/g, '\n\n').trim();
        setDocumentText(normalizedText || t('docReader.msgEmptyDocx'));
        setLanguageDetection(detectLanguage(normalizedText, file.name));
        setStatusMessage(t('docReader.msgTxtSuccess'));
      } catch (error) {
        setErrorMessage(t('docReader.errTxtRead'));
      } finally {
        setIsParsing(false);
      }

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

  const handleAnalyzeFamilyTree = async () => {
    if ((previewType !== 'docx' && previewType !== 'text') || !documentText.trim()) {
      setAnalysisError(t('docReader.errNeedDocxToAnalyze'));
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      const response = await fetch(`${backendBaseUrl}/api/family-tree/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: documentText,
          source: 'document-reader',
          metadata: {
            fileName: activeFile?.name,
            language: languageDetection?.code ?? 'unknown',
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = (await response.json()) as FamilyAnalyzeResponse;
      setAnalysisResult(payload);
      setIsResultModalOpen(true);
      localStorage.setItem('family-tree.analysis', JSON.stringify(payload));
      fetchHistory();
      setStatusMessage(
        t('docReader.msgAnalyzeSuccess', {
          members: payload.people_count,
          relations: payload.relationship_count,
        }),
      );
    } catch (error) {
      setAnalysisError(t('docReader.errBackendUnavailable'));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const renderAnalyzedTreeNode = (node: AnalyzedTreeNode): React.ReactNode => {
    const children = node.children ?? [];

    return (
      <div key={node.id} className="flex flex-col items-center">
        <Card size="small" className="w-[150px] sm:w-[170px] md:w-[190px]" style={{ background: 'hsl(39, 50%, 96%)' }}>
          <div className="font-semibold text-foreground text-sm leading-5 break-words">{node.full_name || node.id}</div>
          <div className="text-xs text-muted-foreground mt-1">
            {node.birth_year ?? '?'} - {node.death_year ?? t('docReader.present')}
          </div>
        </Card>

        {children.length > 0 && (
          <>
            <div className="tree-connector-v h-5" />
            <div className="flex items-start gap-3 relative mt-1">
              {children.length > 1 && (
                <div className="tree-connector-h absolute top-0 left-10 right-10" />
              )}
              {children.map((child) => (
                <div key={child.id} className="flex flex-col items-center">
                  <div className="tree-connector-v h-5" />
                  {renderAnalyzedTreeNode(child)}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      <header
        className="px-4 md:px-6 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between border-b"
        style={{ borderColor: 'hsl(36, 30%, 80%)' }}
      >
        <div className="w-full md:w-auto flex items-start md:items-center gap-3 md:gap-4">
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
        <div className="w-full md:w-auto flex flex-wrap items-center gap-2 md:gap-3 md:justify-end">
          <Tag color="gold">{t('docReader.tagFormats')}</Tag>
          <Tag color="red">{t('docReader.tagDragDrop')}</Tag>
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </header>

      <section className="gold-gradient px-4 md:px-6 py-5">
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

      <main className="px-4 md:px-6 py-8">
        <div className="max-w-7xl mx-auto grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)] xl:grid-cols-[380px_minmax(0,1fr)]">
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
                  <Button
                    size="large"
                    loading={isAnalyzing}
                    disabled={(previewType !== 'docx' && previewType !== 'text') || !documentText.trim()}
                    onClick={handleAnalyzeFamilyTree}
                  >
                    {t('docReader.btnAnalyzeTree')}
                  </Button>
                  {analysisResult && (
                    <Button size="large" onClick={() => setIsResultModalOpen(true)}>
                      {t('docReader.btnOpenAnalysisPopup')}
                    </Button>
                  )}
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,text/plain,.doc,.docx,image/png,image/jpeg,image/webp"
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

            <Card bordered={false} style={{ background: 'hsl(39, 40%, 93%)' }}>
              <div className="flex items-center justify-between gap-2 mb-3">
                <Typography.Title level={5} style={{ margin: 0, fontFamily: 'var(--font-display)' }}>
                  <HistoryOutlined className="mr-2" />
                  {t('docReader.historyTitle')}
                </Typography.Title>
                <div className="flex items-center gap-2">
                  <Button size="small" icon={<SyncOutlined />} loading={isHistoryLoading} onClick={fetchHistory}>
                    {t('docReader.historyRefresh')}
                  </Button>
                  <Button size="small" danger icon={<DeleteOutlined />} loading={isHistoryLoading} onClick={handleClearHistory}>
                    {t('docReader.historyClear')}
                  </Button>
                </div>
              </div>

              <p className="text-xs text-muted-foreground mb-3">
                {t('docReader.historyTotal', { count: historyTotal })}
              </p>

              {historyError && (
                <Alert
                  showIcon
                  type="error"
                  message={t('docReader.analysisFailedTitle')}
                  description={historyError}
                  style={{ marginBottom: 12 }}
                />
              )}

              {historyItems.length === 0 ? (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('docReader.historyEmpty')} />
              ) : (
                <div className="space-y-2 max-h-56 overflow-auto pr-1">
                  {historyItems.map((item) => (
                    <div
                      key={item.request_id}
                      className={`rounded-lg border px-3 py-2 bg-background/70 ${selectedHistoryRequestId === item.request_id ? 'ring-2 ring-gold' : ''}`}
                    >
                      <div className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()}</div>
                      <div className="text-sm font-medium mt-1 break-all">{item.request_id}</div>
                      <div className="mt-1 flex flex-wrap gap-2">
                        <Tag>{t('docReader.analysisPeople', { count: item.people_count })}</Tag>
                        <Tag>{t('docReader.analysisRelationships', { count: item.relationship_count })}</Tag>
                        {item.warning_count > 0 && (
                          <Tag color="warning">{t('docReader.historyWarnings', { count: item.warning_count })}</Tag>
                        )}
                      </div>
                      <div className="mt-2">
                        <Button
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={() => handleLoadHistoryDetail(item.request_id)}
                          loading={isHistoryLoading && selectedHistoryRequestId === item.request_id}
                        >
                          {t('docReader.historyViewDetail')}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
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

            {analysisError && (
              <Alert
                showIcon
                type="error"
                message={t('docReader.analysisFailedTitle')}
                description={analysisError}
                style={{ marginBottom: 16 }}
              />
            )}

            {analysisResult && (
              <Card
                bordered={false}
                className="mb-4"
                title={t('docReader.analysisInlineTitle')}
                style={{ background: 'hsl(39, 40%, 93%)' }}
              >
                <div className="flex flex-wrap gap-2 mb-3">
                  <Tag color="processing">{t('docReader.analysisPeople', { count: analysisResult.people_count })}</Tag>
                  <Tag color="magenta">{t('docReader.analysisRelationships', { count: analysisResult.relationship_count })}</Tag>
                  <Tag>
                    {t('docReader.analysisRoots', {
                      count: Array.isArray((analysisResult.tree_architecture as { roots?: unknown[] }).roots)
                        ? ((analysisResult.tree_architecture as { roots?: unknown[] }).roots?.length ?? 0)
                        : 0,
                    })}
                  </Tag>
                </div>

                {analysisResult.warnings.length > 0 && (
                  <Alert
                    type="warning"
                    showIcon
                    message={t('docReader.analysisWarnings')}
                    description={analysisResult.warnings.join(' | ')}
                    style={{ marginBottom: 12 }}
                  />
                )}

                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => setIsResultModalOpen(true)}>
                    {t('docReader.btnOpenAnalysisPopup')}
                  </Button>
                  <Button type="primary" onClick={() => navigate('/family-tree')}>
                    {t('docReader.btnOpenTreePage')}
                  </Button>
                </div>

                <Card
                  size="small"
                  className="mt-4"
                  title={t('docReader.inlineTreeTitle')}
                  style={{ background: 'hsl(39, 50%, 96%)' }}
                >
                  {(analysisResult.tree as AnalyzedTreeNode[]).length > 0 ? (
                    <div className="overflow-x-auto py-2">
                      <div className="min-w-max flex items-start justify-center gap-4 sm:gap-6 px-2">
                        {(analysisResult.tree as AnalyzedTreeNode[]).map((rootNode) => renderAnalyzedTreeNode(rootNode))}
                      </div>
                    </div>
                  ) : (
                    <Empty description={t('docReader.inlineTreeEmpty')} />
                  )}
                </Card>
              </Card>
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
                        ) : previewType === 'docx' || previewType === 'text' ? (
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
                                : previewType === 'text'
                                  ? t('docReader.modeText')
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

                        {analysisResult && (
                          <Card
                            size="small"
                            className="mt-6"
                            title={t('docReader.analysisTitle')}
                            style={{ background: 'hsl(39, 40%, 93%)' }}
                          >
                            <div className="flex flex-wrap gap-2 mb-3">
                              <Tag color="processing">
                                {t('docReader.analysisPeople', { count: analysisResult.people_count })}
                              </Tag>
                              <Tag color="magenta">
                                {t('docReader.analysisRelationships', { count: analysisResult.relationship_count })}
                              </Tag>
                              <Tag>
                                {t('docReader.analysisRoots', {
                                  count: Array.isArray((analysisResult.tree_architecture as { roots?: unknown[] }).roots)
                                    ? ((analysisResult.tree_architecture as { roots?: unknown[] }).roots?.length ?? 0)
                                    : 0,
                                })}
                              </Tag>
                            </div>

                            {analysisResult.warnings.length > 0 && (
                              <Alert
                                type="warning"
                                showIcon
                                message={t('docReader.analysisWarnings')}
                                description={analysisResult.warnings.join(' | ')}
                                style={{ marginBottom: 12 }}
                              />
                            )}

                            <pre className="max-h-64 overflow-auto rounded bg-black/5 p-3 text-xs leading-5 text-foreground">
                              {JSON.stringify(analysisResult.tree_architecture, null, 2)}
                            </pre>
                          </Card>
                        )}
                      </Card>
                    ) : null,
                  },
                ]}
              />
            )}
          </Card>
        </div>
      </main>

      <Modal
        open={isResultModalOpen}
        onCancel={() => setIsResultModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsResultModalOpen(false)}>
            {t('familyTree.close')}
          </Button>,
          <Button key="open-tree" type="primary" onClick={() => navigate('/family-tree')}>
            {t('docReader.btnOpenTreePage')}
          </Button>,
        ]}
        title={t('docReader.analysisPopupTitle')}
        width={860}
      >
        {analysisResult && (
          <>
            <div className="flex flex-wrap gap-2 mb-3">
              <Tag color="processing">{t('docReader.analysisPeople', { count: analysisResult.people_count })}</Tag>
              <Tag color="magenta">{t('docReader.analysisRelationships', { count: analysisResult.relationship_count })}</Tag>
              <Tag>
                {t('docReader.analysisRoots', {
                  count: Array.isArray((analysisResult.tree_architecture as { roots?: unknown[] }).roots)
                    ? ((analysisResult.tree_architecture as { roots?: unknown[] }).roots?.length ?? 0)
                    : 0,
                })}
              </Tag>
            </div>

            <pre className="max-h-[420px] overflow-auto rounded bg-black/5 p-3 text-xs leading-5 text-foreground">
              {JSON.stringify(analysisResult.tree_architecture, null, 2)}
            </pre>
          </>
        )}
      </Modal>
    </div>
  );
};

export default DocumentReaderPage;