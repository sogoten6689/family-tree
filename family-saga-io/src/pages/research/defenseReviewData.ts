/**
 * Ngân hàng câu hỏi ôn tập bảo vệ luận văn (trang /nghien-cuu/on-tap). Không đặt ở src/data/ vì thư mục đó bị .gitignore.
 *
 * Nguồn số liệu duy nhất: family-tree-harness/research/FINDINGS.md (§3–17),
 * results/SUMMARY.md và trang "Câu hỏi nghiên cứu" (bảng 2: 19 phương pháp).
 * Không thêm số chưa đo; chỗ chưa có số ghi rõ "chưa đo" và đánh dấu `gap`.
 */

export type AxisId = "motivation" | "method" | "experiment" | "limits" | "application";

export const AXES: { id: AxisId; label: string; hint: string }[] = [
  { id: "motivation", label: "1. Động lực và bài toán", hint: "Bài toán, research gap, hình thức hoá, giả định" },
  { id: "method", label: "2. Phương pháp và đóng góp", hint: "Tự thiết kế hay kế thừa, vì sao chọn, chi phí, tính tổng quát" },
  { id: "experiment", label: "3. Thực nghiệm", hint: "Baseline công bằng, ablation, thống kê, rò rỉ, gán nhãn" },
  { id: "limits", label: "4. Phân tích lỗi và giới hạn", hint: "Failure cases, điều kiện biên, đánh đổi" },
  { id: "application", label: "5. Ứng dụng và hướng phát triển", hint: "Rào cản triển khai, bước tiếp theo" },
];

export interface FlashCard {
  id: string;
  axis: AxisId;
  question: string;
  answer: string[];
  /** Có phần chưa đo/chưa làm: phải chủ động thừa nhận khi bị hỏi. */
  gap?: string;
}

