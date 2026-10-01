import { useEffect, useRef, useState } from "react";
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileImageOutlined,
  FileTextOutlined,
  HistoryOutlined,
  ReloadOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
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
import { ReaderWorkspace } from "@/components/documents/ReaderWorkspace";
import type { BBoxItem } from "@/components/documents/BoundingBoxOverlay";
import { PipelineStepsPanel, type VoteMeta } from "@/components/documents/PipelineStepsPanel";

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
  bbox?: BBoxItem[][] | null;
  translation_text?: string | null;
  vote_meta?: VoteMeta[] | null;
  pipeline_version?: string;
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

const backendBaseUrl = import.meta.env.VITE_BACKEND_URL ?? "";
/** Giá trị `lang_type` của Kim Hán Nôm: 0 tự động, 1 Hán, 2 Nôm. */
type HannomLangType = 0 | 1 | 2;
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
  const [langType, setLangType] = useState<HannomLangType>(0);
  const [workspaceVersion, setWorkspaceVersion] = useState(0);
  /** Mặc định BẬT (luôn có thể gõ Hán-Nôm trực tiếp ngay từ đầu, không cần
   * bật checkbox trước) — tắt thì cột Hán-Nôm chuyển về chỉ đọc (xem kết quả
   * OCR mà không sửa). Chỉ ảnh hưởng hiển thị cục bộ, hannomText không được
   * gửi lên backend phân tích (handleAnalyzeFamilyTree chỉ dùng documentText). */
  const [isHannomEditable, setIsHannomEditable] = useState(true);
  const [hannomText, setHannomText] = useState("");
  const [hannomEdited, setHannomEdited] = useState(false);
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
      return created.id;
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

  // Ô Hán-Nôm mặc định đã bật gõ tay — tự đồng bộ nội dung từ OCR/tài liệu
  // đã có cho tới khi người dùng thật sự gõ (hannomEdited=true), để "thêm
  // ảnh hay pdf thì lấy text bỏ vô [ô] thôi" thay vì hiện ô trống.
  useEffect(() => {
    if (!hannomEdited) {
      setHannomText(analysisResult?.hannom_text ?? existingHannomText ?? "");
    }
  }, [analysisResult?.hannom_text, existingHannomText, hannomEdited]);

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
    setHannomText("");
    setHannomEdited(false);
    setExistingHannomText(null);
    setIsHannomEditable(false);
    setWorkspaceVersion((value) => value + 1);
    setCurrentScanId(null);
    setLangType(0);
  };

  const loadFile = async (file: File) => {
    if (imageUrl) {
      URL.revokeObjectURL(imageUrl);
    }

    setHannomText("");
    setHannomEdited(false);
    setExistingHannomText(null);
    setIsHannomEditable(false);
    setWorkspaceVersion((value) => value + 1);
    setCurrentScanId(null);
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
        setDocumentText(normalizedText);
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

        setDocumentText(normalizedText);
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
        handleHannomTextChange((hannomEdited ? hannomText : displayedHannom) + text);
      } else {
        setDocumentText((prev) => prev + text);
        if (!previewType) setPreviewType("text");
      }
    } catch {
      toast.error(t("docReader.pasteFailed"));
    }
  };

  const handleToggleHannomEditable = (nextValue: boolean) => {
    setIsHannomEditable(nextValue);
  };

  const handleHannomTextChange = (text: string) => {
    setHannomText(text);
    setHannomEdited(true);
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
    if (isParsing || isAnalyzing) return;
    await handleSelectedFiles(event.dataTransfer.files);
  };

  const handleAnalyzeFamilyTree = async () => {
    const isTextLike = previewType === "docx" || previewType === "text";
    const isImageLike = previewType === "image" || previewType === "pdf";

    if (isTextLike && !documentText.trim()) {
      setAnalysisError(t("docReader.errNeedDocxToAnalyze"));
      return;
    }
    if (isImageLike && !activeFile && analysisResult?.ocr_text == null) {
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

    setAnalysisError(null);

    // Sau lần OCR đầu, phân tích lại dùng văn bản Quốc ngữ (có thể đã sửa) thay vì OCR lại.
    const hasOcrText = isImageLike && analysisResult?.ocr_text != null;
    const shouldOcr = isImageLike && !hasOcrText;
    if (hasOcrText && !documentText.trim()) {
      setAnalysisError(t("docReader.errNeedDocxToAnalyze"));
      return;
    }

    setIsAnalyzing(true);
    try {
      let analysisScanId = currentScanId;
      if (isAuthenticated && !analysisScanId && isTextLike) {
        analysisScanId = await registerScan(
          activeFile ?? new File([documentText], "manual-input.txt", { type: "text/plain" }),
          documentText,
        ) ?? null;
      }
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
        bbox: raw.bbox ?? analysisResult?.bbox ?? null,
        translation_text: raw.translation_text ?? analysisResult?.translation_text ?? null,
        vote_meta: raw.vote_meta ?? analysisResult?.vote_meta ?? null,
        pipeline_version: raw.pipeline_version ?? analysisResult?.pipeline_version,
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
      if (analysisScanId) {
        await updateUserDocument(analysisScanId, {
          request_id: payload.request_id ?? undefined,
          tree_status: "draft",
          ocr_status: isImageLike ? "completed" : "skipped",
          source_text: shouldOcr ? payload.ocr_text ?? undefined : documentText,
          source_file_key: shouldOcr ? payload.source_file_key ?? undefined : undefined,
        });
      }
      if (isAuthenticated) void fetchHistory();
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

  const isImageInput = previewType === "image" || previewType === "pdf";
  const awaitingOcr = isImageInput && analysisResult?.ocr_text == null;
  const busy = isParsing || isAnalyzing;
  const displayedHannom = hannomEdited ? hannomText : analysisResult?.hannom_text || existingHannomText || "";
  const chooseFile = (kind: "document" | "image") => {
    if (!fileInputRef.current) return;
    fileInputRef.current.accept = kind === "image" ? "image/png,image/jpeg,image/webp" : ".pdf,.docx,.txt";
    fileInputRef.current.click();
  };
  const changeVietnameseText = (text: string) => {
    setDocumentText(text);
    if (!previewType) setPreviewType("text");
  };

  const mainContent = (
    <div className={`reader-page space-y-5 ${embedded ? "" : "px-4 md:px-6 py-8"}`}>
      <div className="rounded-xl bg-card p-4 md:p-6">
        <div className="reader-settings">
          <div className="reader-setting">
            <label htmlFor="reader-document-type">{t("docReader.docTypeLabel")}</label>
            <Tooltip title={t("docReader.docTypeHint")}>
              <Select id="reader-document-type" value="auto" disabled
                options={[{ value: "auto", label: t("docReader.docTypeAuto") }]} />
            </Tooltip>
          </div>
          <div className="reader-setting">
            <label htmlFor="reader-language">{t("docReader.langTypeLabel")}</label>
            <Select<HannomLangType> id="reader-language" value={langType} onChange={setLangType} disabled={busy}
              options={[
                { value: 0, label: t("docReader.langTypeAuto") },
                { value: 1, label: t("docReader.langTypeHan") },
                { value: 2, label: t("docReader.langTypeNom") },
              ]} />
          </div>
        </div>
        <div className="reader-upload-actions">
          <Button size="large" icon={<ReloadOutlined />} disabled={busy} onClick={resetPreview}>{t("docReader.btnReset")}</Button>
          <Button size="large" icon={<FileTextOutlined />} disabled={busy} onClick={() => chooseFile("document")}>{t("docReader.uploadDocument")}</Button>
          <Button size="large" icon={<FileImageOutlined />} disabled={busy} onClick={() => chooseFile("image")}>{t("docReader.uploadImage")}</Button>
          <Typography.Text type="secondary" className="md:ml-2">{t("docReader.readerUploadHint")}</Typography.Text>
          <input ref={fileInputRef} type="file" className="hidden" aria-label={t("docReader.btnChooseFile")}
            onChange={async (event) => {
              const input = event.currentTarget;
              if (input.files) await handleSelectedFiles(input.files);
              input.value = "";
            }} />
        </div>
        <p className="reader-file-summary" role="status">
          {activeFile ? `${t("docReader.fileInfoName")}: ${activeFile.name}` : t("docReader.readerEmptyHint")}
        </p>
        {errorMessage && <Alert showIcon type="warning" message={errorMessage} className="mb-4" />}
        {analysisError && <Alert showIcon type="error" message={t("docReader.analysisFailedTitle")} description={analysisError} className="mb-4" />}
        <div onDragOver={(event) => { event.preventDefault(); if (!busy) setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)} onDrop={handleDrop}
          className={isDragging ? "rounded-xl ring-2 ring-primary" : ""}>
          <Spin spinning={busy} tip={t(isParsing ? "docReader.parsing" : "docReader.readerProcessing")}>
            <ReaderWorkspace
              key={workspaceVersion}
              hannomText={isHannomEditable ? hannomText : displayedHannom}
              vietnameseText={documentText} editableHannom={isHannomEditable}
              vietnameseDisabled={awaitingOcr} busy={busy} imageUrl={imageUrl} filename={activeFile?.name}
              translationText={analysisResult?.translation_text || undefined}
              bbox={analysisResult?.bbox?.[0] || null}
              onHannomChange={handleHannomTextChange} onVietnameseChange={changeVietnameseText}
              onToggleHannom={handleToggleHannomEditable} onPaste={handlePasteActiveColumn} onCopy={handleCopyQuocNgu}
            />
          </Spin>
        </div>
        <PipelineStepsPanel
          pipelineVersion={analysisResult?.pipeline_version}
          transliterationText={analysisResult?.ocr_text}
          translationText={analysisResult?.translation_text}
          voteMeta={analysisResult?.vote_meta}
        />
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <Typography.Text type="secondary">{t(awaitingOcr ? "docReader.readerOcrHint" : "docReader.readerAnalyzeHint")}</Typography.Text>
          <Button type="primary" size="large" loading={isAnalyzing}
            disabled={isParsing || (!isAuthenticated && guestQuota.exhausted) ||
              (awaitingOcr ? !activeFile : !documentText.trim() || previewType === "unsupported")}
            onClick={handleAnalyzeFamilyTree}>
            {t(awaitingOcr ? "docReader.readerOcrAnalyze" : "docReader.btnAnalyzeTree")}
          </Button>
        </div>
        {!isAuthenticated && <div className="mt-3">
          {guestQuota.exhausted ? <Alert showIcon type="warning" message={t("docReader.quotaExceeded")}
            action={<Button onClick={() => navigate("/login")}>{t("auth.loginBtn")}</Button>} />
            : <Typography.Text type="secondary">{t("docReader.quotaRemaining", { count: guestQuota.remaining })}</Typography.Text>}
        </div>}
        {statusMessage && <p role="status" className="mt-3 mb-0 text-sm text-muted-foreground">{statusMessage}</p>}
      </div>
      {embedded && currentScanId != null && <ServerSavedAlert />}
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
