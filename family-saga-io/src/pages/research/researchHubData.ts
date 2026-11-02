/**
 * Dữ liệu trang quản lý thông tin nghiên cứu (/nghien-cuu/quan-ly). Chỉ xem; sửa nội dung bằng PR vào file này.
 *
 * Nguồn số liệu duy nhất: family-tree-harness/research/FINDINGS.md, results/SUMMARY.md, results/best_f1.json
 * và trang "Câu hỏi nghiên cứu" (29/10/2026: 5 RQ, bảng 2 gồm 19 phương pháp). Không thêm số chưa đo;
 * chỗ chưa đo để `value: null`. Thẻ hỏi–đáp dùng lại defenseReviewData.ts, không chép lại ở đây.
 */

export type RqId = "RQ1" | "RQ2" | "RQ3" | "RQ4" | "RQ5";
export type Status = "measured" | "in_progress" | "todo";
/** human = người soát; machine = nhãn máy Gemini chưa soát; semi_auto = gold_builder hoặc phả hệ VGP dựng bằng luật. */
export type LabelSource = "human" | "machine" | "semi_auto";

export const STATUS_LABEL: Record<Status, string> = {
  measured: "Đã đo",
  in_progress: "Đang làm",
  todo: "Chưa làm",
};

export const LABEL_SOURCE_LABEL: Record<LabelSource, string> = {
  human: "Nhãn người",
  machine: "Nhãn máy",
  semi_auto: "Bán tự động",
};

/** Ngày chốt nội dung trang; trạng thái sau ngày này chưa cập nhật. */
export const UPDATED_AT = "2026-10-29";

export const CENTRAL_QUESTION =
  "Khai thác cấu trúc đặc thù của văn bản gia phả (danh sách theo đời, công thức đặt tên, niên hiệu và can chi, bản Hán đi kèm bản dịch Việt) có giúp vượt mô hình tinh chỉnh chuẩn trong nhận dạng thực thể, trích xuất quan hệ và dựng cây không, và vì sao?";

export interface ResearchQuestion {
  id: RqId;
  kind: "understand" | "improve";
  topic: string;
  question: string;
  experiment: string;
  status: Status;
  statusNote: string;
}

export const RESEARCH_QUESTIONS: ResearchQuestion[] = [
  {
    id: "RQ1",
    kind: "understand",
    topic: "Hiểu",
    question: "Mô hình tinh chỉnh chuẩn sai ở đâu trên văn bản gia phả, và vì sao mô hình này hơn mô hình kia?",
    experiment:
      "Kiểm định ghép cặp XLM-R và PhoBERT trên cùng 5 lượt; PhoBERT với dữ liệu tách từ VnCoreNLP; phân loại toàn bộ lỗi (ranh giới, nhầm loại, bỏ sót, thừa); đường học theo 5–25 cây.",
    status: "todo",
    statusNote: "Đã có số xuất phát (XLM-R 0,615, PhoBERT 0,538); chưa kiểm định ghép cặp, chưa phân tích lỗi.",
  },
  {
    id: "RQ2",
    kind: "improve",
    topic: "Cải tiến · NER",
    question: "Đưa tri thức miền gia phả vào mô hình có nâng F1 so với tinh chỉnh thuần không, ở loại thực thể nào, và vì sao?",
    experiment:
      "Bóc tách bốn cấu hình: baseline, +thích nghi miền, +tri thức có cấu trúc (niên hiệu, can chi, chức tước, \"đời thứ n\"), cả hai; cho xlmr-family và sikubert-family; 3 hạt giống.",
    status: "todo",
    statusNote: "Chưa chạy.",
  },
  {
    id: "RQ3",
    kind: "improve",
    topic: "Cải tiến · Dữ liệu",
    question: "Làm sao tận dụng dữ liệu nhãn máy và dữ liệu song ngữ Hán–Việt khi nhãn người rất ít?",
    experiment:
      "So sánh không dùng / dùng thô / dùng có lọc dữ liệu phụ, chấm trên nhãn người; chiếu nhãn từ phía Việt sang phía Hán qua cặp dòng đã người soát, chấm trên 15 trang chữ Hán người soát.",
    status: "todo",
    statusNote: "Dùng thô đã thử (0,595 so với 0,594, không khác biệt); bản có lọc và chiếu nhãn chưa chạy, chờ cặp dòng đã soát.",
  },
  {
    id: "RQ4",
    kind: "improve",
    topic: "Cải tiến · Quan hệ (đóng góp chính đề xuất)",
    question:
      "Quan hệ gia tộc được biểu đạt bằng cấu trúc trình bày hơn là bằng câu. Một phương pháp RE dựa trên cấu trúc có vượt RE mức câu và luật không?",
    experiment:
      "Hai tầng: phân tích bố cục thành khung cây, rồi mô hình chọn cha/mẹ học bằng giám sát xa từ 342 phả hệ VGP. Chấm trên chuẩn vàng mức cây 1.524 quan hệ và 30 quan hệ nhãn người; bóc tách từng tầng.",
    status: "todo",
    statusNote: "Đã có baseline luật (0/30; 0,015 trên chuẩn mức cây); phương pháp đề xuất chưa làm.",
  },
  {
    id: "RQ5",
    kind: "understand",
    topic: "Hiểu · Đầu–cuối",
    question: "Lỗi ở từng bước (NER, RE) lan sang cây gia phả cuối cùng như thế nào?",
    experiment:
      "Thay từng bước bằng bản đúng (oracle); đo tỉ lệ cạnh cha–con, vợ–chồng khớp và số vi phạm ràng buộc, có và không có bước sửa theo ràng buộc.",
    status: "todo",
    statusNote: "Chưa chạy.",
  },
];