export const FLASHCARDS: FlashCard[] = [
  // ── Trục 1 ──
  {
    id: "m1",
    axis: "motivation",
    question: "Phát biểu hình thức bài toán của đề tài.",
    answer: [
      "Đầu vào: văn bản gia phả tiếng Việt hoặc chữ Hán (ảnh đã OCR hoặc chữ gõ sẵn).",
      "NER: gán nhãn chuỗi BIO, trả về tập thực thể (đầu, cuối, loại) với 5 loại PER_NAME, LOC, DATE, ORDER, GENERATION.",
      "RE: tập bộ ba (người A, người B, quan hệ) với quan hệ ∈ {FATHER_OF, MOTHER_OF, SPOUSE}; mọi quan hệ là PER_NAME → PER_NAME.",
      "Dựng cây: đồ thị thoả ràng buộc phả hệ (mỗi người tối đa một cha, không ai là tổ tiên của chính mình).",
    ],
  },
  {
    id: "m2",
    axis: "motivation",
    question: "Research gap của đề tài là gì?",
    answer: [
      "Quan hệ gia tộc trong gia phả nằm ở cấu trúc trình bày (danh sách theo đời), không ở câu: 28/30 quan hệ nhãn người vắt qua nhiều dòng (khoảng cách trung vị 132 ký tự, tối đa 2.382).",
      "Hệ quả đo được: luật mức câu 0/30; luật mức tài liệu 0/30 trên nhãn người và F1 0,015 trên chuẩn vàng mức cây 1.524 quan hệ. RE mức câu có trần lý thuyết 2/30.",
      "Thiếu dữ liệu: chỉ 25 cây nhãn người (692 thực thể, 30 quan hệ); chữ Hán chưa có trang nào người soát.",
    ],
    gap: "Cần chuẩn bị sẵn phần tổng quan tài liệu: các công trình NER/RE trên văn bản lịch sử, gia phả và văn ngôn để chứng minh khoảng trống không chỉ bằng số của mình.",
  },
  {
    id: "m3",
    axis: "motivation",
    question: "Đề tài dựa trên những giả định nào?",
    answer: [
      "Văn bản đầu vào đã là chữ; lỗi OCR chưa được tính vào số đo NER/RE.",
      "Phả hệ VGP (pha_he) dựng bằng luật generation_stack, confidence 0,65, chưa người soát — được giả định đủ đúng để làm chuẩn vàng mức cây và nguồn giám sát xa.",
      "Nhãn chữ Hán hiện là nhãn máy Gemini; mọi số đo chữ Hán giả định nhãn máy là thước đo, nên chỉ đo mức tái tạo nhãn máy.",
      "Quy tắc nhãn Hán chưa được thầy duyệt.",
    ],
    gap: "Giả định về pha_he và nhãn Hán chưa kiểm chứng bằng người; phải nói rõ khi trình bày.",
  },
  {
    id: "m4",
    axis: "motivation",
    question: "Vì sao văn bản gia phả khó hơn NER/RE thông thường?",
    answer: [
      "PER_NAME là loại yếu nhất (XLM-R 0,36–0,41 tuỳ lần chạy; PhoBERT 0,38), trong khi DATE tốt nhất (0,78–0,79): tên đi kèm tước hiệu, tên tự, tên hiệu, cách gọi theo thứ bậc.",
      "Dữ liệu rất nhỏ: CoNLL tiếng Việt chỉ 15.827 token huấn luyện, PER_NAME 180.",
      "Văn bản dài: trung vị 2.168 ký tự, tối đa 84.540, phải cắt đoạn.",
      "Bảng mã cũ: 23/342 cây (6,7%) dùng TCVN3/VNI, nhiều cây trộn với Unicode theo từng dòng.",
    ],
  },

  // ── Trục 2 ──
  {
    id: "p1",
    axis: "method",
    question: "Phần nào em tự thiết kế, phần nào kế thừa?",
    answer: [
      "Thẳng thắn: 19 phương pháp đã thử đều là áp dụng cái có sẵn (tinh chỉnh mô hình tiền huấn luyện, luật, LLM, công cụ ngoài).",
      "Tự xây: chuẩn vàng quan hệ mức cây từ phả hệ VGP (1.524 quan hệ neo văn bản, gấp ~50 lần nhãn người); bộ chấm và cổng chống tụt (dung sai 0,03); bộ sửa bảng mã cũ theo từng dòng (sửa được 18/23 cây); khớp lại offset nhãn Gemini bằng chuỗi.",
      "Đóng góp phương pháp chính đề xuất là RQ4: RE dựa trên bố cục gia phả + giám sát xa từ phả hệ.",
    ],
    gap: "RQ4 chưa có kết quả. Phải nói rõ đây là phần đang làm, kèm bằng chứng vì sao chọn (bảng 2, #16–18).",
  },
  {
    id: "p2",
    axis: "method",
    question: "Vì sao chọn XLM-R chứ không phải PhoBERT cho tiếng Việt?",
    answer: [
      "Kiểm chéo 5 lượt theo cây trên 25 cây nhãn người: XLM-R 0,615 (chạy lại 0,594), PhoBERT 0,538.",
      "Bản cuối cùng dev 3 cây: xlmr-family 0,706, phobert-family 0,633; cùng chiều với CV5.",
      "Triển khai: XLM-R int8 khớp bản gốc 99% (PhoBERT int8 khớp 98,85%).",
      "Thử tách từ pyvi cho PhoBERT trên nhãn máy: −0,023 (t = −1,26), không giúp.",
    ],
    gap: "Chưa kiểm định ghép cặp XLM-R/PhoBERT; chưa thử tách từ VnCoreNLP (H1a). Dao động giữa các lần chạy ~0,02.",
  },
  {
    id: "p3",
    axis: "method",
    question: "Vì sao chọn SikuBERT cho chữ Hán?",
    answer: [
      "Được huấn luyện trước trên văn ngôn cổ (Tứ khố toàn thư), gần văn gia phả nhất; mức ký tự nên không cần tách từ.",
      "CV5 theo sách 0,658, hơn từ điển 0,232 trung bình 0,446 mỗi lượt (t = 10,8, df = 4).",
      "Lưu ý bắt buộc: đo trên nhãn máy Gemini, chỉ chứng minh mô hình học được quy luật nhất quán của nhãn máy.",
    ],
    gap: "Chưa so với XLM-R hay mô hình Hán khác trên chữ Hán; chưa có độ chính xác thật (chờ 15 trang người soát).",
  },
  {
    id: "p4",
    axis: "method",
    question: "Vì sao không để LLM (Gemini) trích xuất trực tiếp?",
    answer: [
      "Tên đúng nhưng 98,6% vị trí (offset) sai; chỉ gán 2.000 ký tự đầu, 60% văn bản không có nhãn.",
      "Nhãn bán tự động (Gemini + luật + phả hệ) chỉ khớp nhãn người F1 0,40.",
      "Cho Gemini tự rà nhãn của mình chỉ bác 5%: đồng thuận vòng tròn.",
      "Tốn tiền, khó giải thích; giữ làm baseline.",
    ],
    gap: "Chưa đo Gemini như một hệ thống baseline trên cùng tập nhãn người (ô Gemini trong bảng SPEC còn trống).",
  },
  {
    id: "p5",
    axis: "method",
    question: "Độ phức tạp, kích thước, độ trễ so với baseline?",
    answer: [
      "Kích thước ONNX: XLM-R int8 278 MB; PhoBERT int8 135,2 MB; SikuBERT fp32 434 MB, int8 109 MB.",
      "Độ trễ đã đo: PhoBERT int8 trung vị 30 ms/câu (CPU Colab 1 luồng); API chữ Hán fp32 trung vị 111 ms, p95 125 ms/request (Mac i9, gồm HTTP).",
      "Mô hình Transformer: self-attention O(n²) theo độ dài chuỗi, nên văn bản dài phải cắt đoạn.",
    ],
    gap: "Chưa đo độ trễ/bộ nhớ trên VPS thật; chưa có bảng số tham số và thời gian huấn luyện đặt cạnh baseline từ điển.",
  },
  {
    id: "p6",
    axis: "method",
    question: "Vì sao đề xuất RE dựa trên bố cục + giám sát xa (RQ4)?",
    answer: [
      "28/30 quan hệ vắt dòng; mọi luật ngôn ngữ ≈ 0 (gán quan hệ như nhãn thực thể F1 = 0; luật mức câu 0/30; luật tài liệu 0,015).",
      "Đã có 342 cây phả hệ VGP và 1.524 quan hệ neo văn bản để làm giám sát xa, không cần gán tay.",
      "Phương án khác: gán tay thêm (25 cây mới có 30 quan hệ, quá tốn); LLM (offset không tin được, tốn tiền) chỉ giữ làm baseline.",
    ],
  },
  {
    id: "p7",
    axis: "method",
    question: "Phương pháp có tổng quát không?",
    answer: [
      "Đã chạy trên hai ngôn ngữ (Việt, chữ Hán), chia dữ liệu theo cây/sách để đo khái quát sang gia phả chưa thấy.",
      "Chuẩn vàng mức cây gần như chỉ có cha–con: FATHER_OF 1.512, MOTHER_OF 10, SPOUSE 2.",
    ],
    gap: "Chưa thử trên nguồn ngoài VGP; MOTHER_OF/SPOUSE và RE chữ Hán chưa có chuẩn vàng.",
  },

  // ── Trục 3 ──
  {
    id: "e1",
    axis: "experiment",
    question: "So sánh XLM-R và PhoBERT có công bằng không?",
    answer: [
      "Cùng 25 cây nhãn người, cùng 5 lượt chia theo cây; bản cuối cùng chia 22 cây huấn luyện / 3 cây dev.",
      "phobert-family: 20 epoch, lr 5e-5, chọn epoch theo dev (epoch 11); xlmr-family chọn epoch 17.",
      "Dev chỉ 43 thực thể và cũng dùng chọn epoch → số lạc quan; chênh 0,07 ≈ 3 thực thể.",
    ],
    gap: "Cần chuẩn bị bảng siêu tham số đã quét cho từng mô hình (sweep_v1) để trả lời 'đã tinh chỉnh công bằng chưa'.",
  },
  {
    id: "e2",
    axis: "experiment",
    question: "Em kiểm định ý nghĩa thống kê thế nào?",
    answer: [
      "t-test theo lượt (df = 4): hai giai đoạn 0,595 so với 0,594, t = −0,36 (không khác); SikuBERT so với từ điển t = 10,8; PhoBERT so với mBERT t = 1,71 (không ý nghĩa).",
      "Khoảng tin cậy bootstrap: sikubert-family 0,715 (CI95 0,649–0,780); từ điển Việt 0,231 (CI 0,07–0,42).",
      "Nhiều hạt giống: mBERT 0,488 ± 0,019 (3 hạt giống). Dao động lần chạy đo được ~0,02, chênh nhỏ hơn mức này không diễn giải.",
    ],
    gap: "Chưa kiểm định ghép cặp XLM-R/PhoBERT; cấu hình chính chưa chạy 3 hạt giống.",
  },
  {
    id: "e3",
    axis: "experiment",
    question: "Làm sao tránh rò rỉ dữ liệu (data leakage)?",
    answer: [
      "Chia theo cây (tiếng Việt) và theo sách (chữ Hán): văn bản cùng gia phả không rơi vào cả huấn luyện và kiểm tra.",
      "Luật RE v2 phát triển trên 114 cây tự động, chấm trên nhãn người đúng một lần; chẩn đoán sau đó không dùng để sửa số.",
      "Đánh dấu vòng tròn: nhãn bán tự động khớp gold mức cây 0,286 nhưng gold_builder đã dùng pha_he.",
    ],
    gap: "Dev 3 cây vừa chọn epoch vừa báo cáo (0,706) → không có test riêng cho bản cuối.",
  },
  {
    id: "e4",
    axis: "experiment",
    question: "Quy trình gán nhãn và độ đồng thuận (kappa)?",
    answer: [
      "25 cây gán trên Label Studio từ nhãn gợi ý: 692 thực thể, 30 quan hệ.",
      "Quan sát hiệu ứng neo: người chỉ thêm, không xoá nhãn gợi ý.",
      "Có nhãn đáng ngờ ngay câu đầu tập huấn luyện ('Thủy Nguyên' không được gán LOC).",
    ],
    gap: "Chưa đo Cohen/Fleiss kappa; chưa có người gán thứ hai. Kế hoạch: gán lại độc lập một mẫu để biết trần chất lượng chuẩn vàng.",
  },
  {
    id: "e5",
    axis: "experiment",
    question: "Có ablation không?",
    answer: [
      "Các so sánh đã có: hai giai đoạn so với chỉ nhãn người; có/không tách từ pyvi; lọc nhãn hai lớp (0,494 so với 0,496, nhãn máy); A/B 6 kiểu lượng tử hoá SikuBERT.",
      "Ablation dự kiến: RQ2 bốn cấu hình (baseline, +thích nghi miền, +tri thức, cả hai); RQ4 chỉ tầng bố cục, chỉ tầng mô hình, cả hai.",
    ],
    gap: "Chưa có ablation cho phương pháp đề xuất của đề tài.",
  },
  {
    id: "e6",
    axis: "experiment",
    question: "Vì sao chọn các tập dữ liệu này?",
    answer: [
      "Tiếng Việt: 342 cây VGP có cả Phả ký và phả hệ → vừa có văn bản vừa có cây để làm chuẩn vàng mức cây.",
      "Chữ Hán: 20 sách, 1.147 trang, chia 5 lượt theo sách; mỗi sách làm test đúng một lần.",
      "Tập test han_final chỉ 38 câu → dùng CV theo sách làm số chính.",
    ],
  },

  // ── Trục 4 ──
  {
    id: "l1",
    axis: "limits",
    question: "Mô hình NER sai chủ yếu ở đâu?",
    answer: [
      "PER_NAME yếu nhất; ví dụ cắt ranh giới 'Vũ Xuân Cường' → 'Vũ', 'Ninh Bình' → 'Ninh'.",
      "Trên 98 cây (đo với nhãn bán tự động): bỏ sót hoàn toàn 56,5%, đúng loại nhưng lệch ranh giới 17,9%, sai loại 3,2%.",
    ],
    gap: "Phân rã lỗi này đo với nhãn bán tự động; phân loại lỗi trên nhãn người (RQ1) chưa làm.",
  },
  {
    id: "l2",
    axis: "limits",
    question: "Khi nào phương pháp mất tác dụng?",
    answer: [
      "RE theo luật: quan hệ chỉ có trong sơ đồ phả hệ dạng văn bản (tên đứng riêng từng dòng) hoặc cần đồng tham chiếu ('con Doãn Khuê' cách 38 dòng).",
      "Văn bản sai bảng mã cũ: tên không đọc được; 5/23 cây chưa sửa được.",
      "Lượng tử hoá int8 với SikuBERT: F1 thực thể chỉ 0,769 so với fp32; per-channel QInt8 ra 0 thực thể.",
    ],
  },
  {
    id: "l3",
    axis: "limits",
    question: "Có những đánh đổi nào?",
    answer: [
      "Hai giai đoạn: recall +0,065 nhưng precision −0,046; PER_NAME +0,143, LOC −0,088 (gợi ý, chưa kiểm định).",
      "PhoBERT recall cao hơn nhưng precision thấp hơn nhiều (fp 24 so với 12).",
      "Chữ Hán: fp32 434 MB chính xác như torch; int8 109 MB nhanh hơn nhưng hỏng thực thể. Chọn fp32 (28/10).",
      "Lọc nhãn máy giảm 87% khối lượng người soát nhưng chỉ dịch cán cân P/R, F1 gần như không đổi.",
    ],
  },
  {
    id: "l4",
    axis: "limits",
    question: "Vì sao SikuBERT nhạy với lượng tử hoá hơn XLM-R?",
    answer: [
      "Quan sát: XLM-R int8 khớp 99% nhãn; SikuBERT khớp 96,1% nhãn ký tự nhưng F1 thực thể 0,769 (một ký tự sai làm hỏng cả thực thể).",
      "Giữ fp32 cho 12 lớp output/dense + classifier → F1 0,916 so với fp32.",
      "Giả thuyết (chưa kiểm): ngoại lai kích hoạt ở FFN; CPU i9-9880H không có VNNI có thể cho kết quả khác VPS.",
    ],
    gap: "Giải thích mới là giả thuyết; chưa đo trên VPS.",
  },

  // ── Trục 5 ──
  {
    id: "a1",
    axis: "application",
    question: "Rào cản khi đưa vào sử dụng thật?",
    answer: [
      "VPS chỉ có CPU; mô hình chữ Hán fp32 cần ~434 MB.",
      "Chữ Hán chưa có RE và chưa có chuẩn vàng quan hệ (có 4.171 quan hệ nhãn máy trên 1.162 trang, chưa soát).",
      "Khâu OCR chưa tổng hợp số đo cùng thước đo nên chưa đưa vào đánh giá đầu–cuối.",
    ],
    gap: "Chưa đo độ trễ, RAM trên VPS; chưa có đánh giá đầu–cuối (RQ5).",
  },
  {
    id: "a2",
    axis: "application",
    question: "Bước tiếp theo tự nhiên là gì?",
    answer: [
      "A: RQ1 — kiểm định ghép cặp, phân tích lỗi, PhoBERT tách từ VnCoreNLP, đường học; song song soát 15 trang chữ Hán (293 thực thể).",
      "B: RQ4 — khung cây từ bố cục, rồi mô hình chọn cha/mẹ học từ phả hệ.",
      "C: RQ2, RQ3 — tri thức miền, lọc nhãn nhiễu, chiếu nhãn qua 22.602 cặp câu song ngữ.",
      "D: RQ5 — đánh giá đầu–cuối.",
    ],
  },
  {
    id: "a3",
    axis: "application",
    question: "Với ảnh Hán Nôm, cây gia phả sẽ dựng thế nào?",
    answer: [
      "Quan hệ nằm ở bố cục, nên với ảnh có thể phải dựng cây từ bố cục trang (khung chữ OCR), không từ câu.",
      "Đây là hướng mở rộng tự nhiên của RQ4.",
    ],
    gap: "Chưa làm; chỉ là hướng phát triển.",
  },
];

