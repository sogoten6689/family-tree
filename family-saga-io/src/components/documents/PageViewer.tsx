import { EditOutlined, FileImageOutlined, PictureOutlined, ScanOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Empty, Image, Input, Modal, Pagination, Spin, Tag, Typography } from "antd";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { PipelineStepsPanel, type VoteMeta } from "@/components/documents/PipelineStepsPanel";
import { isVoteMetaV2 } from "@/components/documents/voteMetaV2";
import { BoundingBoxOverlay } from "@/components/documents/BoundingBoxOverlay";
import {
  editScanPage,
  getScanPage,
  listScanPages,
  ocrScanPage,
  replaceScanPageImage,
  type GiaPhaPageDetail,
  type GiaPhaPageView,
} from "@/lib/userWorkspaceApi";

import "./ReaderWorkspace.css";

const { Text, Paragraph } = Typography;

/**
 * Xem từng trang của bộ gia phả: ảnh gốc (link tạm từ MinIO, bấm để phóng to)
 * cạnh chữ Hán / phiên âm / dịch nghĩa của version hiện tại. Chỉ chủ bộ hoặc
 * admin mở được (API trả 404 cho người khác).
 *
 * Nút "Sửa trang" sửa tay chữ Hán / phiên âm / dịch nghĩa của trang đang xem.
 * KHÔNG ghi đè bản gốc: lần sửa đầu server fork 1 version "manual-edit"
 * (`editVersion`), viewer chuyển sang xem version đó; "Về bản gốc" quay lại.
 * Nút "Thay ảnh" đổi ảnh gốc của trang (ảnh cũ vẫn còn trên MinIO); chữ và OCR
 * giữ nguyên nên khung chữ cũ bị ẩn cho tới khi OCR lại.
 * Nút "OCR lại trang" gọi Kim Hán Nôm (TỐN TIỀN, có hộp xác nhận) và ghi kết
 * quả vào version sửa tay như "Sửa trang"; phiên âm/dịch cũ được báo chưa khớp.
 */