export interface Hypothesis {
  id: string;
  rq: RqId;
  statement: string;
  status: Status;
  evidence: string;
}

export const HYPOTHESES: Hypothesis[] = [
  {
    id: "H1a",
    rq: "RQ1",
    statement: "PhoBERT thua XLM-R một phần vì dữ liệu chưa tách từ theo đúng bộ tách từ PhoBERT đã dùng (VnCoreNLP).",
    status: "todo",
    evidence: "Yếu đi: tách từ pyvi trên nhãn máy không giúp (0,516 → 0,493). Chưa thử VnCoreNLP, chưa thử trên nhãn người.",
  },
  {
    id: "H1b",
    rq: "RQ1",
    statement: "Lỗi PER_NAME tập trung ở ranh giới tên đi kèm tước hiệu, tên tự, tên hiệu và cách gọi theo thứ bậc (\"ông Cả\", \"cụ Phó\").",
    status: "todo",
    evidence: "PER_NAME yếu nhất (XLM-R 0,36–0,41; PhoBERT 0,38), DATE tốt nhất (0,78–0,79). Chưa phân loại lỗi.",
  },
  {
    id: "H2",
    rq: "RQ2",
    statement:
      "Thích nghi miền cải thiện cả năm loại thực thể; tri thức có cấu trúc cải thiện chủ yếu DATE, GENERATION, ORDER. Kết hợp cả hai tốt nhất.",
    status: "todo",
    evidence: "Chưa có số đo.",
  },
  {
    id: "H3a",
    rq: "RQ3",
    statement: "Hai giai đoạn (P3) thất bại vì nhiễu nhãn; lọc theo độ tin cậy sẽ cho cải thiện có ý nghĩa.",
    status: "todo",
    evidence: "Trộn thô: 0,595 so với 0,594 (t = −0,36); riêng PER_NAME tăng 0,143, LOC giảm 0,088. Nhãn bán tự động chỉ khớp người 0,40.",
  },
  {
    id: "H3b",
    rq: "RQ3",
    statement: "Nhãn chiếu qua cặp dòng Hán–Việt đã người soát tốt hơn nhãn Gemini khi chấm trên nhãn người chữ Hán.",
    status: "todo",
    evidence: "21.238/22.602 cặp là bản dịch máy Gemini, chỉ 82 cặp từ bản dịch người; chưa có trường đánh dấu cặp đã soát.",
  },
  {
    id: "H4",
    rq: "RQ4",
    statement: "RE dựa trên cấu trúc vượt rõ RE mức câu (trần lý thuyết 2/30) và luật mức tài liệu v2 (0,015).",
    status: "todo",
    evidence: "28/30 quan hệ nhãn người vắt qua nhiều dòng (khoảng cách trung vị 132 ký tự). Phương pháp chưa cài.",
  },
  {
    id: "H5",
    rq: "RQ5",
    statement: "Chất lượng cây phụ thuộc vào RE nhiều hơn NER; ràng buộc phả hệ sửa được một phần lỗi RE.",
    status: "todo",
    evidence: "Chưa có số đo.",
  },
];

