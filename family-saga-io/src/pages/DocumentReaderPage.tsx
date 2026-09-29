import { useEffect, useRef, useState } from "react";
import {
  ArrowLeftOutlined,
  CopyOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  FileImageOutlined,
  FileTextOutlined,
  HistoryOutlined,
  InboxOutlined,
  PictureOutlined,
  ReloadOutlined,
  SnippetsOutlined,
  SwapOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Empty,
  Modal,
  Select,
  Spin,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FamilyTreeVisualPanel } from "@/components/family-tree/FamilyTreeVisualPanel";
import type { BalkanNode } from "@/lib/familyTreeApi";
import { ServerSavedAlert } from "@/components/flow/ServerSavedAlert";
import { FlowNextBanner } from "@/components/flow/FlowNextBanner";
import { useAuth } from "@/contexts/AuthContext";
import { useGuestUploadQuota } from "@/hooks/useGuestUploadQuota";
import { toast } from "sonner";
import { getStoredAccessToken } from "@/lib/apiClient";
import {
  createUserDocument,
  createUserFamilyTree,
  getUserDocument,
  updateUserDocument,
} from "@/lib/userWorkspaceApi";
import { Textarea } from "@/components/ui/textarea";

type PreviewType = "image" | "pdf" | "docx" | "text" | "unsupported" | null;

type MammothModule = typeof import("mammoth/mammoth.browser");
type DetectedLanguageCode = "vi" | "en" | "unknown";
type DetectionMethod = "text-heuristic" | "filename-heuristic" | "unavailable";

type FamilyAnalyzeResponse = {
  request_id?: string | null;
  balkan_nodes: BalkanNode[];
  gemini_error: string | null;
  ocr_text?: string | null;
  hannom_text?: string | null;
  source_file_key?: string | null;
  pages_processed?: number;
  pages_truncated?: boolean;
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

const supportedFormats = [
  ".docx",
  ".txt",
  ".doc",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".pdf",
];
const backendBaseUrl = import.meta.env.VITE_BACKEND_URL ?? "";
/** Giá trị `lang_type` của Kim Hán Nôm: 0 tự động, 1 Hán, 2 Nôm. */
type HannomLangType = 0 | 1 | 2;
const DOCUMENT_ACCEPT = ".txt,text/plain,.docx,.pdf,application/pdf";
const IMAGE_ACCEPT = "image/png,image/jpeg,image/webp";
const viMarkRegex = /[\u00c0-\u1ef9\u0110\u0111]/g;
const viKeywords = [
  "gia",
  "pha",
  "phả",
  "dong",
  "dòng",
  "ho",
  "họ",
  "ong",
  "ông",
  "ba",
  "bà",
  "con",
  "chau",
  "cháu",
  "nam",
  "năm",
  "sinh",
  "mat",
  "mất",
];
const enKeywords = [
  "family",
  "tree",
  "lineage",
  "ancestor",
  "generation",
  "born",
  "died",
  "child",
  "children",
  "name",
  "year",
  "father",
  "mother",
];

const countKeywordHits = (text: string, keywords: string[]) => {
  const tokens = text
    .toLowerCase()
    .replace(/[^\p{L}\s]/gu, " ")
    .split(/\s+/)
    .filter(Boolean);

  return tokens.reduce(
    (sum, token) => sum + (keywords.includes(token) ? 1 : 0),
    0,
  );
};

const detectLanguageFromFilename = (name: string): LanguageDetection => {
  const lowerName = name.toLowerCase();

  if (/([._-]vi[._-])|vietnamese|tieng-viet|tiếng-việt/.test(lowerName)) {
    return { code: "vi", confidence: 0.62, method: "filename-heuristic" };
  }

  if (/([._-]en[._-])|english/.test(lowerName)) {
    return { code: "en", confidence: 0.62, method: "filename-heuristic" };
  }

  return { code: "unknown", confidence: 0.2, method: "unavailable" };
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
    return { code: "vi", confidence, method: "text-heuristic" };
  }

  if (enScore >= viScore + 2) {
    const confidence = Math.min(0.94, 0.55 + (enScore - viScore) * 0.05);
    return { code: "en", confidence, method: "text-heuristic" };
  }

  const fallback = detectLanguageFromFilename(fileName);
  if (fallback.code !== "unknown") {
    return fallback;
  }

  return { code: "unknown", confidence: 0.3, method: "text-heuristic" };
};

type DocumentReaderPageProps = {
  /** Nằm trong UserLayout — không render header/banner riêng */
  embedded?: boolean;
  initialScanId?: number | null;
  onScanRegistered?: (scanId: number) => void;
};