export function PageViewer({ scanId }: { scanId: number }) {
  const { t } = useTranslation();
  const [pages, setPages] = useState<GiaPhaPageView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  // Chi tiết (OCR từng engine + vote) tải theo trang — bộ lớn có tới 233 trang.
  const [detail, setDetail] = useState<GiaPhaPageDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const currentNumber = pages[index]?.page_number;
  // Version sửa tay đang xem/sửa (null = version hiện tại của bộ).
  const [editVersion, setEditVersion] = useState<{ id: number; number: number } | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ hannom: "", translit: "", translation: "" });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const viewVersionId = editVersion?.id;
  const fileInput = useRef<HTMLInputElement>(null);
  const [replacing, setReplacing] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);
  // Trang đã đổi ảnh trong phiên này: khung chữ (bbox) của ảnh cũ không còn khớp.
  const [imageReplaced, setImageReplaced] = useState<number[]>([]);
  const [ocrBusy, setOcrBusy] = useState(false);
  const [ocrError, setOcrError] = useState<string | null>(null);
  // Trang vừa OCR lại: phiên âm/dịch nghĩa còn là của chữ cũ.
  const [ocrStale, setOcrStale] = useState<number[]>([]);
  // Tăng để tải lại chi tiết trang (khung chữ mới) khi OCR ghi tại chỗ, version không đổi.
  const [detailNonce, setDetailNonce] = useState(0);

  useEffect(() => {
    if (currentNumber === undefined) return;
    let cancelled = false;
    setDetail(null);
    setDetailError(null);
    (viewVersionId === undefined
      ? getScanPage(scanId, currentNumber)
      : getScanPage(scanId, currentNumber, viewVersionId)
    )
      .then((data) => !cancelled && setDetail(data))
      .catch((err) => !cancelled && setDetailError(err instanceof Error ? err.message : "Không tải được OCR/vote"));
    return () => {
      cancelled = true;
    };
  }, [scanId, currentNumber, viewVersionId, detailNonce]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (viewVersionId === undefined ? listScanPages(scanId) : listScanPages(scanId, viewVersionId))
      .then((data) => {
        if (cancelled) return;
        setPages(data);
        // Đổi version (sửa lần đầu / về bản gốc) giữ nguyên trang đang xem.
        setIndex((prev) => Math.min(prev, Math.max(data.length - 1, 0)));
      })
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Không tải được trang"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [scanId, viewVersionId]);

  const openEdit = (current: GiaPhaPageView) => {
    setDraft({
      hannom: current.hannom_text ?? "",
      translit: current.transliteration_text ?? "",
      translation: current.translation_text ?? "",
    });
    setSaveError(null);
    setEditing(true);
  };

  const onPickImage = async (file: File | undefined, current: GiaPhaPageView) => {
    if (!file) return;
    setReplacing(true);
    setImageError(null);
    try {
      const result = await replaceScanPageImage(scanId, current.page_number, file);
      setPages((prev) =>
        prev.map((p) => (p.page_number === current.page_number ? { ...p, image_url: result.page.image_url } : p)),
      );
      setImageReplaced((prev) => (prev.includes(current.page_number) ? prev : [...prev, current.page_number]));
    } catch (err) {
      setImageError(err instanceof Error ? err.message : "Không thay được ảnh");
    } finally {
      setReplacing(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const runOcr = (current: GiaPhaPageView) => {
    Modal.confirm({
      title: t("pageViewer.ocrConfirmTitle", { defaultValue: "OCR lại trang {{n}}?", n: current.page_number }),
      content: t("pageViewer.ocrConfirmBody", {
        defaultValue:
          "Việc này gọi Kim Hán Nôm và TỐN TIỀN mỗi lần chạy. Kết quả lưu vào bản sửa tay, bản gốc giữ nguyên. Phiên âm và dịch nghĩa của trang sẽ chưa khớp chữ mới.",
      }),
      okText: t("pageViewer.ocrConfirmOk", { defaultValue: "OCR (tốn tiền)" }),
      cancelText: t("pageViewer.cancel", { defaultValue: "Huỷ" }),
      onOk: async () => {
        setOcrBusy(true);
        setOcrError(null);
        try {
          const result = await ocrScanPage(scanId, current.page_number, { versionId: viewVersionId });
          setPages((prev) => prev.map((p) => (p.page_number === current.page_number ? { ...p, ...result.page } : p)));
          setImageReplaced((prev) => prev.filter((n) => n !== current.page_number)); // khung chữ mới khớp ảnh hiện tại
          setOcrStale((prev) =>
            result.downstream_stale
              ? prev.includes(current.page_number)
                ? prev
                : [...prev, current.page_number]
              : prev,
          );
          if (result.forked) {
            setEditVersion({ id: result.version.version_id, number: result.version.version_number });
          } else {
            setDetailNonce((n) => n + 1);
          }
        } catch (err) {
          setOcrError(err instanceof Error ? err.message : "Không OCR được");
        } finally {
          setOcrBusy(false);
        }
      },
    });
  };

  const saveEdit = async (current: GiaPhaPageView) => {
    // Chỉ gửi trường đã đổi; so với null coi như "" để không tạo version vì khác biệt rỗng.
    const payload: Parameters<typeof editScanPage>[2] = { version_id: viewVersionId };
    if (draft.hannom !== (current.hannom_text ?? "")) payload.hannom_text = draft.hannom;
    if (draft.translit !== (current.transliteration_text ?? "")) payload.transliteration_text = draft.translit;
    if (draft.translation !== (current.translation_text ?? "")) payload.translation_text = draft.translation;
    if (!("hannom_text" in payload || "transliteration_text" in payload || "translation_text" in payload)) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const result = await editScanPage(scanId, current.page_number, payload);
      setPages((prev) => prev.map((p) => (p.page_number === current.page_number ? { ...p, ...result.page } : p)));
      setDetail((prev) => (prev?.page_number === current.page_number ? { ...prev, ...result.page } : prev));
      setEditing(false);
      if (result.forked) setEditVersion({ id: result.version.version_id, number: result.version.version_number });
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Không lưu được");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Spin className="flex justify-center py-12" />;
  if (error) return <Alert type="warning" showIcon message={error} />;
  if (pages.length === 0) {
    return <Empty description={t("pageViewer.noPages", { defaultValue: "Bộ này chưa có trang." })} />;
  }

  const page = pages[index];
  const withImages = pages.filter((p) => p.image_url).length;
  const loadedDetail = detail?.page_number === page.page_number ? detail : null;
  const voteMeta = loadedDetail?.ocr_vote_meta ? [loadedDetail.ocr_vote_meta as unknown as VoteMeta] : null;
  const replacedImage = imageReplaced.includes(page.page_number);
  const boxes = replacedImage ? [] : (loadedDetail?.ocr_bbox ?? []);
  const stale = isVoteMetaV2(loadedDetail?.ocr_vote_meta) && !!loadedDetail?.ocr_vote_meta.downstream_stale;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Pagination
          simple
          current={index + 1}
          total={pages.length}
          pageSize={1}
          onChange={(value) => setIndex(value - 1)}
        />
        <div className="flex flex-wrap items-center gap-2">
          {editVersion && (
            <>
              <Tag color="orange">
                {t("pageViewer.editVersion", { defaultValue: "Bản sửa tay v{{n}}", n: editVersion.number })}
              </Tag>
              <Button size="small" onClick={() => setEditVersion(null)}>
                {t("pageViewer.backToOriginal", { defaultValue: "Về bản gốc" })}
              </Button>
            </>
          )}
          <input
            ref={fileInput}
            type="file"
            hidden
            accept="image/jpeg,image/png,image/webp,image/tiff"
            data-testid="page-image-input"
            onChange={(e) => void onPickImage(e.target.files?.[0], page)}
          />
          <Button
            size="small"
            icon={<PictureOutlined />}
            loading={replacing}
            onClick={() => fileInput.current?.click()}
          >
            {t("pageViewer.replaceImage", { defaultValue: "Thay ảnh" })}
          </Button>
          <Button size="small" icon={<ScanOutlined />} loading={ocrBusy} onClick={() => runOcr(page)}>
            {t("pageViewer.ocr", { defaultValue: "OCR lại trang" })}
          </Button>
          <Button size="small" type="primary" icon={<EditOutlined />} onClick={() => openEdit(page)}>
            {t("pageViewer.edit", { defaultValue: "Sửa trang" })}
          </Button>
        </div>
        <Text type="secondary">
          {t("pageViewer.imageCount", {
            defaultValue: "{{n}}/{{total}} trang có ảnh",
            n: withImages,
            total: pages.length,
          })}
        </Text>
      </div>
      {ocrError && <Alert type="error" showIcon closable message={ocrError} onClose={() => setOcrError(null)} />}
      {ocrStale.includes(page.page_number) && (
        <Alert
          type="warning"
          showIcon
          message={t("pageViewer.ocrStale", {
            defaultValue: "Đã OCR lại trang này. Phiên âm và dịch nghĩa bên dưới vẫn là của chữ cũ, chưa khớp chữ mới.",
          })}
        />
      )}
      {imageError && <Alert type="error" showIcon closable message={imageError} onClose={() => setImageError(null)} />}
      {replacedImage && (
        <Alert
          type="warning"
          showIcon
          message={t("pageViewer.imageReplaced", {
            defaultValue:
              "Đã thay ảnh trang này. Chữ và kết quả OCR vẫn của ảnh cũ nên khung chữ được ẩn; cần OCR lại để khớp ảnh mới. Ảnh cũ vẫn được giữ trên máy chủ.",
          })}
        />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <Card size="small" title={t("pageViewer.page", { defaultValue: "Trang {{n}}", n: page.page_number })}>
          {page.image_url ? (
            <div className="page-viewer-images">
              <figure>
                <figcaption>{t("pageViewer.original", { defaultValue: "Ảnh gốc" })}</figcaption>
                <Image src={page.image_url} alt={t("pageViewer.page", { defaultValue: "Trang {{n}}", n: page.page_number })} />
              </figure>
              {boxes.length > 0 ? (
                <figure>
                  <figcaption>
                    {t("pageViewer.boxes", {
                      defaultValue: "Khung chữ (Paddle) — {{n}} khung, số = thứ tự đọc",
                      n: boxes.length,
                    })}
                  </figcaption>
                  <BoundingBoxOverlay
                    imageUrl={page.image_url}
                    alt={t("pageViewer.boxesAlt", { defaultValue: "Trang {{n}} có khung chữ", n: page.page_number })}
                    bbox={boxes}
                    showBoxes
                    showOrder
                  />
                </figure>
              ) : (
                loadedDetail && !replacedImage && (
                  <Text type="secondary" className="text-xs">
                    {t("pageViewer.noBoxes", { defaultValue: "Chưa có khung chữ cho trang này." })}
                  </Text>
                )
              )}
            </div>
          ) : (
            <Empty
              image={<FileImageOutlined className="text-4xl text-muted-foreground" />}
              description={t("pageViewer.noImage", { defaultValue: "Chưa có ảnh cho trang này" })}
            />
          )}
        </Card>
        <div className="space-y-3">
          <Card size="small" title={t("pageViewer.hannom", { defaultValue: "Chữ Hán Nôm" })}>
            {page.hannom_text ? (
              <Paragraph className="whitespace-pre-wrap page-viewer-han !mb-0">{page.hannom_text}</Paragraph>
            ) : (
              <Paragraph type="secondary" className="!mb-0">
                {t("pageViewer.none", { defaultValue: "Chưa có" })}
              </Paragraph>
            )}
          </Card>
          {detailError && <Alert type="warning" showIcon message={detailError} />}
          {stale && (
            <Alert
              type="warning"
              showIcon
              message={t("pageViewer.stale", {
                defaultValue: "Chữ Hán trang này đã đổi sau khi vote lại — phiên âm / dịch nghĩa có thể chưa khớp.",
              })}
            />
          )}
          {loadedDetail || detailError ? (
            <PipelineStepsPanel
              key={page.page_number}
              transliterationText={page.transliteration_text}
              translationText={page.translation_text}
              voteMeta={voteMeta}
              initialStep={voteMeta ? 1 : 0}
              hannomText={page.hannom_text}
            />
          ) : (
            <Spin className="flex justify-center py-6" />
          )}
        </div>
      </div>
      <Modal
        open={editing}
        width={720}
        title={t("pageViewer.editTitle", { defaultValue: "Sửa trang {{n}}", n: page.page_number })}
        okText={t("pageViewer.save", { defaultValue: "Lưu" })}
        cancelText={t("pageViewer.cancel", { defaultValue: "Huỷ" })}
        confirmLoading={saving}
        onOk={() => void saveEdit(page)}
        onCancel={() => setEditing(false)}
        destroyOnHidden
      >
        <div className="space-y-3">
          <Alert
            type="info"
            showIcon
            message={t("pageViewer.editNote", {
              defaultValue:
                "Bản gốc được giữ nguyên: chỗ sửa lưu vào một version sửa tay riêng. Khung chữ và kết quả vote OCR giữ như cũ nên có thể không còn khớp chữ đã sửa.",
            })}
          />
          {saveError && <Alert type="error" showIcon message={saveError} />}
          <label className="block">
            <Text strong>{t("pageViewer.hannom", { defaultValue: "Chữ Hán Nôm" })}</Text>
            <Input.TextArea
              aria-label={t("pageViewer.hannom", { defaultValue: "Chữ Hán Nôm" })}
              className="page-viewer-han"
              autoSize={{ minRows: 4, maxRows: 14 }}
              value={draft.hannom}
              onChange={(e) => setDraft((d) => ({ ...d, hannom: e.target.value }))}
            />
          </label>
          <label className="block">
            <Text strong>{t("pageViewer.translit", { defaultValue: "Phiên âm" })}</Text>
            <Input.TextArea
              aria-label={t("pageViewer.translit", { defaultValue: "Phiên âm" })}
              autoSize={{ minRows: 3, maxRows: 12 }}
              value={draft.translit}
              onChange={(e) => setDraft((d) => ({ ...d, translit: e.target.value }))}
            />
          </label>
          <label className="block">
            <Text strong>{t("pageViewer.translation", { defaultValue: "Dịch nghĩa" })}</Text>
            <Input.TextArea
              aria-label={t("pageViewer.translation", { defaultValue: "Dịch nghĩa" })}
              autoSize={{ minRows: 3, maxRows: 12 }}
              value={draft.translation}
              onChange={(e) => setDraft((d) => ({ ...d, translation: e.target.value }))}
            />
          </label>
        </div>
      </Modal>
    </div>
  );
}