export const STAGES = [
  "Tạo nhãn và dữ liệu",
  "Nhận dạng thực thể tiếng Việt",
  "Nhận dạng thực thể chữ Hán",
  "Trích xuất quan hệ",
  "Triển khai",
] as const;
export type Stage = (typeof STAGES)[number];

export interface Method {
  /** Số thứ tự bảng 2 của trang "Câu hỏi nghiên cứu". */
  n: number;
  stage: Stage;
  name: string;
  why: string;
  result: string;
  takeaway: string;
  rqs: RqId[];
  /** Kết quả âm, không khác biệt hoặc chưa kết luận được. */
  negative?: boolean;
  /** Loại nhãn của số đo trong cột kết quả, nếu có. */
  labelSource?: LabelSource;
}

export const METHODS: Method[] = [
  { n: 1, stage: "Tạo nhãn và dữ liệu", name: "Gemini gán nhãn thực thể tự động (133 gia phả)", why: "Chưa có nhãn; gán tay tốn công, LLM rẻ và nhanh", result: "Tên đúng nhưng 98,6% offset sai; chỉ gán 2.000 ký tự đầu, 60% văn bản không có nhãn", takeaway: "Bỏ offset của LLM, tự khớp lại bằng chuỗi; luôn kiểm độ phủ toàn văn", rqs: ["RQ3"], negative: true, labelSource: "machine" },
  { n: 2, stage: "Tạo nhãn và dữ liệu", name: "Lọc nhãn máy hai lớp: luật hình thức + Gemini thẩm định", why: "Gemini tự rà nhãn của chính nó chỉ bác 5% (đồng thuận vòng tròn)", result: "Hai bộ lọc gần như không trùng (14/149 chỗ), giảm 87% khối lượng soát; F1 mô hình 0,494 so với 0,496", takeaway: "Lọc chỉ dịch cán cân P/R, không thay được người soát", rqs: ["RQ3"], negative: true, labelSource: "machine" },
  { n: 3, stage: "Tạo nhãn và dữ liệu", name: "Nhãn bán tự động gold_builder (Gemini + luật + phả hệ), 114 cây", why: "Tăng số cây có nhãn", result: "Khớp nhãn người F1 0,400", takeaway: "Không dùng làm chuẩn vàng", rqs: ["RQ3"], negative: true, labelSource: "human" },
  { n: 4, stage: "Tạo nhãn và dữ liệu", name: "Người gán nhãn 25 cây (Label Studio)", why: "Số đo trên nhãn máy không cho biết độ chính xác thật", result: "692 thực thể, 30 quan hệ; người chỉ thêm, không xoá nhãn gợi ý (hiệu ứng neo)", takeaway: "Thước đo duy nhất đáng tin hiện nay; còn nhỏ", rqs: ["RQ1"], labelSource: "human" },
  { n: 5, stage: "Tạo nhãn và dữ liệu", name: "Chuẩn vàng quan hệ mức cây từ phả hệ VGP", why: "30 quan hệ quá ít để đo RE", result: "1.524 quan hệ neo vào văn bản; nhãn người khớp F1 0,47", takeaway: "Thước đo RE lớn và rẻ, nhưng gần như chỉ có cha–con, chưa người soát", rqs: ["RQ4", "RQ5"], labelSource: "semi_auto" },
  { n: 6, stage: "Tạo nhãn và dữ liệu", name: "Sửa văn bản sai bảng mã cũ TCVN3/VNI theo từng dòng", why: "23/342 cây không đọc được tên", result: "Sửa được 18/23 cây; neo thêm 17 quan hệ", takeaway: "Tiền xử lý bắt buộc trước NER/RE", rqs: ["RQ4"] },
  { n: 7, stage: "Nhận dạng thực thể tiếng Việt", name: "Từ điển (không học máy)", why: "Mức sàn để biết mô hình học có giá trị không", result: "Dev 75 câu F1 0,231 (CI 0,07–0,42)", takeaway: "Sàn; tập quá nhỏ để kết luận", rqs: ["RQ1"], negative: true, labelSource: "human" },
  { n: 8, stage: "Nhận dạng thực thể tiếng Việt", name: "mBERT trên nhãn máy đã lọc", why: "Đa ngữ, có sẵn script", result: "0,488 ± 0,019 (3 hạt giống)", takeaway: "Ba kiến trúc cùng dừng quanh 0,49: nút thắt ở nhãn, không ở mô hình", rqs: ["RQ1"], labelSource: "machine" },
  { n: 9, stage: "Nhận dạng thực thể tiếng Việt", name: "PhoBERT trên cùng nhãn máy, có và không tách từ (pyvi)", why: "Mô hình đơn ngữ tiếng Việt chuẩn, huấn luyện trước trên văn bản đã tách từ", result: "Không tách 0,516; tách từ pyvi 0,493 (t = −1,26)", takeaway: "pyvi không giúp; chưa thử VnCoreNLP và nhãn người", rqs: ["RQ1"], negative: true, labelSource: "machine" },
  { n: 10, stage: "Nhận dạng thực thể tiếng Việt", name: "XLM-R và PhoBERT trên 25 cây nhãn người, kiểm chéo 5 lượt theo cây", why: "Nhãn máy không đo được chất lượng; chia theo cây để tránh rò rỉ", result: "XLM-R 0,615 (chạy lại 0,594); PhoBERT 0,538", takeaway: "Số đáng tin nhất hiện có; chưa kiểm định ghép cặp", rqs: ["RQ1"], labelSource: "human" },
  { n: 11, stage: "Nhận dạng thực thể tiếng Việt", name: "Hai giai đoạn: 103 cây bán tự động rồi tinh chỉnh bằng nhãn người", why: "Tận dụng nhiều nhãn nhiễu khi nhãn người ít", result: "XLM-R 0,595 so với 0,594 (t = −0,36); PhoBERT 0,526 so với 0,538", takeaway: "Trộn thô không giúp; có thể có lợi theo từng loại thực thể", rqs: ["RQ3"], negative: true, labelSource: "human" },
  { n: 12, stage: "Nhận dạng thực thể tiếng Việt", name: "Bản cuối xlmr-family và phobert-family (22 cây huấn luyện, 3 cây dev)", why: "Cần mô hình triển khai cho API", result: "Dev 43 thực thể: 0,706 so với 0,633", takeaway: "Quy trình tiếng Việt dùng XLM-R (quyết định 28/10)", rqs: ["RQ1"], labelSource: "human" },
  { n: 13, stage: "Nhận dạng thực thể chữ Hán", name: "Từ điển (không học máy)", why: "Mức sàn", result: "Kiểm chéo 5 lượt theo sách 0,232", takeaway: "Sàn", rqs: ["RQ2"], labelSource: "machine" },
  { n: 14, stage: "Nhận dạng thực thể chữ Hán", name: "SikuBERT, mức ký tự", why: "Huấn luyện trước trên văn ngôn cổ, gần văn gia phả; mức ký tự không cần tách từ", result: "Kiểm chéo 0,658, bản cuối 0,715; hơn từ điển 0,446 (t = 10,8)", takeaway: "Học được quy luật của nhãn máy; độ chính xác thật chờ 15 trang người soát", rqs: ["RQ2", "RQ3"], labelSource: "machine" },
  { n: 15, stage: "Nhận dạng thực thể chữ Hán", name: "Công cụ NER chữ Hán của Kim Hán Nôm", why: "Công cụ sẵn có của lab trong nước", result: "Thử 1 câu: chỉ có nhãn PER, đúng ranh giới 2/4 tên", takeaway: "Chưa đánh giá được (n = 1)", rqs: ["RQ3"], negative: true },
  { n: 16, stage: "Trích xuất quan hệ", name: "Gán quan hệ như nhãn thực thể (mBERT)", why: "Dùng lại khung NER", result: "F1 = 0 cho cả ba loại quan hệ", takeaway: "Quan hệ không phải một đoạn chữ", rqs: ["RQ4"], negative: true },
  { n: 17, stage: "Trích xuất quan hệ", name: "Luật mức câu theo hướng dẫn gán nhãn", why: "Đơn giản, giải thích được", result: "0/30 quan hệ nhãn người", takeaway: "28/30 quan hệ vắt qua nhiều dòng", rqs: ["RQ4"], negative: true, labelSource: "human" },
  { n: 18, stage: "Trích xuất quan hệ", name: "Luật mức tài liệu v2 (phát triển trên 114 cây tự động, chấm một lần)", why: "Vượt giới hạn câu", result: "0/30 trên nhãn người; 0,015 trên chuẩn mức cây", takeaway: "Quan hệ nằm ở cấu trúc danh sách theo đời, không ở câu chữ", rqs: ["RQ4"], negative: true, labelSource: "human" },
  { n: 19, stage: "Triển khai", name: "Lượng tử hoá ONNX int8", why: "VPS chỉ có CPU; giảm dung lượng và độ trễ", result: "XLM-R khớp bản gốc 99%; SikuBERT chỉ F1 0,77 so với bản gốc", takeaway: "Chữ Hán dùng fp32 (quyết định 28/10)", rqs: [] },
];