const DocumentReaderPage = ({
  embedded = false,
  initialScanId = null,
  onScanRegistered,
}: DocumentReaderPageProps) => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const guestQuota = useGuestUploadQuota();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const documentInputRef = useRef<HTMLInputElement | null>(null);
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const [langType, setLangType] = useState<HannomLangType>(0);
  /** Chỉ đổi vị trí hiển thị hai cột, không dịch ngược Quốc ngữ → Hán-Nôm. */
  const [columnsSwapped, setColumnsSwapped] = useState(false);
  /** Bật thì cột Hán-Nôm chuyển từ chỉ đọc (kết quả OCR) sang ô nhập tay —
   * chỉ ảnh hưởng hiển thị cục bộ, hannomText không được gửi lên backend
   * phân tích (handleAnalyzeFamilyTree chỉ dùng documentText). */
  const [isHannomEditable, setIsHannomEditable] = useState(false);
  const [hannomText, setHannomText] = useState("");
  const [showSourceImage, setShowSourceImage] = useState(false);
  /** Hán-Nôm gốc của 1 scan ĐÃ tồn tại (vd import corpus, hoặc lần phân tích
   * trước) — khác với analysisResult.hannom_text (chỉ có khi vừa OCR trong
   * phiên làm việc hiện tại). Nạp khi mở lại 1 scan qua initialScanId. */
  const [existingHannomText, setExistingHannomText] = useState<string | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [activeFile, setActiveFile] = useState<File | null>(null);
  const [previewType, setPreviewType] = useState<PreviewType>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [documentText, setDocumentText] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [languageDetection, setLanguageDetection] =
    useState<LanguageDetection | null>(null);
  const [analysisResult, setAnalysisResult] =
    useState<FamilyAnalyzeResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isResultModalOpen, setIsResultModalOpen] = useState(false);
  const [inputMode, setInputMode] = useState<"file" | "text">("file");
  const [manualInputText, setManualInputText] = useState("");
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selectedHistoryRequestId, setSelectedHistoryRequestId] = useState<
    string | null
  >(null);
  const [currentScanId, setCurrentScanId] = useState<number | null>(initialScanId);
  const [isSavingTree, setIsSavingTree] = useState(false);

  const registerScan = async (file: File, sourceText?: string) => {
    // Guest ẩn danh: không có tài khoản để gắn document vào — bỏ qua, không
    // gọi /api/user/documents (đúng nhánh isAuthenticated ở REQUIREMENTS.md §7.1/§B).
    if (!isAuthenticated) return;
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "unknown";
    const fileType = file.type || ext;
    try {
      const created = await createUserDocument({
        title: file.name,
        file_name: file.name,
        file_type: fileType,
        page_count: 1,
        source_text: sourceText,
      });
      setCurrentScanId(created.id);
      onScanRegistered?.(created.id);
      toast.success(
        t("flow.serverSaved", { defaultValue: "Đã lưu trên server" }),
      );
    } catch {
      setCurrentScanId(null);
    }
  };

  useEffect(() => {
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [imageUrl]);

  // Mở lại 1 scan đã có sẵn (vd tài liệu import corpus, hoặc đã phân tích
  // trước đó) — nạp text/hannom_text đã lưu để hiện đúng 2 cột thay vì màn
  // hình upload trống, dù chưa có file/ảnh nào được tải trong phiên này.
  useEffect(() => {
    if (!initialScanId) return;
    let cancelled = false;
    (async () => {
      try {
        const scan = await getUserDocument(initialScanId);
        if (cancelled) return;
        if (scan.source_text) {
          setDocumentText((prev) => prev || scan.source_text || "");
          setPreviewType((prev) => prev ?? "text");
        }
        if (scan.hannom_text) {
          setExistingHannomText(scan.hannom_text);
        }
      } catch {
        // Không chặn UI nếu fetch lỗi — vẫn dùng được như màn hình upload mới.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialScanId]);

  const fetchHistory = async () => {
    setIsHistoryLoading(true);
    setHistoryError(null);

    try {
      const response = await fetch(
        `${backendBaseUrl}/api/family-tree/history?limit=10`,
        {
          headers: {
            ...(getStoredAccessToken()
              ? { Authorization: `Bearer ${getStoredAccessToken()}` }
              : {}),
          },
        },
      );
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = (await response.json()) as HistoryResponse;
      setHistoryItems(payload.items ?? []);
      setHistoryTotal(payload.total ?? 0);
    } catch {
      setHistoryError(t("docReader.historyLoadFailed"));
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleClearHistory = async () => {
    setIsHistoryLoading(true);
    setHistoryError(null);

    try {
      const response = await fetch(
        `${backendBaseUrl}/api/family-tree/history`,
        {
          method: "DELETE",
          headers: {
            ...(getStoredAccessToken()
              ? { Authorization: `Bearer ${getStoredAccessToken()}` }
              : {}),
          },
        },
      );
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      setHistoryItems([]);
      setHistoryTotal(0);
      setSelectedHistoryRequestId(null);
      setStatusMessage(t("docReader.historyCleared"));
    } catch {
      setHistoryError(t("docReader.historyClearFailed"));
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleLoadHistoryDetail = async (requestId: string) => {
    setIsHistoryLoading(true);
    setHistoryError(null);
    setSelectedHistoryRequestId(requestId);

    try {
      const response = await fetch(
        `${backendBaseUrl}/api/family-tree/history/${requestId}`,
      );
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const raw = (await response.json()) as Partial<FamilyAnalyzeResponse>;
      const payload: FamilyAnalyzeResponse = {
        balkan_nodes: Array.isArray(raw.balkan_nodes) ? raw.balkan_nodes : [],
        gemini_error: raw.gemini_error ?? null,
      };
      setAnalysisResult(payload);
      setIsResultModalOpen(true);
      localStorage.setItem("family-tree.analysis", JSON.stringify(payload));
      setStatusMessage(
        t("docReader.historyLoaded", {
          requestId,
          count: payload.balkan_nodes.length,
        }),
      );
    } catch {
      setHistoryError(t("docReader.historyDetailLoadFailed"));
    } finally {
      setIsHistoryLoading(false);
    }
  };

  useEffect(() => {
    // Lịch sử /api/family-tree/history không lọc theo user ở nhánh fallback
    // khi gọi ẩn danh (rò rỉ lịch sử toàn hệ thống) — chỉ tải cho người đã
    // đăng nhập, Guest không thấy panel này (xem JSX bên dưới).
    if (isAuthenticated) {
      fetchHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  const resetPreview = () => {
    if (imageUrl) {
      URL.revokeObjectURL(imageUrl);
    }

    setActiveFile(null);
    setPreviewType(null);
    setImageUrl(null);
    setDocumentText("");
    setStatusMessage(null);
    setErrorMessage(null);
    setIsParsing(false);
    setLanguageDetection(null);
    setAnalysisResult(null);
    setAnalysisError(null);
    setIsAnalyzing(false);
    setIsResultModalOpen(false);
    setInputMode("file");
    setManualInputText("");
  };

  const applyManualText = async () => {
    const normalizedText = manualInputText.replace(/\n{3,}/g, "\n\n").trim();
    if (!normalizedText) {
      setErrorMessage(t("docReader.errNeedDocxToAnalyze"));
      return;
    }

    if (imageUrl) {
      URL.revokeObjectURL(imageUrl);
    }

    const syntheticFile = new File(
      [normalizedText],
      "manual-input.txt",
      {
        type: "text/plain",
      },
    );

    setActiveFile(syntheticFile);
    setPreviewType("text");
    setImageUrl(null);
    setDocumentText(normalizedText);
    setStatusMessage(t("docReader.msgTxtSuccess"));
    setErrorMessage(null);
    setLanguageDetection(detectLanguage(normalizedText, syntheticFile.name));
    setAnalysisResult(null);
    setAnalysisError(null);
    setIsAnalyzing(false);
    setIsResultModalOpen(false);
    await registerScan(syntheticFile, normalizedText);
  };

  const loadFile = async (file: File) => {
    if (imageUrl) {
      URL.revokeObjectURL(imageUrl);
    }

    setActiveFile(file);
    setErrorMessage(null);
    setStatusMessage(null);
    setDocumentText("");
    setImageUrl(null);
    setIsParsing(false);
    setLanguageDetection(null);
    setAnalysisResult(null);
    setAnalysisError(null);
    setIsAnalyzing(false);
    setIsResultModalOpen(false);

    const lowerName = file.name.toLowerCase();

    if (
      file.type.startsWith("image/") ||
      /\.(png|jpe?g|webp)$/i.test(lowerName)
    ) {
      setPreviewType("image");
      setImageUrl(URL.createObjectURL(file));
      setLanguageDetection(detectLanguageFromFilename(file.name));
      setStatusMessage(t("docReader.msgImageSuccess"));
      await registerScan(file);
      return;
    }

    if (file.type === "application/pdf" || /\.pdf$/i.test(lowerName)) {
      setPreviewType("pdf");
      setLanguageDetection(detectLanguageFromFilename(file.name));
      setStatusMessage(t("docReader.msgPdfSuccess"));
      await registerScan(file);
      return;
    }

    if (/\.txt$/i.test(lowerName)) {
      setPreviewType("text");
      setIsParsing(true);

      try {
        const rawText = await file.text();
        const normalizedText = rawText.replace(/\n{3,}/g, "\n\n").trim();
        setDocumentText(normalizedText || t("docReader.msgEmptyDocx"));
        setLanguageDetection(detectLanguage(normalizedText, file.name));
        setStatusMessage(t("docReader.msgTxtSuccess"));
        await registerScan(file, normalizedText);
      } catch (error) {
        setErrorMessage(t("docReader.errTxtRead"));
      } finally {
        setIsParsing(false);
      }

      return;
    }

    if (/\.docx$/i.test(lowerName)) {
      setPreviewType("docx");
      setIsParsing(true);

      try {
        const mammothModule: MammothModule =
          await import("mammoth/mammoth.browser");
        const arrayBuffer = await file.arrayBuffer();
        const result = await mammothModule.extractRawText({ arrayBuffer });
        const normalizedText = result.value.replace(/\n{3,}/g, "\n\n").trim();

        setDocumentText(normalizedText || t("docReader.msgEmptyDocx"));
        setLanguageDetection(detectLanguage(normalizedText, file.name));
        setStatusMessage(t("docReader.msgDocxSuccess"));
        await registerScan(file, normalizedText);
      } catch (error) {
        setErrorMessage(t("docReader.errDocxParse"));
      } finally {
        setIsParsing(false);
      }

      return;
    }

    if (/\.doc$/i.test(lowerName)) {
      setPreviewType("unsupported");
      setLanguageDetection(detectLanguageFromFilename(file.name));
      setErrorMessage(t("docReader.errDocOld"));
      return;
    }

    setPreviewType("unsupported");
    setLanguageDetection(detectLanguageFromFilename(file.name));
    setErrorMessage(t("docReader.errUnsupported"));
  };

  const handleCopyQuocNgu = async () => {
    try {
      await navigator.clipboard.writeText(documentText);
      toast.success(t("docReader.copySuccess"));
    } catch {
      toast.error(t("docReader.copyFailed"));
    }
  };

  /** Dán vào ô đang chỉnh sửa — Hán-Nôm nếu đang bật "Gõ Hán-Nôm", ngược lại
   * Quốc Ngữ (ô còn lại luôn có thể chỉnh sửa). */
  const handlePasteActiveColumn = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (isHannomEditable) {
        setHannomText((prev) => prev + text);
      } else {
        setDocumentText((prev) => prev + text);
      }
    } catch {
      toast.error(t("docReader.pasteFailed"));
    }
  };

  const handleToggleHannomEditable = (nextValue: boolean) => {
    if (nextValue && !hannomText) {
      setHannomText(analysisResult?.hannom_text ?? existingHannomText ?? "");
    }
    setIsHannomEditable(nextValue);
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
    const isTextLike = previewType === "docx" || previewType === "text";
    const isImageLike = previewType === "image" || previewType === "pdf";

    if (isTextLike && !documentText.trim()) {
      setAnalysisError(t("docReader.errNeedDocxToAnalyze"));
      return;
    }
    if (isImageLike && !activeFile) {
      setAnalysisError(t("docReader.errNeedDocxToAnalyze"));
      return;
    }
    if (!isTextLike && !isImageLike) {
      setAnalysisError(t("docReader.errNeedDocxToAnalyze"));
      return;
    }

    if (!isAuthenticated && guestQuota.exhausted) {
      setAnalysisError(t("docReader.quotaExceeded"));
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);

    // Sau lần OCR đầu, phân tích lại dùng văn bản Quốc ngữ (có thể đã sửa) thay vì OCR lại.
    const hasOcrText = isImageLike && analysisResult?.ocr_text != null;
    const shouldOcr = isImageLike && !hasOcrText;
    if (hasOcrText && !documentText.trim()) {
      setAnalysisError(t("docReader.errNeedDocxToAnalyze"));
      return;
    }

    try {
      const token = getStoredAccessToken();
      let response: Response;

      if (shouldOcr && activeFile) {
        // Ảnh/PDF: gửi multipart, backend tự OCR (Kim Hán Nôm), lưu ảnh gốc
        // vào MinIO (best-effort) rồi phân tích — xem POST
        // /api/family-tree/analyze-image trong nlp_family_extractor/api.py.
        const formData = new FormData();
        formData.append("file", activeFile);
        const query = new URLSearchParams({ lang_type: String(langType) });
        if (currentScanId != null) {
          query.set("scan_id", String(currentScanId));
        }
        response = await fetch(
          `${backendBaseUrl}/api/family-tree/analyze-image?${query.toString()}`,
          {
            method: "POST",
            headers: {
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: formData,
          },
        );
      } else {
        response = await fetch(
          `${backendBaseUrl}/api/family-tree/analyze`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({
              text: documentText,
              source: "document-reader",
              metadata: {
                fileName: activeFile?.name,
                language: languageDetection?.code ?? "unknown",
              },
            }),
          },
        );
      }

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        throw new Error(
          (errorBody && typeof errorBody.detail === "string" && errorBody.detail) ||
            `HTTP ${response.status}`,
        );
      }

      const raw = (await response.json()) as Partial<FamilyAnalyzeResponse>;
      const payload: FamilyAnalyzeResponse = {
        request_id: raw.request_id ?? null,
        balkan_nodes: Array.isArray(raw.balkan_nodes) ? raw.balkan_nodes : [],
        gemini_error: raw.gemini_error ?? null,
        ocr_text: raw.ocr_text ?? analysisResult?.ocr_text ?? null,
        hannom_text: raw.hannom_text ?? analysisResult?.hannom_text ?? null,
        source_file_key: raw.source_file_key ?? analysisResult?.source_file_key ?? null,
        pages_processed: raw.pages_processed ?? analysisResult?.pages_processed,
        pages_truncated: raw.pages_truncated ?? analysisResult?.pages_truncated,
      };
      setAnalysisResult(payload);
      if (shouldOcr && payload.ocr_text) {
        setDocumentText(payload.ocr_text);
      }
      setIsResultModalOpen(true);
      localStorage.setItem("family-tree.analysis", JSON.stringify(payload));
      if (!isAuthenticated) {
        guestQuota.consume();
      }
      if (currentScanId) {
        await updateUserDocument(currentScanId, {
          request_id: payload.request_id ?? undefined,
          tree_status: "draft",
          ocr_status: isImageLike ? "completed" : "skipped",
          source_text: shouldOcr ? payload.ocr_text ?? undefined : documentText,
          source_file_key: shouldOcr ? payload.source_file_key ?? undefined : undefined,
        });
      }
      fetchHistory();
      setStatusMessage(
        payload.pages_truncated
          ? t("docReader.msgAnalyzePagesTruncated", {
              count: payload.balkan_nodes.length,
              pages: payload.pages_processed,
              defaultValue:
                "Phân tích xong {{count}} người (chỉ OCR {{pages}} trang đầu — tài liệu dài hơn nên dùng trang Admin).",
            })
          : t("docReader.msgAnalyzeSuccess", {
              count: payload.balkan_nodes.length,
            }),
      );
      setIsResultModalOpen(true);
    } catch (error) {
      setAnalysisError(
        error instanceof Error && error.message
          ? error.message
          : t("docReader.errBackendUnavailable"),
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const mainContent = (
    <div className={embedded ? "space-y-6" : "px-4 md:px-6 py-8"}>
      {embedded && (
        <section className="brand-gradient px-4 md:px-6 py-5 rounded-2xl">
          <div className="mx-auto flex flex-wrap items-center justify-between gap-4 text-primary-foreground">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-primary-foreground/80">
                {t("docReader.bannerLabel")}
              </p>
              <h2 className="text-3xl font-display font-bold mt-2">
                {t("docReader.bannerTitle")}
              </h2>
            </div>
            <div className="max-w-xl text-sm text-primary-foreground/90 leading-6">
              {t("docReader.bannerDesc")}
            </div>
          </div>
        </section>
      )}
      {embedded && currentScanId != null && (
        <ServerSavedAlert />
      )}
      <div className={`mx-auto grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)] xl:grid-cols-[380px_minmax(0,1fr)] ${embedded ? "max-w-full" : "max-w-7xl"}`}>
          <div className="space-y-6">
            <Card
              bordered={false}
              className={`transition-shadow ${isDragging ? "bg-muted shadow-lg ring-2 ring-primary/40" : "bg-card shadow-md"}`}
              styles={{ body: { padding: 24 } }}
            >
              <div
                className={`rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
                  isDragging
                    ? "border-primary bg-muted"
                    : "border-border bg-background"
                }`}
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
                <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-full brand-gradient text-primary-foreground">
                  <InboxOutlined className="text-[34px]" />
                </div>

                <Typography.Title level={4} className="!mb-2 font-display text-foreground">
                  {t("docReader.dropTitle")}
                </Typography.Title>
                <Typography.Paragraph className="!mb-5 text-muted-foreground">
                  {t("docReader.dropDesc")}
                </Typography.Paragraph>

                <div className="flex flex-wrap justify-center gap-2 mb-6">
                  {supportedFormats.map((format) => (
                    <Tag key={format} className="px-2.5 py-1">
                      {format}
                    </Tag>
                  ))}
                </div>

                <div className="flex justify-center gap-3 flex-wrap">
                  <Button
                    type="primary"
                    size="large"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {t("docReader.btnChooseFile")}
                  </Button>
                  <Button
                    icon={<ReloadOutlined />}
                    size="large"
                    onClick={resetPreview}
                  >
                    {t("docReader.btnReset")}
                  </Button>
                  <Button
                    size="large"
                    loading={isAnalyzing}
                    disabled={
                      (!isAuthenticated && guestQuota.exhausted) ||
                      (previewType === "image" || previewType === "pdf"
                        ? !activeFile
                        : (previewType !== "docx" && previewType !== "text") ||
                          !documentText.trim())
                    }
                    onClick={handleAnalyzeFamilyTree}
                  >
                    {t("docReader.btnAnalyzeTree")}
                  </Button>
                  {analysisResult && (
                    <Button
                      size="large"
                      onClick={() => setIsResultModalOpen(true)}
                    >
                      {t("docReader.btnOpenAnalysisPopup")}
                    </Button>
                  )}
                </div>

                {!isAuthenticated && (
                  <div className="mt-4 flex justify-center">
                    {guestQuota.exhausted ? (
                      <Alert
                        showIcon
                        type="warning"
                        message={t("docReader.quotaExceeded")}
                        action={
                          <Button
                            size="small"
                            type="primary"
                            onClick={() =>
                              navigate("/login", {
                                state: { from: "/user/documents/new" },
                              })
                            }
                          >
                            {t("auth.loginBtn", { defaultValue: "Đăng nhập" })}
                          </Button>
                        }
                      />
                    ) : (
                      <Tag color="processing">
                        {t("docReader.quotaRemaining", {
                          count: guestQuota.remaining,
                        })}
                      </Tag>
                    )}
                  </div>
                )}

                <div className="mt-6 rounded-2xl border border-border bg-background/80 p-4 text-left">
                  <Tabs
                    activeKey={inputMode}
                    onChange={(key) => setInputMode(key as "file" | "text")}
                    className="[&_.ant-tabs-nav]:mb-4"
                    items={[
                      {
                        key: "file",
                        label: t("docReader.inputModeFile", {
                          defaultValue: "Upload file",
                        }),
                        children: (
                          <Typography.Paragraph className="!mb-0 text-sm text-muted-foreground">
                            {t("docReader.directInputFallback", {
                              defaultValue:
                                "Chuyển sang tab Nhập text để dán nội dung trực tiếp.",
                            })}
                          </Typography.Paragraph>
                        ),
                      },
                      {
                        key: "text",
                        label: t("docReader.inputModeText", {
                          defaultValue: "Nhập text",
                        }),
                        children: (
                          <div className="space-y-3">
                            <div>
                              <Typography.Title
                                level={5}
                                className="!mb-1 font-display text-foreground"
                              >
                                {t("docReader.directInputTitle", {
                                  defaultValue: "Nhập text trực tiếp",
                                })}
                              </Typography.Title>
                              <Typography.Text type="secondary">
                                {t("docReader.directInputDesc", {
                                  defaultValue:
                                    "Dán nội dung vào đây rồi phân tích ngay, không cần upload file.",
                                })}
                              </Typography.Text>
                            </div>
                            <Textarea
                              value={manualInputText}
                              onChange={(event) =>
                                setManualInputText(event.target.value)
                              }
                              placeholder={t(
                                "docReader.directInputPlaceholder",
                                {
                                  defaultValue:
                                    "Dán hoặc gõ nội dung gia phả vào đây...",
                                },
                              )}
                              className="min-h-[240px] w-full resize-y text-sm leading-6"
                            />
                            <div className="flex flex-wrap gap-2">
                              <Button
                                type="primary"
                                onClick={applyManualText}
                                disabled={!manualInputText.trim()}
                              >
                                {t("docReader.btnUseDirectText", {
                                  defaultValue: "Dùng text này",
                                })}
                              </Button>
                              <Button
                                onClick={() => setManualInputText("")}
                                disabled={!manualInputText}
                              >
                                {t("docReader.btnClearDirectText", {
                                  defaultValue: "Xóa text",
                                })}
                              </Button>
                            </div>
                          </div>
                        ),
                      },
                    ]}
                  />
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,text/plain,.doc,.docx,image/png,image/jpeg,image/webp,.pdf,application/pdf"
                  className="hidden"
                  onChange={async (event) => {
                    if (event.target.files) {
                      await handleSelectedFiles(event.target.files);
                      event.target.value = "";
                    }
                  }}
                />
              </div>
            </Card>

            <Card bordered={false} className="bg-muted">
              <Typography.Title level={4} className="!mb-4 font-display text-foreground">
                {t("docReader.workflowTitle")}
              </Typography.Title>
              <div className="space-y-3 text-sm text-muted-foreground leading-6">
                <p>{t("docReader.step1")}</p>
                <p>{t("docReader.step2")}</p>
                <p>{t("docReader.step3")}</p>
              </div>
            </Card>

            {/* Lịch sử /api/family-tree/history không lọc theo user ở nhánh
                fallback ẩn danh (rò rỉ toàn hệ thống) — chỉ hiện cho người
                đã đăng nhập, đúng REQUIREMENTS.md §7.1/§B. */}
            {isAuthenticated && (
            <Card bordered={false} className="bg-muted">
              <div className="flex items-center justify-between gap-2 mb-3">
                <Typography.Title level={5} className="!m-0 font-display text-foreground">
                  <HistoryOutlined className="mr-2" />
                  {t("docReader.historyTitle")}
                </Typography.Title>
                <div className="flex items-center gap-2">
                  <Button
                    size="small"
                    icon={<SyncOutlined />}
                    loading={isHistoryLoading}
                    onClick={fetchHistory}
                  >
                    {t("docReader.historyRefresh")}
                  </Button>
                  <Button
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    loading={isHistoryLoading}
                    onClick={handleClearHistory}
                  >
                    {t("docReader.historyClear")}
                  </Button>
                </div>
              </div>

              <p className="text-xs text-muted-foreground mb-3">
                {t("docReader.historyTotal", { count: historyTotal })}
              </p>

              {historyError && (
                <Alert
                  showIcon
                  type="error"
                  message={t("docReader.analysisFailedTitle")}
                  description={historyError}
                  className="mb-3"
                />
              )}

              {historyItems.length === 0 ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={t("docReader.historyEmpty")}
                />
              ) : (
                <div className="space-y-2 max-h-56 overflow-auto pr-1">
                  {historyItems.map((item) => (
                    <div
                      key={item.request_id}
                      className={`rounded-lg border px-3 py-2 bg-background/70 ${selectedHistoryRequestId === item.request_id ? "ring-2 ring-gold" : ""}`}
                    >
                      <div className="text-xs text-muted-foreground">
                        {new Date(item.created_at).toLocaleString()}
                      </div>
                      <div className="text-sm font-medium mt-1 break-all">
                        {item.request_id}
                      </div>
                      <div className="mt-1 flex flex-wrap gap-2">
                        <Tag>
                          {t("docReader.analysisPeople", {
                            count: item.people_count,
                          })}
                        </Tag>
                        <Tag>
                          {t("docReader.analysisRelationships", {
                            count: item.relationship_count,
                          })}
                        </Tag>
                        {item.warning_count > 0 && (
                          <Tag color="warning">
                            {t("docReader.historyWarnings", {
                              count: item.warning_count,
                            })}
                          </Tag>
                        )}
                      </div>
                      <div className="mt-2">
                        <Button
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={() =>
                            handleLoadHistoryDetail(item.request_id)
                          }
                          loading={
                            isHistoryLoading &&
                            selectedHistoryRequestId === item.request_id
                          }
                        >
                          {t("docReader.historyViewDetail")}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
            )}
          </div>

          <Card
            bordered={false}
            className="bg-card min-h-[640px]"
            styles={{ body: { padding: 24, height: "100%" } }}
          >
            <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
              <div>
                <Typography.Title level={3} className="!mb-1 font-display text-foreground">
                  {t("docReader.previewAreaTitle")}
                </Typography.Title>
                <Typography.Text type="secondary">
                  {t("docReader.previewAreaSubtitle")}
                </Typography.Text>
              </div>

              {activeFile && (
                <Tag color="processing" className="px-2.5 py-1.5">
                  {activeFile.name}
                </Tag>
              )}
            </div>

            {statusMessage && (
              <Alert
                showIcon
                type="success"
                message={t("docReader.successTitle")}
                description={
                  <div>
                    <div>{statusMessage}</div>
                    {languageDetection && (
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <Tag color="processing">
                          {t("docReader.detectedLanguage", {
                            lang: t(`docReader.lang.${languageDetection.code}`),
                          })}
                        </Tag>
                        <Tag>
                          {t("docReader.detectedBy", {
                            method: t(
                              `docReader.method.${languageDetection.method}`,
                            ),
                          })}
                        </Tag>
                      </div>
                    )}
                  </div>
                }
                className="mb-4"
              />
            )}

            {errorMessage && (
              <Alert
                showIcon
                type="warning"
                message={t("docReader.warningTitle")}
                description={errorMessage}
                className="mb-4"
              />
            )}

            {analysisError && (
              <Alert
                showIcon
                type="error"
                message={t("docReader.analysisFailedTitle")}
                description={analysisError}
                className="mb-4"
              />
            )}

            {analysisResult && !isAuthenticated && (
              <FlowNextBanner
                message={t("docReader.guestAnalyzeDoneBanner")}
                nextLabel={t("auth.loginBtn", { defaultValue: "Đăng nhập" })}
                nextHref="/login"
              />
            )}

            {analysisResult && (
              <Card
                bordered={false}
                className="mb-4 bg-muted"
                title={t("docReader.analysisInlineTitle")}
              >
                <div className="flex flex-wrap gap-2 mb-3">
                  <Tag color="processing">
                    {t("docReader.analysisPeople", {
                      count: analysisResult.balkan_nodes.length,
                    })}
                  </Tag>
                </div>

                {analysisResult.gemini_error && (
                  <Alert
                    type="warning"
                    showIcon
                    message={t("docReader.geminiErrorTitle")}
                    description={analysisResult.gemini_error}
                    className="mb-3"
                  />
                )}

                <div className="flex flex-wrap gap-2 mb-3">
                  <Button onClick={() => setIsResultModalOpen(true)}>
                    {t("docReader.btnOpenAnalysisPopup")}
                  </Button>
                  {isAuthenticated ? (
                    <Button
                      type="primary"
                      onClick={() => navigate("/user/family-trees")}
                    >
                      {t("docReader.btnOpenTreePage")}
                    </Button>
                  ) : (
                    <Button
                      type="primary"
                      onClick={() =>
                        navigate("/login", {
                          state: { from: "/user/documents/new" },
                        })
                      }
                    >
                      {t("docReader.guestLoginToSave")}
                    </Button>
                  )}
                </div>

                <Card
                  size="small"
                  className="mt-4 bg-muted"
                  title={t("docReader.inlineTreeTitle")}
                >
                  {analysisResult.balkan_nodes.length > 0 ? (
                    <FamilyTreeVisualPanel
                      nodes={analysisResult.balkan_nodes}
                      treeName={t("docReader.inlineTreeTitle", { defaultValue: "Sơ đồ từ phân tích" })}
                    />
                  ) : (
                    <Empty description={t("docReader.inlineTreeEmpty")} />
                  )}
                </Card>
              </Card>
            )}

            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Tooltip title={t("docReader.docTypeHint")}>
                <Select
                  value="auto"
                  disabled
                  aria-label={t("docReader.docTypeLabel")}
                  className="min-w-[140px]"
                  options={[
                    { value: "auto", label: `${t("docReader.docTypeLabel")}: ${t("docReader.docTypeAuto")}` },
                  ]}
                />
              </Tooltip>
              <Select<HannomLangType>
                value={langType}
                onChange={setLangType}
                aria-label={t("docReader.langTypeLabel")}
                className="min-w-[140px]"
                options={[
                  { value: 0, label: `${t("docReader.langTypeLabel")}: ${t("docReader.langTypeAuto")}` },
                  { value: 1, label: `${t("docReader.langTypeLabel")}: ${t("docReader.langTypeHan")}` },
                  { value: 2, label: `${t("docReader.langTypeLabel")}: ${t("docReader.langTypeNom")}` },
                ]}
              />
            </div>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <Button icon={<ReloadOutlined />} onClick={resetPreview}>
                {t("docReader.btnReset")}
              </Button>
              <Button
                icon={<FileTextOutlined />}
                onClick={() => documentInputRef.current?.click()}
              >
                {t("docReader.btnPickDocument")}
              </Button>
              <Button
                icon={<PictureOutlined />}
                onClick={() => imageInputRef.current?.click()}
              >
                {t("docReader.btnPickImage")}
              </Button>
              {[
                { ref: documentInputRef, accept: DOCUMENT_ACCEPT },
                { ref: imageInputRef, accept: IMAGE_ACCEPT },
              ].map(({ ref, accept }) => (
                <input
                  key={accept}
                  ref={ref}
                  type="file"
                  accept={accept}
                  className="hidden"
                  onChange={async (event) => {
                    const file = event.target.files?.[0];
                    event.target.value = "";
                    if (file) {
                      await loadFile(file);
                    }
                  }}
                />
              ))}
            </div>

            {isParsing ? (
              <div className="h-[520px] flex items-center justify-center rounded-2xl bg-muted">
                <div className="text-center">
                  <Spin size="large" />
                  <Typography.Paragraph className="!mt-4 !mb-0 text-muted-foreground">
                    {t("docReader.parsing")}
                  </Typography.Paragraph>
                </div>
              </div>
            ) : !activeFile ? (
              <div className="h-[520px] flex items-center justify-center rounded-2xl border border-dashed border-border bg-background">
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={t("docReader.noDocument")}
                />
              </div>
            ) : (
              <Tabs
                defaultActiveKey="preview"
                items={[
                  {
                    key: "preview",
                    label: (
                      <span>
                        <EyeOutlined /> {t("docReader.tabPreview")}
                      </span>
                    ),
                    children:
                      previewType === "unsupported" || previewType === null ? (
                        <div className="h-[520px] flex items-center justify-center rounded-2xl border border-border bg-muted">
                          <Empty description={t("docReader.noPreview")} />
                        </div>
                      ) : (
                        (() => {
                          const isImageLike =
                            previewType === "image" || previewType === "pdf";
                          const ocrDone =
                            isImageLike && analysisResult?.ocr_text != null;

                          const hannomBody = isHannomEditable ? (
                            <Textarea
                              value={hannomText}
                              onChange={(event) => setHannomText(event.target.value)}
                              placeholder={t("docReader.hannomEditPlaceholder")}
                              className="h-full w-full resize-none rounded-none border-0 bg-muted px-5 py-4 text-2xl leading-[2.4rem] focus-visible:ring-0 focus-visible:ring-offset-0"
                            />
                          ) : ocrDone ? (
                            analysisResult?.hannom_text ? (
                              <div className="h-full overflow-auto bg-muted px-5 py-4 whitespace-pre-wrap text-2xl leading-[2.4rem] text-foreground">
                                {analysisResult.hannom_text}
                              </div>
                            ) : (
                              <div className="h-full flex items-center justify-center bg-muted px-6 text-center text-sm text-muted-foreground">
                                {t("docReader.hannomEmptyAfterOcr")}
                              </div>
                            )
                          ) : existingHannomText ? (
                            <div className="h-full overflow-auto bg-muted px-5 py-4 whitespace-pre-wrap text-2xl leading-[2.4rem] text-foreground">
                              {existingHannomText}
                            </div>
                          ) : previewType === "image" && imageUrl ? (
                            <div className="h-full overflow-auto bg-muted p-4">
                              <img
                                src={imageUrl}
                                alt={activeFile.name}
                                className="mx-auto max-w-full rounded-xl shadow-lg"
                              />
                            </div>
                          ) : previewType === "pdf" ? (
                            <div className="h-full flex flex-col items-center justify-center gap-3 bg-muted text-center px-6">
                              <FileTextOutlined style={{ fontSize: 48 }} className="!text-primary" />
                              <p className="font-medium mb-0">{activeFile.name}</p>
                              <p className="text-sm text-muted-foreground mb-0">
                                {t("docReader.pdfPreviewHint")}
                              </p>
                            </div>
                          ) : (
                            <div className="h-full overflow-auto bg-muted px-5 py-4">
                              <Alert
                                type="info"
                                showIcon
                                message={t("docReader.noHannomSource")}
                                className="mb-3"
                              />
                              <article className="whitespace-pre-wrap text-[15px] leading-8 text-foreground">
                                {documentText}
                              </article>
                            </div>
                          );

                          const showSourceImagePreview =
                            showSourceImage && previewType === "image" && !!imageUrl;

                          const hannomColumn = (
                            <div className="flex min-w-0 flex-col overflow-hidden rounded-2xl border border-border">
                              <div className="border-b border-border bg-background px-4 py-2 text-center text-sm font-semibold tracking-widest text-foreground">
                                {t("docReader.columnHannom")}
                              </div>
                              <div className="flex h-[560px] flex-col">
                                {showSourceImagePreview && (
                                  <div className="h-[180px] shrink-0 overflow-auto border-b border-border bg-muted p-2">
                                    <img
                                      src={imageUrl}
                                      alt={activeFile.name}
                                      className="mx-auto max-h-full rounded-lg shadow"
                                    />
                                  </div>
                                )}
                                <div className="min-h-0 flex-1">{hannomBody}</div>
                              </div>
                            </div>
                          );

                          const quocNguColumn = (
                            <div className="flex min-w-0 flex-col overflow-hidden rounded-2xl border border-border">
                              <div className="border-b border-border bg-background px-4 py-2 text-center text-sm font-semibold tracking-widest text-foreground">
                                {t("docReader.columnQuocNgu")}
                              </div>
                              <Textarea
                                value={documentText}
                                onChange={(event) =>
                                  setDocumentText(event.target.value)
                                }
                                disabled={isImageLike && !ocrDone}
                                placeholder={
                                  isImageLike && !ocrDone
                                    ? t("docReader.quocNguAwaitOcr")
                                    : t("docReader.quocNguPlaceholder")
                                }
                                className="h-[560px] w-full resize-none rounded-none border-0 bg-muted px-5 py-4 text-[15px] leading-8 focus-visible:ring-0 focus-visible:ring-offset-0"
                              />
                            </div>
                          );

                          return (
                            <div>
                              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] md:items-start">
                                {columnsSwapped ? quocNguColumn : hannomColumn}
                                <div className="flex justify-center md:pt-1">
                                  <Tooltip title={t("docReader.btnSwapColumns")}>
                                    <Button
                                      shape="circle"
                                      icon={<SwapOutlined />}
                                      aria-label={t("docReader.btnSwapColumns")}
                                      onClick={() =>
                                        setColumnsSwapped((value) => !value)
                                      }
                                    />
                                  </Tooltip>
                                </div>
                                {columnsSwapped ? hannomColumn : quocNguColumn}
                              </div>
                              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                                <div className="flex flex-wrap items-center gap-4">
                                  <Checkbox
                                    checked={isHannomEditable}
                                    onChange={(event) =>
                                      handleToggleHannomEditable(event.target.checked)
                                    }
                                  >
                                    {t("docReader.chkTypeHannom")}
                                  </Checkbox>
                                  <Checkbox
                                    checked={showSourceImage}
                                    onChange={(event) => setShowSourceImage(event.target.checked)}
                                  >
                                    {t("docReader.chkShowImageResult")}
                                  </Checkbox>
                                </div>
                                <div className="flex items-center gap-1">
                                  <Typography.Text type="secondary" className="text-sm mr-2">
                                    {t("docReader.charCount", {
                                      count: documentText.length,
                                    })}
                                  </Typography.Text>
                                  <Tooltip title={t("docReader.btnPaste")}>
                                    <Button
                                      type="text"
                                      icon={<SnippetsOutlined />}
                                      aria-label={t("docReader.btnPaste")}
                                      onClick={handlePasteActiveColumn}
                                    />
                                  </Tooltip>
                                  <Tooltip title={t("docReader.btnEditHannom")}>
                                    <Button
                                      type="text"
                                      icon={<EditOutlined />}
                                      aria-label={t("docReader.btnEditHannom")}
                                      disabled={!ocrDone && !existingHannomText && !isHannomEditable}
                                      onClick={() =>
                                        handleToggleHannomEditable(!isHannomEditable)
                                      }
                                    />
                                  </Tooltip>
                                  <Tooltip title={t("docReader.btnCopy")}>
                                    <Button
                                      type="text"
                                      icon={<CopyOutlined />}
                                      aria-label={t("docReader.btnCopy")}
                                      disabled={!documentText}
                                      onClick={handleCopyQuocNgu}
                                    />
                                  </Tooltip>
                                </div>
                              </div>
                            </div>
                          );
                        })()
                      ),
                  },
                  {
                    key: "info",
                    label: (
                      <span>
                        <FileTextOutlined /> {t("docReader.tabInfo")}
                      </span>
                    ),
                    children: activeFile ? (
                      <Card
                        bordered={false}
                        className="bg-muted"
                      >
                        <Descriptions column={1} bordered size="middle">
                          <Descriptions.Item
                            label={t("docReader.fileInfoName")}
                          >
                            {activeFile.name}
                          </Descriptions.Item>
                          <Descriptions.Item
                            label={t("docReader.fileInfoType")}
                          >
                            {activeFile.type || t("docReader.unknownType")}
                          </Descriptions.Item>
                          <Descriptions.Item
                            label={t("docReader.fileInfoSize")}
                          >
                            {(activeFile.size / 1024 / 1024).toFixed(2)} MB
                          </Descriptions.Item>
                          <Descriptions.Item
                            label={t("docReader.fileInfoMode")}
                          >
                            {previewType === "image"
                              ? t("docReader.modeImage")
                              : previewType === "pdf"
                                ? t("docReader.modePdf")
                                : previewType === "docx"
                                  ? t("docReader.modeDocx")
                                  : previewType === "text"
                                    ? t("docReader.modeText")
                                    : t("docReader.modeUnsupported")}
                          </Descriptions.Item>
                          <Descriptions.Item
                            label={t("docReader.fileInfoLanguage")}
                          >
                            {languageDetection
                              ? t(`docReader.lang.${languageDetection.code}`)
                              : t("docReader.lang.unknown")}
                          </Descriptions.Item>
                          <Descriptions.Item
                            label={t("docReader.fileInfoDetectionMethod")}
                          >
                            {languageDetection
                              ? t(
                                  `docReader.method.${languageDetection.method}`,
                                )
                              : t("docReader.method.unavailable")}
                          </Descriptions.Item>
                          <Descriptions.Item
                            label={t("docReader.fileInfoDetectionConfidence")}
                          >
                            {languageDetection
                              ? `${Math.round(languageDetection.confidence * 100)}%`
                              : "-"}
                          </Descriptions.Item>
                        </Descriptions>

                        <div className="grid gap-4 md:grid-cols-2 mt-6">
                          <Card
                            size="small"
                            className="bg-muted"
                          >
                            <div className="flex items-center gap-3 mb-2">
                              <FileImageOutlined
                                className="!text-primary"
                              />
                              <span className="font-medium">
                                {t("docReader.cardImageTitle")}
                              </span>
                            </div>
                            <p className="mb-0 text-sm text-muted-foreground leading-6">
                              {t("docReader.cardImageDesc")}
                            </p>
                          </Card>

                          <Card
                            size="small"
                            className="bg-muted"
                          >
                            <div className="flex items-center gap-3 mb-2">
                              <FileTextOutlined className="!text-primary" />
                              <span className="font-medium">
                                {t("docReader.cardDocxTitle")}
                              </span>
                            </div>
                            <p className="mb-0 text-sm text-muted-foreground leading-6">
                              {t("docReader.cardDocxDesc")}
                            </p>
                          </Card>
                        </div>

                        {analysisResult && (
                          <Card
                            size="small"
                            className="mt-6 bg-muted"
                            title={t("docReader.analysisTitle")}
                          >
                            <div className="flex flex-wrap gap-2 mb-3">
                              <Tag color="processing">
                                {t("docReader.analysisPeople", {
                                  count: analysisResult.balkan_nodes.length,
                                })}
                              </Tag>
                            </div>
                            {analysisResult.gemini_error && (
                              <Alert
                                type="warning"
                                showIcon
                                className="mb-3"
                                message={t("docReader.geminiErrorTitle")}
                                description={analysisResult.gemini_error}
                              />
                            )}
                            <pre className="max-h-64 overflow-auto rounded bg-muted p-3 text-xs leading-5 text-foreground">
                              {JSON.stringify(
                                analysisResult.balkan_nodes,
                                null,
                                2,
                              )}
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

      <Modal
        open={isResultModalOpen}
        onCancel={() => setIsResultModalOpen(false)}
        footer={
          isAuthenticated
            ? [
                <Button key="close" onClick={() => setIsResultModalOpen(false)}>
                  {t("familyTree.close")}
                </Button>,
                <Button
                  key="save-tree"
                  type="primary"
                  loading={isSavingTree}
                  disabled={!analysisResult?.balkan_nodes?.length}
                  onClick={async () => {
                    if (!analysisResult?.balkan_nodes?.length) return;
                    setIsSavingTree(true);
                    try {
                      const treeName =
                        activeFile?.name.replace(/\.[^.]+$/, "") ??
                        t("docReader.defaultTreeName", { defaultValue: "Gia phả mới" });
                      const created = await createUserFamilyTree({
                        name: treeName,
                        description: t("docReader.savedFromScan", { defaultValue: "Tạo từ phòng đọc tài liệu" }),
                        nodes: analysisResult.balkan_nodes,
                        source_scan_id: currentScanId ?? undefined,
                      });
                      if (currentScanId) {
                        await updateUserDocument(currentScanId, {
                          tree_status: "created",
                          family_tree_id: created.id,
                        });
                      }
                      setIsResultModalOpen(false);
                      navigate(`/user/family-trees/${created.id}?tab=visual`);
                    } catch (error) {
                      setAnalysisError(error instanceof Error ? error.message : "Không lưu được cây gia phả");
                    } finally {
                      setIsSavingTree(false);
                    }
                  }}
                >
                  {t("docReader.btnSaveTree", { defaultValue: "Lưu cây gia phả" })}
                </Button>,
                <Button
                  key="open-tree"
                  onClick={() => navigate("/user/family-trees")}
                >
                  {t("docReader.btnOpenTreePage")}
                </Button>,
              ]
            : [
                <Button key="close" onClick={() => setIsResultModalOpen(false)}>
                  {t("familyTree.close")}
                </Button>,
                <Button
                  key="login-to-save"
                  type="primary"
                  onClick={() =>
                    navigate("/login", { state: { from: "/user/documents/new" } })
                  }
                >
                  {t("docReader.guestLoginToSave")}
                </Button>,
              ]
        }
        title={t("docReader.analysisPopupTitle")}
        width={1040}
      >
        {analysisResult && (
          <Tabs
            defaultActiveKey="analysis"
            items={[
              {
                key: "analysis",
                label: t("docReader.analysisTabLabel", {
                  defaultValue: "Phân tích",
                }),
                children: (
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Tag color="processing">
                        {t("docReader.analysisPeople", {
                          count: analysisResult.balkan_nodes.length,
                        })}
                      </Tag>
                    </div>
                    {analysisResult.gemini_error && (
                      <Alert
                        type="warning"
                        showIcon
                        message={t("docReader.geminiErrorTitle")}
                        description={analysisResult.gemini_error}
                      />
                    )}
                    <Card
                      size="small"
                      className="bg-muted"
                      title={t("docReader.analysisTitle", {
                        defaultValue: "Kết quả phân tích",
                      })}
                    >
                      <pre className="max-h-[520px] overflow-auto rounded bg-background p-3 text-xs leading-5 text-foreground">
                        {JSON.stringify(analysisResult.balkan_nodes, null, 2)}
                      </pre>
                    </Card>
                  </div>
                ),
              },
              {
                key: "diagram",
                label: t("docReader.diagramTabLabel", {
                  defaultValue: "Sơ đồ",
                }),
                children:
                  analysisResult.balkan_nodes.length > 0 ? (
                    <FamilyTreeVisualPanel
                      nodes={analysisResult.balkan_nodes}
                      treeName={t("docReader.inlineTreeTitle", {
                        defaultValue: "Sơ đồ từ phân tích",
                      })}
                    />
                  ) : (
                    <Empty description={t("docReader.inlineTreeEmpty")} />
                  ),
              },
            ]}
          />
        )}
      </Modal>
    </div>
  );

  if (embedded) {
    return mainContent;
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="px-4 md:px-6 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between border-b border-border">
        <div className="w-full md:w-auto flex items-start md:items-center gap-3 md:gap-4">
          <Button
            icon={<ArrowLeftOutlined />}
            type="text"
            onClick={() => navigate("/user/dashboard")}
            className="!text-primary"
          >
            {t("common.back", { defaultValue: "Quay lại" })}
          </Button>
          <div className="section-divider w-px h-6 mx-2 bg-border" />
          <div>
            <h1 className="text-2xl font-display font-bold text-foreground">
              {t("docReader.pageTitle")}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              {t("docReader.pageSubtitle")}
            </p>
          </div>
        </div>
        <div className="w-full md:w-auto flex flex-wrap items-center gap-2 md:gap-3 md:justify-end">
          <Tag color="gold">{t("docReader.tagFormats")}</Tag>
          <Tag color="red">{t("docReader.tagDragDrop")}</Tag>
        </div>
      </header>

      <section className="brand-gradient px-4 md:px-6 py-5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 text-primary-foreground">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-primary-foreground/80">
              {t("docReader.bannerLabel")}
            </p>
            <h2 className="text-3xl font-display font-bold mt-2">
              {t("docReader.bannerTitle")}
            </h2>
          </div>
          <div className="max-w-xl text-sm text-primary-foreground/90 leading-6">
            {t("docReader.bannerDesc")}
          </div>
        </div>
      </section>

      {mainContent}
    </div>
  );
};

export default DocumentReaderPage;