export interface MockQuestion {
  id: string;
  axis: AxisId;
  question: string;
  /** Các ý câu trả lời cần có. */
  mustHave: string[];
  /** Câu trả lời dễ mất điểm. */
  trap: string;
  model: string;
}

export const MOCK_QUESTIONS: MockQuestion[] = [
  {
    id: "q1",
    axis: "method",
    question: "Em chỉ fine-tune mô hình có sẵn. Đóng góp khoa học của luận văn nằm ở đâu?",
    mustHave: [
      "Thừa nhận 19 phương pháp đã thử đều là áp dụng cái có sẵn",
      "10/19 kết quả âm hoặc không khác biệt, và chúng chỉ ra nút thắt thật",
      "Đóng góp chính đề xuất: RE dựa trên bố cục + giám sát xa (RQ4)",
      "Tài nguyên tự xây: chuẩn vàng mức cây 1.524 quan hệ, bộ chấm có cổng chống tụt",
    ],
    trap: "Nói 'XLM-R đạt 0,615 là đóng góp' — đó là baseline.",
    model:
      "Dạ, em xin thừa nhận phần tinh chỉnh chỉ là mốc so sánh. Đến nay em đã thử 19 phương pháp, tất cả là áp dụng cái có sẵn, và 10 phương pháp cho kết quả âm hoặc không khác biệt. Chính các kết quả này cho thấy nút thắt nằm ở quan hệ: 28/30 quan hệ vắt qua dòng nên mọi luật mức câu gần bằng 0. Vì vậy đóng góp chính em đề xuất là RE dựa trên bố cục gia phả, học bằng giám sát xa từ 342 cây phả hệ, chấm trên chuẩn vàng mức cây 1.524 quan hệ do em xây.",
  },
  {
    id: "q2",
    axis: "experiment",
    question: "SikuBERT đạt 0,715. Vậy mô hình nhận dạng đúng khoảng 71,5% thực thể chữ Hán?",
    mustHave: [
      "0,715 đo so với nhãn máy Gemini, chưa trang nào người soát",
      "Chỉ đo mức tái tạo nhãn máy, không phải độ chính xác thật",
      "Test chỉ 38 câu, CI95 0,649–0,780",
      "Ở tiếng Việt, nhãn tự động chỉ khớp nhãn người F1 0,40 → độ chính xác thật có thể thấp hơn nhiều",
      "Kế hoạch: soát 15 trang (293 thực thể) rồi chấm lại",
    ],
    trap: "Đồng ý 'đúng 71,5%', hoặc nhầm F1 với accuracy.",
    model:
      "Dạ không ạ. 0,715 là F1 so với nhãn máy Gemini trên 38 câu (CI95 0,649–0,780), nên chỉ cho biết mô hình tái tạo nhãn máy tốt đến đâu. Ở tiếng Việt, nhãn tự động chỉ khớp nhãn người F1 0,40, nên độ chính xác thật có thể thấp hơn nhiều. Em đang chờ soát 15 trang, 293 thực thể, để có số đo thật.",
  },
  {
    id: "q3",
    axis: "experiment",
    question: "XLM-R hơn PhoBERT 0,077. Chênh lệch này có ý nghĩa thống kê không?",
    mustHave: [
      "Chưa kiểm định ghép cặp — thừa nhận",
      "Dao động giữa các lần chạy ~0,02 (0,615 so với 0,594)",
      "Mỗi lượt chỉ 5 cây; phương sai giữa lượt lớn",
      "Bản cuối cùng chiều (0,706 so với 0,633) nhưng dev 43 thực thể, chênh ≈ 3 thực thể",
      "Kế hoạch: bootstrap ghép cặp, t-test theo lượt (RQ1)",
    ],
    trap: "Khẳng định 'XLM-R tốt hơn rõ rệt' khi chưa kiểm định.",
    model:
      "Dạ, em chưa kiểm định ghép cặp nên chưa dám kết luận. Chênh 0,077 lớn hơn dao động lần chạy em đo được (~0,02) và bản cuối cũng cùng chiều, nhưng mỗi lượt chỉ 5 cây và dev bản cuối chỉ 43 thực thể. Kiểm định ghép cặp trên cùng 5 lượt là việc đầu tiên trong RQ1 và không tốn GPU.",
  },
  {
    id: "q4",
    axis: "experiment",
    question: "Ai gán 25 cây nhãn người? Độ đồng thuận giữa người gán là bao nhiêu?",
    mustHave: [
      "Chưa đo kappa — thừa nhận",
      "25 cây, 692 thực thể, 30 quan hệ, gán trên Label Studio từ nhãn gợi ý",
      "Hiệu ứng neo: người chỉ thêm, không xoá nhãn gợi ý",
      "Kế hoạch: người thứ hai gán độc lập một mẫu, tính Cohen kappa",
    ],
    trap: "Lảng tránh hoặc nói 'nhãn người thì đúng'.",
    model:
      "Dạ, đây là điểm yếu em xin nhận: em chưa đo độ đồng thuận. 25 cây (692 thực thể, 30 quan hệ) được gán trên Label Studio từ nhãn gợi ý, và em quan sát thấy hiệu ứng neo: người chỉ thêm chứ không xoá nhãn gợi ý. Em sẽ cho một người thứ hai gán độc lập một mẫu để tính Cohen kappa, từ đó biết trần chất lượng của chính chuẩn vàng.",
  },
  {
    id: "q5",
    axis: "method",
    question: "Sao không dùng luôn LLM để trích quan hệ cho nhanh?",
    mustHave: [
      "98,6% offset Gemini sai; chỉ gán 2.000 ký tự đầu",
      "Nhãn bán tự động khớp nhãn người chỉ F1 0,40",
      "Gemini tự rà chỉ bác 5% (đồng thuận vòng tròn)",
      "Tốn tiền, khó giải thích; giữ LLM làm baseline",
    ],
    trap: "Nói 'LLM không tốt' mà không có số.",
    model:
      "Dạ, em đã dùng Gemini ở khâu tạo nhãn và đo được: tên đúng nhưng 98,6% vị trí sai, chỉ gán 2.000 ký tự đầu; nhãn bán tự động chỉ khớp nhãn người F1 0,40; Gemini tự rà nhãn của mình chỉ bác 5%. Vì vậy em giữ LLM làm baseline, còn phương pháp chính phải giải thích được và chạy được trên CPU.",
  },
  {
    id: "q6",
    axis: "limits",
    question: "Chuẩn vàng mức cây lấy từ phả hệ dựng bằng luật. Như vậy có vòng tròn không?",
    mustHave: [
      "pha_he dựng bằng luật generation_stack, confidence 0,65, chưa người soát",
      "Nhãn người khớp gold mức cây chỉ F1 0,472; 13/30 quan hệ người không có trong cấu trúc",
      "Đã tự đánh dấu vòng tròn: gold_builder dùng pha_he nên 0,286 không dùng để so",
      "Gần như chỉ cha–con (1.512/1.524)",
    ],
    trap: "Coi gold mức cây là sự thật tuyệt đối.",
    model:
      "Dạ có rủi ro đó và em đã ghi nhận. Phả hệ dựng bằng luật, confidence 0,65, chưa người soát; nhãn người chỉ khớp nó F1 0,472. Với hệ thống nào đã dùng pha_he (như gold_builder, 0,286), em đánh dấu vòng tròn và không dùng để so. Gold mức cây là thước đo lớn và rẻ cho cha–con, còn MOTHER_OF, SPOUSE vẫn phải dựa vào nhãn người.",
  },
  {
    id: "q7",
    axis: "experiment",
    question: "Thêm 103 cây dữ liệu mà không tăng. Vậy dữ liệu bán tự động là vô ích?",
    mustHave: [
      "0,595 so với 0,594, t = −0,36: không khác biệt ở F1 gộp",
      "Theo loại: PER_NAME +0,143, DATE +0,067, LOC −0,088 (gợi ý)",
      "Nhãn bán tự động chỉ khớp người 0,40: nhiễu là giả thuyết chính (H3a)",
      "Hướng: lọc theo độ tin cậy thay vì trộn thô",
    ],
    trap: "Kết luận 'vô ích' hoặc 'có ích' khi chưa kiểm định theo loại.",
    model:
      "Dạ, ở F1 gộp thì không khác biệt (0,595 so với 0,594, t = −0,36). Nhưng theo loại có dấu hiệu đánh đổi: PER_NAME tăng 0,143 trong khi LOC giảm 0,088. Em giả thuyết trộn thô thất bại vì nhiễu nhãn, nên RQ3 sẽ thử lọc theo độ tin cậy và chấm trên nhãn người.",
  },
  {
    id: "q8",
    axis: "application",
    question: "Hệ thống chạy trên server thật thì độ trễ, bộ nhớ ra sao?",
    mustHave: [
      "Chưa đo trên VPS — thừa nhận",
      "Số đã có: API chữ Hán fp32 trung vị 111 ms, p95 125 ms (Mac i9)",
      "Kích thước: SikuBERT fp32 434 MB; XLM-R int8 278 MB",
      "Vì sao chữ Hán dùng fp32: int8 chỉ F1 0,769 so với fp32",
    ],
    trap: "Đưa số đo trên Mac như số của server.",
    model:
      "Dạ, em chưa đo trên VPS. Trên máy Mac i9, API chữ Hán bản fp32 có trễ trung vị 111 ms, p95 125 ms mỗi request; mô hình 434 MB. Em chọn fp32 vì bản int8 chỉ đạt F1 0,769 so với fp32. Đo lại trên VPS là việc cần làm trước khi bảo vệ.",
  },
  {
    id: "q9",
    axis: "motivation",
    question: "Tại sao không làm RE mức câu như các bài báo RE phổ biến?",
    mustHave: [
      "28/30 quan hệ nhãn người vắt qua dòng (trung vị 132 ký tự)",
      "Trần lý thuyết RE mức câu: 2/30",
      "Luật mức câu 0/30; gán quan hệ như NER F1 = 0",
      "Phả ký viết dạng danh sách: cha một dòng, các con các dòng sau",
    ],
    trap: "Trả lời theo cảm nhận mà không đưa số 28/30.",
    model:
      "Dạ, vì em đo được 28/30 quan hệ nhãn người vắt qua nhiều dòng, khoảng cách trung vị 132 ký tự. Phả ký viết dạng danh sách: cha một dòng, các con các dòng sau. Nên mọi RE trong phạm vi một câu có trần 2/30, và thực tế luật mức câu được 0/30.",
  },
];