export interface Result {
  id: string;
  task: "NER" | "RE";
  pipeline: "vi" | "han";
  system: string;
  /** Tập dữ liệu chấm. */
  dataset: string;
  /** Loại nhãn của tập chấm. */
  labelSource: LabelSource;
  value: number | null;
  n?: string;
  ci95?: string;
  /** ISO; null = nguồn không ghi ngày. */
  date: string | null;
  source: string;
  status: Status;
  rqs: RqId[];
  note?: string;
}

export const RESULTS: Result[] = [
  { id: "r-xlmr-cv5", task: "NER", pipeline: "vi", system: "XLM-R base (sweep_v1)", dataset: "Kiểm chéo 5 lượt theo cây, 25 cây", labelSource: "human", value: 0.615, n: "692 thực thể", date: "2026-10-25", source: "FINDINGS.md §8; best_f1.json", status: "measured", rqs: ["RQ1"], note: "Ngày ghi nhận, không phải ngày chạy. P 0,593, R 0,639." },
  { id: "r-xlmr-cv5-rerun", task: "NER", pipeline: "vi", system: "XLM-R base, chạy lại (P3 nhánh A)", dataset: "Kiểm chéo 5 lượt theo cây, 25 cây", labelSource: "human", value: 0.594, n: "692 thực thể", date: "2026-10-25", source: "results/vi_p3_colab/results.json", status: "measured", rqs: ["RQ1"], note: "Dao động giữa các lần chạy khoảng 0,02." },
  { id: "r-phobert-cv5", task: "NER", pipeline: "vi", system: "PhoBERT base (sweep_v1)", dataset: "Kiểm chéo 5 lượt theo cây, 25 cây", labelSource: "human", value: 0.538, n: "692 thực thể", date: "2026-10-25", source: "FINDINGS.md §8; best_f1.json", status: "measured", rqs: ["RQ1"], note: "Đối chứng." },
  { id: "r-xlmr-2stage", task: "NER", pipeline: "vi", system: "XLM-R base hai giai đoạn (+103 cây bán tự động)", dataset: "Kiểm chéo 5 lượt theo cây, 25 cây", labelSource: "human", value: 0.595, n: "692 thực thể", date: "2026-10-25", source: "FINDINGS.md §9; results/vi_p3_colab", status: "measured", rqs: ["RQ3"], note: "Huấn luyện có nhãn bán tự động, chấm bằng nhãn người. t = −0,36, không khác biệt." },
  { id: "r-xlmr-family-dev", task: "NER", pipeline: "vi", system: "xlmr-family v1 (= xlmr_ner_v1 đang chạy), epoch 17", dataset: "vi_final dev 3 cây", labelSource: "human", value: 0.706, n: "43 thực thể", date: "2026-10-28", source: "results/vi_phobert_family/result.json", status: "measured", rqs: ["RQ1"], note: "Dev cũng dùng chọn epoch → lạc quan; chưa có test riêng." },
  { id: "r-phobert-family-dev", task: "NER", pipeline: "vi", system: "phobert-family v1, epoch 11", dataset: "vi_final dev 3 cây", labelSource: "human", value: 0.633, n: "43 thực thể", date: "2026-10-28", source: "results/vi_phobert_family/result.json", status: "measured", rqs: ["RQ1"], note: "Đối chứng; dev cũng dùng chọn epoch." },
  { id: "r-vi-dict", task: "NER", pipeline: "vi", system: "Từ điển (độ dài tối thiểu 2)", dataset: "vi_final dev 75 câu", labelSource: "human", value: 0.231, ci95: "0,066–0,424", date: "2026-10-25", source: "results/SUMMARY.md; FINDINGS.md §6", status: "measured", rqs: ["RQ1"], note: "Không có test riêng." },
  { id: "r-semiauto-vs-human", task: "NER", pipeline: "vi", system: "Nhãn bán tự động gold_builder", dataset: "25 cây có cả hai bản nhãn", labelSource: "human", value: 0.4, date: "2026-10-25", source: "FINDINGS.md §8", status: "measured", rqs: ["RQ3"], note: "Đo chất lượng nhãn, không phải mô hình. P 0,359, R 0,451." },
  { id: "r-onnx-heldout", task: "NER", pipeline: "vi", system: "XLM-R ONNX int8 qua API", dataset: "98 cây ngoài split vi_final", labelSource: "semi_auto", value: 0.268, n: "2.612 thực thể", ci95: "0,225–0,322", date: "2026-10-25", source: "results/vi_heldout_api/vi__xlmr-ner-onnx-int8.json", status: "measured", rqs: [], note: "Không phải thước đo chất lượng: nhãn chấm chỉ khớp người 0,40." },
  { id: "r-han-dict-cv5", task: "NER", pipeline: "han", system: "Từ điển (không học máy)", dataset: "Kiểm chéo 5 lượt theo sách, 20 sách", labelSource: "machine", value: 0.232, date: "2026-10-25", source: "results/SUMMARY.md", status: "measured", rqs: ["RQ2"] },
  { id: "r-han-dict-test", task: "NER", pipeline: "han", system: "Từ điển (không học máy)", dataset: "han_final/test, 15 trang / 38 câu", labelSource: "machine", value: 0.444, ci95: "0,352–0,540", date: "2026-10-25", source: "results/SUMMARY.md", status: "measured", rqs: ["RQ2"] },
  { id: "r-sikubert-cv5", task: "NER", pipeline: "han", system: "SikuBERT 6 epoch/lượt", dataset: "Kiểm chéo 5 lượt theo sách, 20 sách", labelSource: "machine", value: 0.658, n: "21.519 thực thể", date: "2026-10-25", source: "results/han_sikubert_colab/results.json; best_f1.json", status: "measured", rqs: ["RQ2", "RQ3"] },
  { id: "r-sikubert-final", task: "NER", pipeline: "han", system: "sikubert-family v1 (chọn epoch 5 theo dev)", dataset: "han_final/test, 15 trang", labelSource: "machine", value: 0.715, ci95: "0,649–0,779", date: "2026-10-25", source: "results/han_sikubert_final/run.json; best_f1.json", status: "measured", rqs: ["RQ2", "RQ3"] },
  { id: "r-sikubert-final-human", task: "NER", pipeline: "han", system: "sikubert-family v1", dataset: "han_final/test, 15 trang", labelSource: "human", value: null, date: null, source: "results/SUMMARY.md (bảng SPEC §0.7)", status: "in_progress", rqs: ["RQ2", "RQ3"], note: "Chờ người soát 15 trang chữ Hán (B12a)." },
  { id: "r-sikubert-int8", task: "NER", pipeline: "han", system: "sikubert-family ONNX int8 (QInt8 mặc định)", dataset: "100 câu, so với đầu ra bản fp32", labelSource: "machine", value: 0.769, date: "2026-10-28", source: "FINDINGS.md §17", status: "measured", rqs: [], note: "Đo độ khớp với bản fp32, không phải độ chính xác. Giữ fp32 cho FFN-out + classifier: 0,916." },
  { id: "r-re-rule-sentence", task: "RE", pipeline: "vi", system: "Luật mức câu (gợi ý trong hướng dẫn) + thực thể gold", dataset: "25 cây, 30 quan hệ", labelSource: "human", value: 0, date: "2026-10-25", source: "FINDINGS.md §11.2", status: "measured", rqs: ["RQ4"], note: "28/30 quan hệ vắt qua dòng; trần mức câu 2/30." },
  { id: "r-re-semiauto", task: "RE", pipeline: "vi", system: "Nhãn bán tự động gold_builder", dataset: "25 cây, 30 quan hệ", labelSource: "human", value: 0.287, date: "2026-10-25", source: "FINDINGS.md §11.2", status: "measured", rqs: ["RQ4"], note: "P 0,170, R 0,933: bắt gần hết nhưng thừa nhiều." },
  { id: "r-re-doc-v2-human", task: "RE", pipeline: "vi", system: "Luật mức tài liệu v2 + thực thể gold", dataset: "25 cây, 30 quan hệ", labelSource: "human", value: 0, date: "2026-10-25", source: "FINDINGS.md §13", status: "measured", rqs: ["RQ4"], note: "Chấm một lần." },
  { id: "r-re-human-vs-tree", task: "RE", pipeline: "vi", system: "Nhãn người", dataset: "Chuẩn vàng mức cây (pha_he), 1.524 quan hệ neo", labelSource: "semi_auto", value: 0.472, date: "2026-10-25", source: "FINDINGS.md §14", status: "measured", rqs: ["RQ4", "RQ5"], note: "Chuẩn mức cây dựng bằng luật generation_stack, chưa người soát." },
  { id: "r-re-doc-v2-tree", task: "RE", pipeline: "vi", system: "Luật mức tài liệu v2", dataset: "Chuẩn vàng mức cây, 139 cây", labelSource: "semi_auto", value: 0.015, date: "2026-10-25", source: "FINDINGS.md §14", status: "measured", rqs: ["RQ4"] },
  { id: "r-re-structure", task: "RE", pipeline: "vi", system: "RE dựa trên cấu trúc + giám sát xa (đề xuất)", dataset: "Chuẩn vàng mức cây và 30 quan hệ nhãn người", labelSource: "human", value: null, date: null, source: "Trang Câu hỏi nghiên cứu, RQ4", status: "todo", rqs: ["RQ4"] },
  { id: "r-xlmr-han", task: "NER", pipeline: "han", system: "XLM-R", dataset: "—", labelSource: "machine", value: null, date: null, source: "results/SUMMARY.md (bảng SPEC §0.7)", status: "todo", rqs: ["RQ2"] },
  { id: "r-gemini", task: "NER", pipeline: "vi", system: "Gemini (vi/han)", dataset: "—", labelSource: "human", value: null, date: null, source: "results/SUMMARY.md (bảng SPEC §0.7)", status: "todo", rqs: ["RQ3"], note: "Gọi Gemini tốn tiền." },
  { id: "r-vote", task: "NER", pipeline: "han", system: "Bỏ phiếu đa nguồn (vi/han)", dataset: "—", labelSource: "human", value: null, date: null, source: "results/SUMMARY.md (bảng SPEC §0.7)", status: "todo", rqs: ["RQ3"], note: "Hạ xuống thí nghiệm phụ (đề xuất 29/10)." },
];

export const EVALUATION_RULES = [
  "Chia dữ liệu theo cây (tiếng Việt) hoặc theo sách (chữ Hán); không để cùng gia phả rơi vào cả huấn luyện và kiểm tra.",
  "Tập kiểm tra là nhãn người soát; số đo trên nhãn máy chỉ báo cáo riêng, có ghi rõ.",
  "Mọi so sánh có baseline, khoảng tin cậy bootstrap và kiểm định ghép cặp; ít nhất 3 hạt giống. Chênh lệch nhỏ hơn ~0,02 F1 không được diễn giải.",
  "Kết quả mới qua cổng chống tụt của harness: chỉ so cùng tập dữ liệu và cùng loại nhãn.",
];

/** Bỏ dấu tiếng Việt để tìm kiếm không dấu. */
export const plain = (x: string) => x.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d").toLowerCase();

export const matches = (query: string, ...fields: (string | undefined)[]) => {
  const q = plain(query.trim());
  return !q || fields.some((f) => f !== undefined && plain(f).includes(q));
};

/** Số kiểu Việt: 0,615. */
export const fmt = (v: number) => v.toFixed(3).replace(".", ",");