export interface QuizItem {
  id: string;
  question: string;
  options: string[];
  answer: number;
  explain: string;
}

export const QUIZ: QuizItem[] = [
  { id: "z1", question: "XLM-R, kiểm chéo 5 lượt theo cây trên 25 cây nhãn người: F1 gộp?", options: ["0,538", "0,615", "0,706", "0,658"], answer: 1, explain: "0,615 (chạy lại 0,594). 0,538 là PhoBERT; 0,706 là dev bản cuối; 0,658 là SikuBERT trên nhãn máy." },
  { id: "z2", question: "PhoBERT, cùng thiết lập kiểm chéo: F1?", options: ["0,538", "0,633", "0,516", "0,594"], answer: 0, explain: "0,538. 0,633 là phobert-family trên dev 43 thực thể; 0,516 là PhoBERT trên nhãn máy." },
  { id: "z3", question: "Có bao nhiêu cây nhãn người cho NER tiếng Việt?", options: ["139", "103", "25", "342"], answer: 2, explain: "25 cây (692 thực thể, 30 quan hệ). 114 cây còn lại là bán tự động; 342 là số cây VGP." },
  { id: "z4", question: "Nhãn bán tự động khớp nhãn người với F1 bao nhiêu?", options: ["0,40", "0,47", "0,29", "0,62"], answer: 0, explain: "0,400 (P 0,359, R 0,451). 0,472 là nhãn người khớp gold mức cây." },
  { id: "z5", question: "Tỉ lệ offset Gemini trả về bị sai?", options: ["60%", "87%", "98,6%", "5%"], answer: 2, explain: "98,6%. 60% là phần văn bản không có nhãn; 87% là khối lượng soát giảm nhờ lọc; 5% là tỉ lệ Gemini tự bác." },
  { id: "z6", question: "Bao nhiêu trong 30 quan hệ nhãn người vắt qua nhiều dòng?", options: ["13", "28", "2", "30"], answer: 1, explain: "28/30, khoảng cách trung vị 132 ký tự. Trần RE mức câu là 2/30." },
  { id: "z7", question: "Luật RE mức tài liệu v2 trên chuẩn vàng mức cây: F1?", options: ["0,287", "0,211", "0,000", "0,015"], answer: 3, explain: "0,015. 0,211 là trên dev 114 cây tự động; trên 25 cây người là 0,000." },
  { id: "z8", question: "Chuẩn vàng mức cây có bao nhiêu quan hệ neo văn bản?", options: ["1.524", "72.484", "895", "4.171"], answer: 0, explain: "1.524 (FATHER_OF 1.512). 72.484 là toàn bộ quan hệ suy từ 342 cây; 4.171 là quan hệ nhãn máy chữ Hán." },
  { id: "z9", question: "SikuBERT int8 (QInt8 mặc định): F1 thực thể so với bản fp32?", options: ["0,99", "0,916", "0,769", "0,352"], answer: 2, explain: "0,769. 0,916 là khi giữ fp32 cho FFN-out + classifier; 0,99 là XLM-R Việt." },
  { id: "z10", question: "SikuBERT kiểm chéo 5 lượt theo sách (nhãn máy): F1?", options: ["0,715", "0,658", "0,627", "0,232"], answer: 1, explain: "0,658. 0,715 là bản cuối trên 15 trang; 0,627 là dev bản cuối; 0,232 là từ điển." },
  { id: "z11", question: "Hai giai đoạn (+103 cây bán tự động) so với chỉ nhãn người: t bằng?", options: ["1,71", "10,8", "−1,26", "−0,36"], answer: 3, explain: "t = −0,36 (df = 4): 0,595 so với 0,594, không khác biệt." },
  { id: "z12", question: "Dao động F1 giữa các lần chạy cùng cấu hình khoảng?", options: ["0,002", "0,02", "0,08", "0,2"], answer: 1, explain: "~0,02 (0,615 so với 0,594). Chênh nhỏ hơn ~0,03 không nên diễn giải." },
  { id: "z13", question: "Đề tài đã thử bao nhiêu phương pháp (đến 28/10)?", options: ["5", "10", "19", "25"], answer: 2, explain: "19 phương pháp ở 5 khâu; 10 phương pháp cho kết quả âm, không khác biệt hoặc chưa kết luận." },
  { id: "z14", question: "Tách từ pyvi cho PhoBERT trên nhãn máy thay đổi F1 bao nhiêu?", options: ["+0,028", "−0,023", "+0,077", "0"], answer: 1, explain: "−0,023 (0,516 → 0,493, t = −1,26). +0,028 là PhoBERT hơn mBERT." },
  { id: "z15", question: "xlmr-family bản cuối đạt 0,706 trên tập nào?", options: ["Test 98 cây", "CV5 25 cây", "Dev 3 cây, 43 thực thể", "Test 15 trang"], answer: 2, explain: "Dev 3 cây, 43 thực thể, cũng dùng chọn epoch → lạc quan, không có test riêng." },
  { id: "z16", question: "Baseline từ điển chữ Hán, CV5 theo sách: F1?", options: ["0,444", "0,231", "0,232", "0,173"], answer: 2, explain: "0,232. 0,444 là trên han_final/test 38 câu; 0,231 là từ điển tiếng Việt." },
  { id: "z17", question: "Bộ sửa bảng mã cũ sửa được bao nhiêu cây?", options: ["18/23", "23/342", "319/342", "5/23"], answer: 0, explain: "18/23 cây. 23/342 là số cây dùng bảng mã cũ; 319 là con số đo sai ban đầu đã đính chính." },
  { id: "z18", question: "API chữ Hán fp32: độ trễ trung vị mỗi request (máy Mac i9)?", options: ["30 ms", "111 ms", "2,0 s", "48 ms"], answer: 1, explain: "111 ms (p95 125 ms). 2,0 s là request đầu do nạp mô hình. Chưa đo trên VPS." },
];

export interface ErrorStatement {
  id: string;
  statement: string;
  correct: boolean;
  explain: string;
}

export const ERROR_STATEMENTS: ErrorStatement[] = [
  { id: "s1", statement: "SikuBERT đạt F1 0,715 nên nhận dạng đúng khoảng 71,5% thực thể chữ Hán.", correct: false, explain: "0,715 đo so với nhãn máy Gemini, không phải nhãn người; và F1 không phải tỉ lệ đúng." },
  { id: "s2", statement: "XLM-R tốt hơn PhoBERT một cách có ý nghĩa thống kê (0,615 so với 0,538).", correct: false, explain: "Chưa kiểm định ghép cặp. Chênh cùng chiều ở bản cuối, nhưng dao động lần chạy ~0,02 và mỗi lượt chỉ 5 cây." },
  { id: "s3", statement: "Thêm 103 cây nhãn bán tự động giúp XLM-R tăng từ 0,594 lên 0,595.", correct: false, explain: "Chênh theo lượt −0,014 ± 0,087, t = −0,36: không khác biệt, không được gọi là 'tăng'." },
  { id: "s4", statement: "Mô hình tiếng Việt đang chạy chỉ đạt F1 0,268.", correct: false, explain: "0,268 đo với nhãn bán tự động (chỉ khớp người 0,40); kết luận này đã bị rút lại." },
  { id: "s5", statement: "28/30 quan hệ nhãn người vắt qua nhiều dòng, nên RE trong phạm vi một câu tối đa chỉ bắt được 2/30.", correct: true, explain: "Đúng. Đây là bằng chứng chính cho RQ4." },
  { id: "s6", statement: "Lượng tử hoá int8 an toàn cho mọi mô hình vì XLM-R vẫn khớp 99%.", correct: false, explain: "SikuBERT int8 chỉ F1 0,769 so với fp32; per-channel QInt8 ra 0 thực thể. Chữ Hán dùng fp32." },
  { id: "s7", statement: "Bản cuối xlmr-family đạt 0,706 trên tập kiểm tra.", correct: false, explain: "0,706 là trên dev 3 cây (43 thực thể), cũng dùng chọn epoch; chưa có test riêng." },
  { id: "s8", statement: "Dữ liệu được chia theo cây (tiếng Việt) và theo sách (chữ Hán) để tránh rò rỉ giữa huấn luyện và kiểm tra.", correct: true, explain: "Đúng. Văn bản cùng gia phả không rơi vào cả hai phía." },
  { id: "s9", statement: "Tách từ không giúp PhoBERT, vậy giả thuyết H1a đã bị bác.", correct: false, explain: "Mới thử pyvi trên nhãn máy (−0,023). Chưa thử VnCoreNLP (bộ PhoBERT dùng) và chưa thử trên nhãn người: giả thuyết yếu đi, chưa bị bác." },
  { id: "s10", statement: "Chuẩn vàng mức cây có 1.524 quan hệ, đủ để đánh giá FATHER_OF, MOTHER_OF và SPOUSE.", correct: false, explain: "FATHER_OF 1.512, MOTHER_OF 10, SPOUSE 2: gần như chỉ đo được cha–con." },
  { id: "s11", statement: "Nhãn bán tự động có recall quan hệ 0,93 nên là nguồn RE tốt.", correct: false, explain: "Precision chỉ 0,17 (28 đúng, 137 thừa), F1 0,287." },
  { id: "s12", statement: "SikuBERT hơn từ điển 0,446 F1 mỗi lượt (t = 10,8), chứng tỏ mô hình học được quy luật nhất quán của nhãn máy.", correct: true, explain: "Đúng, với điều kiện nói rõ: 'của nhãn máy', không chứng minh mô hình đúng với người." },
];

export interface GlossaryTerm {
  id: string;
  group: string;
  term: string;
  /** Giải thích bằng lời thường, không cần nền tảng chuyên ngành. */
  meaning: string;
  /** Gắn với số liệu/việc cụ thể của đề tài. */
  inThesis?: string;
  /** Câu hội đồng hay hỏi lại về khái niệm này. */
  remember?: string;
}

export const GLOSSARY_GROUPS = [
  "Bài toán",
  "Mô hình",
  "Huấn luyện",
  "Đánh giá",
  "Thống kê",
  "Dữ liệu và nhãn",
  "Triển khai",
] as const;

export const GLOSSARY: GlossaryTerm[] = [
  // ── Bài toán ──
  {
    id: "g-ner",
    group: "Bài toán",
    term: "NER (Named Entity Recognition) — nhận dạng thực thể",
    meaning: "Tìm trong văn bản những đoạn chữ là tên riêng hay thông tin có loại (tên người, địa danh, ngày tháng…) và cho biết mỗi đoạn thuộc loại nào.",
    inThesis: "5 loại: PER_NAME (tên người), LOC (địa danh), DATE (thời gian), ORDER (thứ bậc: trưởng, thứ…), GENERATION (đời thứ n).",
  },
  {
    id: "g-re",
    group: "Bài toán",
    term: "RE (Relation Extraction) — trích xuất quan hệ",
    meaning: "Sau khi có các thực thể, xác định giữa hai thực thể có quan hệ gì. Kết quả là các bộ ba (A, quan hệ, B).",
    inThesis: "3 quan hệ: FATHER_OF, MOTHER_OF, SPOUSE, luôn giữa hai PER_NAME. Ví dụ (Hoàng Húy Tức, FATHER_OF, Hoàng Văn Ánh).",
  },
  {
    id: "g-bio",
    group: "Bài toán",
    term: "Gán nhãn chuỗi, nhãn BIO",
    meaning: "Cách biến NER thành bài toán gán nhãn từng token: B- là token bắt đầu thực thể, I- là token nằm bên trong, O là ngoài thực thể.",
    inThesis: "'Vũ Xuân Cường' → B-PER_NAME, I-PER_NAME, I-PER_NAME. Nếu mô hình chỉ gán B cho 'Vũ' thì sai ranh giới.",
  },
  {
    id: "g-offset",
    group: "Bài toán",
    term: "Offset (vị trí ký tự)",
    meaning: "Số thứ tự ký tự bắt đầu và kết thúc của một thực thể trong văn bản. Bộ chấm so khớp theo offset, nên offset sai thì coi như sai dù tên đúng.",
    inThesis: "Gemini trả tên đúng nhưng 98,6% offset sai → phải tự khớp lại bằng chuỗi.",
  },
  {
    id: "g-coref",
    group: "Bài toán",
    term: "Đồng tham chiếu (coreference)",
    meaning: "Hai cách gọi khác nhau cùng chỉ một người, ví dụ 'ông Thuỷ tổ' và tên thật của ông.",
    inThesis: "Một lý do luật RE thất bại: 'con Doãn Khuê' nằm cách tên Doãn Khuê 38 dòng.",
  },
  {
    id: "g-distant",
    group: "Bài toán",
    term: "Giám sát xa (distant supervision)",
    meaning: "Không gán nhãn tay, mà lấy nhãn tự động từ một nguồn tri thức có sẵn rồi gắn vào văn bản. Rẻ, nhiều, nhưng có nhiễu.",
    inThesis: "Lấy quan hệ từ cây phả hệ VGP rồi tìm hai tên trong Phả ký → 1.524 quan hệ neo văn bản. Đây là nền của RQ4.",
  },

  // ── Mô hình ──
  {
    id: "g-transformer",
    group: "Mô hình",
    term: "Transformer, BERT",
    meaning: "Kiến trúc mạng nơ-ron đọc cả câu cùng lúc và cho mỗi từ 'nhìn' các từ khác (cơ chế attention). BERT là một mô hình Transformer được huấn luyện trước trên rất nhiều văn bản để hiểu ngôn ngữ, sau đó đem tinh chỉnh cho việc cụ thể.",
    inThesis: "Mọi mô hình học máy của đề tài (XLM-R, PhoBERT, SikuBERT, mBERT) đều thuộc họ BERT.",
    remember: "Attention có chi phí O(n²) theo độ dài chuỗi, nên văn bản dài phải cắt đoạn (thường ≤ 512 token).",
  },
  {
    id: "g-xlmr",
    group: "Mô hình",
    term: "XLM-R (XLM-RoBERTa)",
    meaning: "Mô hình BERT đa ngữ của Facebook/Meta, huấn luyện trước trên văn bản của khoảng 100 ngôn ngữ (có tiếng Việt). Không cần tách từ trước khi đưa vào.",
    inThesis: "Mô hình chính cho tiếng Việt (xlmr-family): CV5 0,615; dev bản cuối 0,706; int8 khớp 99%.",
    remember: "Vì sao đa ngữ lại hơn PhoBERT? Chưa giải thích được; một giả thuyết là dữ liệu chưa tách từ theo cách PhoBERT cần (H1a).",
  },
  {
    id: "g-phobert",
    group: "Mô hình",
    term: "PhoBERT",
    meaning: "Mô hình BERT đơn ngữ tiếng Việt của VinAI. Được huấn luyện trước trên văn bản đã tách từ (ví dụ 'gia_phả'), nên lý thuyết cần đầu vào cũng được tách từ.",
    inThesis: "Mô hình đối chứng: CV5 0,538; dev 0,633. Tách từ bằng pyvi không giúp (−0,023).",
  },
  {
    id: "g-sikubert",
    group: "Mô hình",
    term: "SikuBERT",
    meaning: "Mô hình BERT huấn luyện trước trên Tứ khố toàn thư (văn ngôn cổ Trung Hoa), làm việc ở mức từng chữ Hán nên không cần tách từ.",
    inThesis: "Mô hình cho chữ Hán (sikubert-family): CV5 0,658, bản cuối 0,715 — cả hai đo trên nhãn máy.",
  },
  {
    id: "g-mbert",
    group: "Mô hình",
    term: "mBERT (multilingual BERT)",
    meaning: "Bản BERT đa ngữ đầu tiên của Google, cũ hơn XLM-R.",
    inThesis: "Thử trên nhãn máy: 0,488 ± 0,019 (3 hạt giống).",
  },
  {
    id: "g-llm",
    group: "Mô hình",
    term: "LLM (mô hình ngôn ngữ lớn), Gemini",
    meaning: "Mô hình rất lớn sinh văn bản theo yêu cầu (prompt). Dùng được ngay không cần huấn luyện, nhưng tốn tiền mỗi lần gọi và khó kiểm soát vị trí, định dạng đầu ra.",
    inThesis: "Gemini dùng để tạo nhãn máy; offset sai 98,6%. Giữ làm baseline, không làm phương pháp chính.",
  },
  {
    id: "g-dict",
    group: "Mô hình",
    term: "Baseline từ điển",
    meaning: "Cách đơn giản nhất: có danh sách tên đã biết, thấy chuỗi trùng thì gán nhãn. Không học gì. Dùng làm mức sàn.",
    inThesis: "Chữ Hán CV5 0,232; tiếng Việt dev 0,231. Mô hình học phải vượt mức này mới có giá trị.",
  },

  // ── Huấn luyện ──
  {
    id: "g-pretrain",
    group: "Huấn luyện",
    term: "Huấn luyện trước (pre-training) và tinh chỉnh (fine-tuning)",
    meaning: "Huấn luyện trước: mô hình học ngôn ngữ chung trên kho văn bản khổng lồ (người khác đã làm). Tinh chỉnh: lấy mô hình đó, huấn luyện tiếp một ít trên dữ liệu có nhãn của mình cho việc cụ thể (ở đây là NER).",
    inThesis: "Thầy nhắc: fine-tune chỉ là baseline, không phải đóng góp.",
  },
  {
    id: "g-baseline",
    group: "Huấn luyện",
    term: "Baseline (mốc so sánh)",
    meaning: "Phương pháp chuẩn/đơn giản dùng để so. Phương pháp mới chỉ có ý nghĩa khi hơn baseline một cách có kiểm định.",
    inThesis: "Từ điển là sàn; XLM-R/PhoBERT/SikuBERT tinh chỉnh chuẩn là baseline cho phương pháp đề xuất.",
  },
  {
    id: "g-epoch",
    group: "Huấn luyện",
    term: "Epoch, siêu tham số (hyperparameter), learning rate",
    meaning: "Epoch: một lượt mô hình học hết dữ liệu huấn luyện. Siêu tham số: các thông số người chọn trước khi huấn luyện (số epoch, tốc độ học lr…), không do mô hình tự học.",
    inThesis: "phobert-family: 20 epoch, lr 5e-5, epoch tốt nhất 11; xlmr-family epoch 17; SikuBERT 6 epoch.",
  },
  {
    id: "g-seed",
    group: "Huấn luyện",
    term: "Hạt giống ngẫu nhiên (seed)",
    meaning: "Con số khởi tạo ngẫu nhiên. Cùng dữ liệu, khác seed vẫn cho kết quả hơi khác, nên phải chạy nhiều seed để biết dao động.",
    inThesis: "Dao động đo được ~0,02 F1 (0,615 so với 0,594). Chênh nhỏ hơn mức này không được diễn giải.",
  },
  {
    id: "g-twostage",
    group: "Huấn luyện",
    term: "Huấn luyện hai giai đoạn",
    meaning: "Giai đoạn 1 học trên nhiều dữ liệu nhãn nhiễu; giai đoạn 2 tinh chỉnh tiếp trên ít dữ liệu nhãn tốt.",
    inThesis: "+103 cây bán tự động: 0,595 so với 0,594, t = −0,36 → không khác biệt.",
  },
  {
    id: "g-domain",
    group: "Huấn luyện",
    term: "Thích nghi miền (domain adaptation)",
    meaning: "Cho mô hình học thêm văn bản của đúng lĩnh vực mình (chưa cần nhãn) trước khi tinh chỉnh, để quen cách viết đặc thù.",
    inThesis: "Đề xuất RQ2(a): học tiếp trên văn bản gia phả chưa gán nhãn. Chưa làm.",
  },
  {
    id: "g-tokenize",
    group: "Huấn luyện",
    term: "Tách từ (word segmentation), token",
    meaning: "Tiếng Việt viết cách theo âm tiết, nên 'gia phả' là 2 âm tiết nhưng 1 từ. Tách từ là nối chúng lại ('gia_phả'). Token là đơn vị nhỏ mà mô hình đọc.",
    inThesis: "Dữ liệu chưa tách từ (0 token có dấu '_'). Đã thử pyvi; chưa thử VnCoreNLP (bộ PhoBERT dùng).",
  },

  // ── Đánh giá ──
  {
    id: "g-prf",
    group: "Đánh giá",
    term: "Precision (P), Recall (R)",
    meaning: "Precision = trong các thực thể mô hình đưa ra, bao nhiêu phần đúng. Recall = trong các thực thể thật, mô hình tìm được bao nhiêu phần. Đúng = khớp cả ranh giới lẫn loại.",
    inThesis: "XLM-R CV5: tp 442 (đúng), fp 303 (thừa), fn 250 (sót). P = 442/(442+303) = 0,593; R = 442/(442+250) = 0,639.",
    remember: "P cao, R thấp: ít nói sai nhưng bỏ sót nhiều. P thấp, R cao: tìm nhiều nhưng thừa nhiều (như nhãn bán tự động RE: R 0,93, P 0,17).",
  },
  {
    id: "g-f1",
    group: "Đánh giá",
    term: "F1",
    meaning: "Trung bình điều hoà của P và R: F1 = 2·P·R / (P + R), từ 0 đến 1. Chỉ cao khi cả P và R đều cao. Đây là thước đo chính của NER/RE.",
    inThesis: "XLM-R: 2 × 0,593 × 0,639 / (0,593 + 0,639) = 0,615.",
    remember: "F1 không phải 'tỉ lệ đúng' (accuracy). F1 0,715 không có nghĩa là 71,5% thực thể đúng.",
  },
  {
    id: "g-micro",
    group: "Đánh giá",
    term: "F1 gộp (micro) và F1 theo loại",
    meaning: "F1 gộp: cộng tp/fp/fn của mọi loại thực thể rồi tính một F1. F1 theo loại: tính riêng cho từng loại để thấy loại nào yếu.",
    inThesis: "PER_NAME yếu nhất (0,36–0,41), DATE tốt nhất (0,78–0,79) ở XLM-R.",
  },
  {
    id: "g-split",
    group: "Đánh giá",
    term: "Tập huấn luyện / dev / test",
    meaning: "Train: để mô hình học. Dev (validation): để chọn siêu tham số, epoch. Test: chỉ dùng một lần cuối để báo cáo; nếu dùng test để chọn thì số bị lạc quan.",
    inThesis: "Bản cuối xlmr-family 0,706 là trên dev 43 thực thể, cũng dùng chọn epoch → chưa có test riêng.",
  },
  {
    id: "g-cv",
    group: "Đánh giá",
    term: "Kiểm chéo k lượt (k-fold cross-validation), CV5",
    meaning: "Chia dữ liệu thành k phần; lần lượt lấy 1 phần làm test, k−1 phần làm train; lặp k lần rồi gộp kết quả. Dùng khi dữ liệu ít để mọi mẫu đều được làm test một lần.",
    inThesis: "CV5 theo cây (25 cây → mỗi lượt 5 cây test) cho tiếng Việt; CV5 theo sách (20 sách) cho chữ Hán.",
  },
  {
    id: "g-leak",
    group: "Đánh giá",
    term: "Rò rỉ dữ liệu (data leakage)",
    meaning: "Thông tin của tập test lọt vào lúc huấn luyện hay lúc chọn mô hình, làm số đo đẹp giả.",
    inThesis: "Tránh bằng chia theo cây/sách: văn bản cùng một gia phả không nằm ở cả train và test.",
  },
  {
    id: "g-ablation",
    group: "Đánh giá",
    term: "Ablation (thí nghiệm bóc tách)",
    meaning: "Bỏ từng thành phần của phương pháp rồi đo lại, để chứng minh thành phần nào thật sự có tác dụng.",
    inThesis: "Dự kiến cho RQ2 (4 cấu hình) và RQ4 (chỉ tầng bố cục / chỉ tầng mô hình / cả hai). Chưa làm.",
  },
  {
    id: "g-oracle",
    group: "Đánh giá",
    term: "Oracle, đánh giá đầu–cuối (end-to-end)",
    meaning: "Oracle: thay một bước bằng kết quả đúng tuyệt đối để xem bước đó gây bao nhiêu lỗi. Đầu–cuối: đo cả chuỗi từ văn bản đến cây cuối cùng.",
    inThesis: "RQ5: NER đúng + RE dự đoán, và ngược lại. Chưa làm.",
  },

  // ── Thống kê ──
  {
    id: "g-ttest",
    group: "Thống kê",
    term: "Kiểm định t (t-test), bậc tự do (df)",
    meaning: "Kiểm tra xem chênh lệch giữa hai hệ thống có lớn hơn mức dao động ngẫu nhiên không. |t| càng lớn càng chắc là khác thật. df = số lượt − 1.",
    inThesis: "SikuBERT so với từ điển t = 10,8 (khác chắc chắn). Hai giai đoạn t = −0,36 (không khác). df = 4 vì 5 lượt.",
  },
  {
    id: "g-paired",
    group: "Thống kê",
    term: "Kiểm định ghép cặp (paired test)",
    meaning: "So hai hệ thống trên cùng từng lượt/từng mẫu rồi xét hiệu số, nên loại được chênh lệch do lượt dễ/khó. Mạnh hơn so hai con số trung bình.",
    inThesis: "Chưa làm cho XLM-R và PhoBERT — điểm yếu cần làm trước khi bảo vệ.",
  },
  {
    id: "g-pvalue",
    group: "Thống kê",
    term: "p-value, ý nghĩa thống kê",
    meaning: "Xác suất thấy chênh lệch lớn như vậy nếu thật ra hai hệ thống như nhau. Thường p < 0,05 thì gọi là có ý nghĩa thống kê.",
    remember: "Đề tài hiện báo t và df, chưa ghi p-value; nên chuẩn bị quy đổi sẵn.",
  },
  {
    id: "g-bootstrap",
    group: "Thống kê",
    term: "Khoảng tin cậy bootstrap (CI95)",
    meaning: "Lấy mẫu lại có hoàn lại từ tập test rất nhiều lần, tính F1 mỗi lần; khoảng chứa 95% kết quả là CI95. Khoảng rộng = tập test nhỏ, số kém chắc chắn.",
    inThesis: "sikubert-family 0,715 (CI95 0,649–0,780) trên 38 câu; từ điển Việt 0,231 (CI 0,07–0,42).",
  },
  {
    id: "g-kappa",
    group: "Thống kê",
    term: "Cohen's kappa, Fleiss' kappa",
    meaning: "Đo mức đồng ý giữa những người gán nhãn, đã trừ phần đồng ý do may rủi. Cohen cho 2 người, Fleiss cho từ 3 người. Gần 1 = rất đồng ý; khoảng 0,6–0,8 thường coi là tốt.",
    inThesis: "Chưa đo — chưa có người gán thứ hai. Đây là câu hội đồng rất hay hỏi.",
  },

  // ── Dữ liệu và nhãn ──
  {
    id: "g-gold",
    group: "Dữ liệu và nhãn",
    term: "Chuẩn vàng (gold standard)",
    meaning: "Bộ nhãn được coi là đúng để chấm điểm hệ thống. Thường do người gán và soát.",
    inThesis: "Chuẩn vàng tin được nhất: 25 cây nhãn người (692 thực thể, 30 quan hệ).",
  },
  {
    id: "g-labels",
    group: "Dữ liệu và nhãn",
    term: "Nhãn người, nhãn máy, nhãn bán tự động",
    meaning: "Nhãn người: người gán/soát. Nhãn máy: LLM tự gán, chưa ai soát. Bán tự động: kết hợp LLM + luật + phả hệ, chưa soát.",
    inThesis: "Bán tự động chỉ khớp nhãn người F1 0,40. Toàn bộ nhãn chữ Hán là nhãn máy Gemini.",
    remember: "Số đo trên nhãn máy chỉ cho biết mô hình bắt chước nhãn máy tốt đến đâu, không phải độ chính xác thật.",
  },
  {
    id: "g-treegold",
    group: "Dữ liệu và nhãn",
    term: "Chuẩn vàng mức cây",
    meaning: "Chuẩn vàng quan hệ lấy từ cây phả hệ có sẵn thay vì gán tay từng quan hệ trong văn bản.",
    inThesis: "342 cây VGP → 1.524 quan hệ neo văn bản (gấp ~50 lần 30 quan hệ nhãn người), gần như chỉ cha–con.",
  },
  {
    id: "g-anchor",
    group: "Dữ liệu và nhãn",
    term: "Hiệu ứng neo (anchoring)",
    meaning: "Khi người gán nhãn xuất phát từ nhãn gợi ý của máy, họ có xu hướng giữ nguyên gợi ý, làm nhãn người bị kéo theo máy.",
    inThesis: "Quan sát trên 25 cây: người chỉ thêm, không xoá nhãn gợi ý.",
  },
  {
    id: "g-encoding",
    group: "Dữ liệu và nhãn",
    term: "Bảng mã TCVN3, VNI (mojibake)",
    meaning: "Các cách mã hoá chữ Việt cũ trước Unicode. Đọc sai bảng mã sẽ ra chữ lỗi như 'Gia ph¶ hä Hoµng'.",
    inThesis: "23/342 cây dùng bảng mã cũ; sửa được 18/23 bằng bộ chuyển theo từng dòng.",
  },
  {
    id: "g-ocr",
    group: "Dữ liệu và nhãn",
    term: "OCR",
    meaning: "Nhận dạng chữ từ ảnh chụp/scan thành văn bản máy đọc được.",
    inThesis: "Có công cụ Kim Hán Nôm OCR và PaddleOCR, nhưng chưa có số đo cùng thước đo nên chưa đưa vào đánh giá.",
  },

  // ── Triển khai ──
  {
    id: "g-onnx",
    group: "Triển khai",
    term: "ONNX",
    meaning: "Định dạng lưu mô hình dùng chung, chạy nhanh trên CPU bằng ONNX Runtime mà không cần PyTorch.",
    inThesis: "API chạy mô hình ở dạng ONNX trên VPS chỉ có CPU.",
  },
  {
    id: "g-quant",
    group: "Triển khai",
    term: "Lượng tử hoá (quantization), int8, fp32",
    meaning: "fp32: lưu mỗi trọng số bằng số thực 32 bit (bản gốc). int8: nén còn số nguyên 8 bit → nhỏ khoảng 4 lần, chạy nhanh hơn, nhưng có thể mất độ chính xác.",
    inThesis: "XLM-R int8 khớp bản gốc 99%; SikuBERT int8 chỉ F1 0,769 so với fp32 → chữ Hán dùng fp32 (434 MB so với 109 MB).",
  },
  {
    id: "g-latency",
    group: "Triển khai",
    term: "Độ trễ (latency), trung vị, p95",
    meaning: "Thời gian từ lúc gửi yêu cầu đến lúc nhận kết quả. Trung vị: một nửa số yêu cầu nhanh hơn mức này. p95: 95% yêu cầu nhanh hơn mức này (đo trường hợp chậm).",
    inThesis: "API chữ Hán fp32: trung vị 111 ms, p95 125 ms (máy Mac i9, chưa đo trên VPS).",
  },
  {
    id: "g-harness",
    group: "Triển khai",
    term: "Harness đánh giá, cổng chống tụt",
    meaning: "Bộ công cụ chấm tự động mọi phiên bản mô hình theo cùng một cách. Cổng chống tụt báo lỗi nếu phiên bản mới kém hơn phiên bản tốt nhất quá một dung sai.",
    inThesis: "Repo family-tree-harness; dung sai 0,03; chỉ so trong cùng quy trình, cùng tập, cùng loại nhãn.",
  },
];
