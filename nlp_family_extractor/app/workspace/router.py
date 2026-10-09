from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser, CurrentUser, OptionalUser
from app.auth.models import UserRole
from app.auth.user_repository import UserRepository
from app.database import database_enabled, get_db
from app.documents.repository import DocumentRepository
from app.documents.schemas import DocumentListResponse, DocumentResponse
from app.documents.storage import ObjectStorage
from app.family_tree_store import FamilyTreeNotFoundError, FamilyTreeStoreError
from app.workspace.models import GiaPhaVersion, GiaPhaVersionStep, OcrStatus, TreeStatus, UserScan
from app.workspace.gia_pha_list import GIA_PHA_CACHE, MAX_PAGE_SIZE, filter_items, paginate
from app.workspace.llm_import import add_coverage_warnings, parse_import
from app.workspace.stats import STATS_CACHE, page_progress, summarize_items
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository, UserScanRepository
from app.workspace.utils import compute_generation_count

# Phải khớp đúng tools/import_hannom_bilingual_corpus.py:REQUEST_ID_PREFIX
HANNOM_CORPUS_REQUEST_ID_PREFIX = "hannom-corpus:"
MANUAL_EDIT_SOURCE = "manual-edit"  # GiaPhaVersion.source của version do người sửa tay từng trang


def require_workspace_database() -> None:
    if not database_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database chưa được cấu hình. Thiết lập biến môi trường MYSQL_*.",
        )


class WorkspaceTreeSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    node_count: int
    generation_count: int = 0
    external_url: Optional[str] = None
    has_source_document: bool = False
    has_hannom_text: bool = False
    user_id: Optional[int] = None
    is_public: bool = False
    lineage_code: Optional[str] = None
    source_document_title: Optional[str] = None


class WorkspaceTreeDocument(WorkspaceTreeSummary):
    nodes: List[Dict[str, Any]] = Field(default_factory=list)


class WorkspaceTreeListResponse(BaseModel):
    total: int
    items: List[WorkspaceTreeSummary]


class UserStatsResponse(BaseModel):
    scanned_documents: int
    family_trees: int
    history_total: int


class AdminStatsResponse(BaseModel):
    total_trees: int
    public_trees: int
    total_users: int
    total_scans: int
    history_total: int


class HannomProgressItem(BaseModel):
    doc_id: str
    title_vn: str
    page_count: int
    has_ocr: bool
    has_transliteration: bool
    has_translation: bool
    ma_dinh_danh: Optional[str] = None
    flags: List[str] = Field(default_factory=list)


class HannomProgressResponse(BaseModel):
    total_books: int
    total_pages: int
    pages_with_ocr: int
    pages_with_transliteration: int
    pages_with_translation: int
    ocr_percent: float
    transliteration_percent: float
    translation_percent: float
    books: List[HannomProgressItem]


class UserScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    file_name: str
    file_type: str
    page_count: int
    uploaded_at: datetime
    ocr_status: OcrStatus
    tree_status: TreeStatus
    family_tree_id: Optional[str] = None
    request_id: Optional[str] = None
    source_file_key: Optional[str] = None
    source_text: Optional[str] = None
    hannom_text: Optional[str] = None
    transliteration_text: Optional[str] = None
    ocr_bbox: Optional[List[Dict[str, Any]]] = None
    # Vote OCR theo từng trang (pipeline v2 / corpus import) — để mở lại 1 bộ
    # gia phả vẫn xem được panel các bước, không chỉ ngay sau khi phân tích.
    ocr_vote_meta: Optional[List[Dict[str, Any]]] = None
    ma_dinh_danh: Optional[str] = None
    ma_dinh_danh_nguon: Optional[str] = None


class UserScanListResponse(BaseModel):
    total: int
    items: List[UserScanResponse]


class UserScanCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    file_name: str = Field(min_length=1, max_length=255)
    file_type: str = Field(default="unknown", max_length=64)
    page_count: int = Field(default=1, ge=1)
    source_text: Optional[str] = None
    hannom_text: Optional[str] = None
    transliteration_text: Optional[str] = None
    ocr_bbox: Optional[List[Dict[str, Any]]] = None


class UserScanUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    ocr_status: Optional[OcrStatus] = None
    tree_status: Optional[TreeStatus] = None
    family_tree_id: Optional[str] = None
    request_id: Optional[str] = None
    source_text: Optional[str] = None
    source_file_key: Optional[str] = None
    hannom_text: Optional[str] = None
    transliteration_text: Optional[str] = None
    ocr_bbox: Optional[List[Dict[str, Any]]] = None


class ItemVersionStep(BaseModel):
    step_type: str
    status: str
    error_message: Optional[str] = None


class ItemVersion(BaseModel):
    version_id: int
    version_number: int
    is_current: bool
    ocr_engines: Optional[List[str]] = None
    status: str
    steps: List[ItemVersionStep] = Field(default_factory=list)
    parent_version_id: Optional[int] = None
    source: Optional[str] = None  # != None: version nhập từ LLM
    review_status: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[str] = None


class LlmImportRequest(BaseModel):
    source: str = ""
    model_note: Optional[str] = None
    records: List[Dict[str, Any]] = Field(default_factory=list)
    dry_run: bool = False


class LlmImportResult(BaseModel):
    ok: bool
    dry_run: bool
    pages: int
    records: int
    skipped_annotations: int
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    version: Optional[ItemVersion] = None


class TextEngineRunRequest(BaseModel):
    engine: str
    pages: Optional[List[int]] = None  # None = mọi trang có văn bản Hán Nôm


class GiaPhaPageView(BaseModel):
    page_number: int
    image_url: Optional[str] = None  # link tạm (presigned) nếu ảnh đã lên MinIO
    hannom_text: Optional[str] = None
    transliteration_text: Optional[str] = None
    translation_text: Optional[str] = None


class GiaPhaPageDetail(GiaPhaPageView):
    # OCR từng engine + vote của trang (đã gắn sẵn diff từng chữ để tô màu).
    ocr_vote_meta: Optional[Dict[str, Any]] = None
    # Khung chữ trên ảnh gốc [{bbox_xyxy, han, confidence, order}] — theo thứ tự đọc.
    ocr_bbox: Optional[List[Dict[str, Any]]] = None


class GiaPhaPageEditRequest(BaseModel):
    """Sửa tay chữ 1 trang. Trường None = giữ nguyên; "" = xoá trắng."""

    hannom_text: Optional[str] = None
    transliteration_text: Optional[str] = None
    translation_text: Optional[str] = None
    # None = sửa trên version hiện tại. Version không phải "manual-edit" thì
    # không bị ghi đè — server fork ra version sửa tay mới và trả về.
    version_id: Optional[int] = None


class GiaPhaPageEditResult(BaseModel):
    version: ItemVersion
    page: GiaPhaPageView
    forked: bool  # True = vừa tạo version sửa tay mới (client dùng version_id này cho các lần sửa sau)


class GiaPhaPageDeletedItem(BaseModel):
    page_number: int
    deleted_at: Optional[str] = None
    image_url: Optional[str] = None
    hannom_text: Optional[str] = None  # của version hiện tại, để nhận ra trang


class GiaPhaPageDeleteResult(BaseModel):
    page_number: int
    deleted: bool  # True = vừa xoá mềm, False = vừa khôi phục
    active_pages: int


class DeletedScanItem(BaseModel):
    id: int
    title: str
    ma_dinh_danh: Optional[str] = None
    page_count: int
    deleted_at: Optional[str] = None
    deleted_by: Optional[int] = None


class DeletedScanListResponse(BaseModel):
    total: int
    items: List[DeletedScanItem]


class GiaPhaPageImageResult(BaseModel):
    page: GiaPhaPageView
    # Key ảnh cũ — object vẫn còn trên MinIO (không xoá) nên khôi phục được.
    previous_image_key: Optional[str] = None


class GiaPhaPageOcrRequest(BaseModel):
    engine: str = "kimhannom"
    # OCR là lời gọi TỐN TIỀN: server từ chối nếu chưa có xác nhận rõ ràng.
    confirm_paid: bool = False
    version_id: Optional[int] = None  # version sửa tay đang làm việc (xem GiaPhaPageEditRequest)


class GiaPhaPageOcrResult(BaseModel):
    version: ItemVersion
    page: GiaPhaPageView
    forked: bool
    engine: str
    box_count: int
    # Phiên âm / dịch nghĩa của trang còn là của chữ cũ → chưa khớp OCR mới.
    downstream_stale: bool


class MaDinhDanhAutoResult(BaseModel):
    ma_dinh_danh: Optional[str] = None
    ma_dinh_danh_nguon: Optional[str] = None
    problems: List[str] = Field(default_factory=list)


class VersionReviewRequest(BaseModel):
    review_status: str = Field(pattern="^(pending|approved|rejected)$")


class GiaPhaItem(BaseModel):
    id: str
    ma_dinh_danh_pending: bool = False
    ma_dinh_danh_nguon: Optional[str] = None  # "catalogue" | "gemini"
    ho_toc: Optional[str] = None  # để tìm kiếm theo họ
    title: str
    status: str  # "built" | "pending"
    is_public: Optional[bool] = None
    updated_at: str
    scan_id: Optional[int] = None
    tree_id: Optional[str] = None
    node_count: Optional[int] = None
    current_version: Optional[ItemVersion] = None


class GiaPhaListResponse(BaseModel):
    total: int  # số bộ SAU khi lọc/tìm kiếm (dùng cho phân trang)
    items: List[GiaPhaItem]  # chỉ trang hiện tại (hoặc tất cả nếu page_size=0)
    total_all: Optional[int] = None  # số bộ TRƯỚC khi lọc (hiện "x/y bộ")
    page: int = 1
    page_size: int = 0  # 0 = không phân trang


class HoTocCount(BaseModel):
    ho_toc: str
    count: int


class CodeSourceCounts(BaseModel):
    catalogue: int = 0
    gemini: int = 0
    other: int = 0


class PageProgress(BaseModel):
    scans: int
    pages: int
    ocr_pages: int
    transliteration_pages: int
    translation_pages: int
    ocr_percent: float
    transliteration_percent: float
    translation_percent: float


class GiaPhaSummary(BaseModel):
    """Thống kê tóm tắt của phạm vi người xem (khách / user / admin), cache 30 giây."""

    scope: str  # "public" | "user" | "admin"
    total: int
    built: int
    pending: int
    with_code: int
    without_code: int
    code_source: CodeSourceCounts
    public_trees: int
    nodes: int
    top_ho_toc: List[HoTocCount]
    pages: Optional[PageProgress] = None  # None với khách (không lộ số liệu riêng tư)
    generated_at: str


class GiaPhaVersionCloneRequest(BaseModel):
    make_current: bool = False


class UserFamilyTreeCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    source_scan_id: Optional[int] = None


def _to_tree_summary(item: Dict[str, Any], *, source_document_title: Optional[str] = None) -> WorkspaceTreeSummary:
    nodes = item.get("nodes") if isinstance(item.get("nodes"), list) else []
    return WorkspaceTreeSummary(
        id=item["id"],
        name=item["name"],
        description=item.get("description"),
        created_at=item["created_at"],
        updated_at=item["updated_at"],
        node_count=item.get("node_count", len(nodes)),
        generation_count=item.get("generation_count") or compute_generation_count(nodes),
        external_url=item.get("external_url"),
        has_source_document=bool(item.get("has_source_document", False)),
        has_hannom_text=bool(item.get("has_hannom_text", False)),
        user_id=item.get("user_id"),
        is_public=bool(item.get("is_public", False)),
        lineage_code=item.get("lineage_code"),
        source_document_title=source_document_title,
    )


def _scan_display_id(scan: UserScan) -> tuple[str, bool]:
    """Mã gia phả hiển thị: ma_dinh_danh (F-code) nếu đã xác nhận đủ 5 input,
    ngược lại id tạm (doc_id từ request_id, hoặc fallback scan-{id}) + cờ
    ma_dinh_danh_pending=True. Xem app/workspace/ma_dinh_danh.py."""
    if scan.ma_dinh_danh:
        return scan.ma_dinh_danh, False
    if scan.request_id:
        doc_id = (
            scan.request_id[len(HANNOM_CORPUS_REQUEST_ID_PREFIX):]
            if scan.request_id.startswith(HANNOM_CORPUS_REQUEST_ID_PREFIX)
            else scan.request_id
        )
        return doc_id, True
    return f"scan-{scan.id}", True


def _item_version_from(version: GiaPhaVersion, steps: List[GiaPhaVersionStep]) -> ItemVersion:
    return ItemVersion(
        version_id=version.id,
        version_number=version.version_number,
        is_current=version.is_current,
        ocr_engines=version.ocr_engines,
        status=version.status,
        steps=[
            ItemVersionStep(step_type=s.step_type.value, status=s.status, error_message=s.error_message) for s in steps
        ],
        parent_version_id=version.parent_version_id,
        source=version.source,
        review_status=version.review_status,
        note=version.note,
        created_at=version.created_at.isoformat() if version.created_at else None,
    )


def _version_lookup(version_repo: GiaPhaVersionRepository, version_ids: List[int]) -> Dict[int, ItemVersion]:
    """Nạp trước version hiện tại + các bước của nhiều bộ trong 2 truy vấn (thay vì 2 truy vấn/bộ)."""
    versions = version_repo.get_many(version_ids)
    steps = version_repo.steps_for_many(list(versions))
    return {vid: _item_version_from(v, steps.get(vid, [])) for vid, v in versions.items()}


def _scan_to_gia_pha_item(
    scan: UserScan,
    version_repo: GiaPhaVersionRepository,
    lookup: Optional[Dict[int, ItemVersion]] = None,
) -> GiaPhaItem:
    gia_pha_id, pending = _scan_display_id(scan)
    current_version = None
    if scan.current_version_id:
        if lookup is not None:
            current_version = lookup.get(scan.current_version_id)
        else:
            version = version_repo.get(scan.current_version_id)
            if version is not None:
                current_version = _item_version_from(version, version_repo.steps_for(version.id))
    return GiaPhaItem(
        id=gia_pha_id,
        ma_dinh_danh_pending=pending,
        ma_dinh_danh_nguon=scan.ma_dinh_danh_nguon,
        ho_toc=scan.ho_toc,
        title=scan.title,
        status="built" if scan.tree_status == TreeStatus.CREATED else "pending",
        updated_at=scan.uploaded_at.isoformat(),
        scan_id=scan.id,
        tree_id=scan.family_tree_id,
        current_version=current_version,
    )


def _tree_to_gia_pha_item(
    tree: Dict[str, Any],
    source_scan: Optional[UserScan] = None,
    version_repo: Optional[GiaPhaVersionRepository] = None,
    *,
    expose_scan: bool = False,
    lookup: Optional[Dict[int, ItemVersion]] = None,
) -> GiaPhaItem:
    """Cây đã dựng. Mã hiển thị lấy từ bộ gia phả nguồn (scan) — trước đây
    dùng id kỹ thuật của cây và ghi sai ma_dinh_danh_pending=False. Cây không
    có bộ nguồn → id cây + pending=True (chưa có mã chính thức).
    expose_scan=False (khách): chỉ hiện mã, không lộ scan_id/version riêng tư."""
    display_id, pending = _scan_display_id(source_scan) if source_scan else (tree["id"], True)
    current_version = None
    if expose_scan and source_scan is not None and source_scan.current_version_id:
        if lookup is not None:
            current_version = lookup.get(source_scan.current_version_id)
        elif version_repo is not None:
            version = version_repo.get(source_scan.current_version_id)
            if version is not None:
                current_version = _item_version_from(version, version_repo.steps_for(version.id))
    return GiaPhaItem(
        id=display_id,
        ma_dinh_danh_pending=pending,
        ma_dinh_danh_nguon=source_scan.ma_dinh_danh_nguon if source_scan else None,
        ho_toc=source_scan.ho_toc if source_scan else None,
        title=tree["name"],
        status="built",
        is_public=bool(tree.get("is_public")),
        updated_at=tree["updated_at"],
        scan_id=source_scan.id if (expose_scan and source_scan is not None) else None,
        tree_id=tree["id"],
        node_count=tree.get("node_count"),
        current_version=current_version,
    )


def _find_scan_by_display_id(scans: UserScanRepository, current_user, gia_pha_id: str) -> Optional[UserScan]:
    candidates = scans.list_all() if current_user.role == UserRole.ADMIN else scans.list_by_user(current_user.id)
    for scan in candidates:
        display_id, _ = _scan_display_id(scan)
        if display_id == gia_pha_id:
            return scan
    return None


def create_workspace_router(
    *,
    get_tree_store: Callable[[], Any],
    get_history_repo: Callable[[], Any],
) -> APIRouter:
    router = APIRouter(tags=["Workspace"], dependencies=[Depends(require_workspace_database)])

    def scan_repo(db: Session = Depends(get_db)) -> UserScanRepository:
        return UserScanRepository(db)

    def user_repo(db: Session = Depends(get_db)) -> UserRepository:
        return UserRepository(db)

    def version_repo(db: Session = Depends(get_db)) -> GiaPhaVersionRepository:
        return GiaPhaVersionRepository(db)

    def page_repo(db: Session = Depends(get_db)) -> GiaPhaPageRepository:
        return GiaPhaPageRepository(db)

    def _raise_store_error(error: Exception) -> None:
        if isinstance(error, FamilyTreeNotFoundError):
            raise HTTPException(status_code=404, detail=str(error)) from error
        if isinstance(error, FamilyTreeStoreError):
            raise HTTPException(status_code=500, detail=str(error)) from error
        raise HTTPException(status_code=500, detail="Unexpected family tree storage error") from error

    @router.get("/api/public/family-trees", response_model=WorkspaceTreeListResponse)
    def list_public_family_trees() -> WorkspaceTreeListResponse:
        store = get_tree_store()
        try:
            items = store.list_public_trees()
        except Exception as error:
            _raise_store_error(error)
        summaries = [_to_tree_summary(item) for item in items]
        return WorkspaceTreeListResponse(total=len(summaries), items=summaries)

    @router.get("/api/public/family-trees/{tree_id}", response_model=WorkspaceTreeDocument)
    def get_public_family_tree(tree_id: str) -> WorkspaceTreeDocument:
        store = get_tree_store()
        try:
            item = store.get_public_tree(tree_id)
        except Exception as error:
            _raise_store_error(error)
        summary = _to_tree_summary(item, source_document_title=None)
        return WorkspaceTreeDocument(**summary.model_dump(), nodes=item.get("nodes", []))

    @router.get("/api/public/family-trees/{tree_id}/documents", response_model=DocumentListResponse)
    def list_public_family_tree_documents(
        tree_id: str,
        db: Session = Depends(get_db),
    ) -> DocumentListResponse:
        store = get_tree_store()
        try:
            store.get_public_tree(tree_id)
        except Exception as error:
            _raise_store_error(error)

        documents = DocumentRepository(db).list_by_family_tree(tree_id)
        storage = ObjectStorage.from_env()
        items: List[DocumentResponse] = []
        for document in documents:
            response = DocumentResponse.model_validate(document)
            for file_item in response.files:
                if storage.config.enabled:
                    file_item.download_url = storage.get_presigned_url(file_item.file_key)
            items.append(response)
        return DocumentListResponse(total=len(items), items=items)

    def _scope_key(current_user) -> str:
        if current_user is None:
            return "public"
        if current_user.role == UserRole.ADMIN:
            return "admin"
        return f"user:{current_user.id}"

    def _load_all_items(current_user, scans: UserScanRepository, versions: GiaPhaVersionRepository, *, refresh: bool = False):
        """Danh sách Gia phả ĐẦY ĐỦ (chưa lọc) của phạm vi người xem; cache 20 giây trong bộ nhớ."""
        scope_key = _scope_key(current_user)
        all_items = None if refresh else GIA_PHA_CACHE.get(scope_key)
        if all_items is not None:
            return all_items
        store = get_tree_store()
        try:
            if current_user is None:
                trees = store.list_public_trees()
                pending_scans: List[UserScan] = []
            elif current_user.role == UserRole.ADMIN:
                trees = store.list_trees()
                pending_scans = [s for s in scans.list_all() if not s.family_tree_id]
            else:
                trees = store.list_trees_by_user(current_user.id)
                pending_scans = [s for s in scans.list_by_user(current_user.id) if not s.family_tree_id]
        except Exception as error:
            _raise_store_error(error)

        source_scans = scans.by_family_tree_ids([tree["id"] for tree in trees])
        expose = current_user is not None
        version_ids = [sc.current_version_id for sc in pending_scans if sc.current_version_id]
        if expose:
            version_ids += [sc.current_version_id for sc in source_scans.values() if sc.current_version_id]
        lookup = _version_lookup(versions, version_ids)
        all_items = [
            _tree_to_gia_pha_item(tree, source_scans.get(tree["id"]), versions, expose_scan=expose, lookup=lookup)
            for tree in trees
        ]
        all_items.extend(_scan_to_gia_pha_item(scan, versions, lookup) for scan in pending_scans)
        GIA_PHA_CACHE.set(scope_key, all_items)
        return all_items

    @router.get("/api/gia-pha/summary", response_model=GiaPhaSummary)
    def gia_pha_summary(
        current_user: OptionalUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        refresh: bool = Query(False, description="true = bỏ qua cache"),
    ) -> GiaPhaSummary:
        """Thống kê tóm tắt (số bộ, đã dựng cây/chờ, có/chưa có mã, nguồn mã, nhân vật, họ tộc
        nhiều nhất, tiến độ OCR/phiên âm/dịch). Cache 30 giây theo phạm vi, xoá khi có request ghi."""
        scope_key = _scope_key(current_user)
        cache_key = f"summary:{scope_key}"
        cached = None if refresh else STATS_CACHE.get(cache_key)
        if cached is not None:
            return cached
        data = summarize_items(_load_all_items(current_user, scans, versions, refresh=refresh))
        pages = None
        if current_user is not None:
            only_user = None if current_user.role == UserRole.ADMIN else current_user.id
            pages = PageProgress(**page_progress(scans.page_stats(only_user)))
        result = GiaPhaSummary(
            scope=scope_key.split(":")[0],
            pages=pages,
            generated_at=datetime.now(timezone.utc).isoformat(),
            **data,
        )
        STATS_CACHE.set(cache_key, result)
        return result

    @router.get("/api/gia-pha", response_model=GiaPhaListResponse)
    def list_gia_pha(
        current_user: OptionalUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        page: int = Query(1, ge=1),
        page_size: int = Query(0, ge=0, le=MAX_PAGE_SIZE, description="0 = không phân trang (trả tất cả)"),
        q: str = Query("", max_length=200, description="Tìm theo mã/tên/họ, không phân biệt dấu"),
        status: Literal["all", "built", "pending"] = "all",
        code: Literal["all", "has", "none"] = "all",
        source: Literal["all", "catalogue", "gemini"] = "all",
        refresh: bool = Query(False, description="true = bỏ qua cache, đọc lại từ DB (nút Tải lại)"),
    ) -> GiaPhaListResponse:
        """Danh sách Gia phả: lọc + phân trang ở backend. Danh sách đầy đủ (chưa lọc) của mỗi
        phạm vi (khách / admin / từng user) được cache 20 giây trong bộ nhớ và bị xoá ngay khi có
        request ghi thành công (api.py); lọc và cắt trang chạy trên bản cache nên rẻ."""
        all_items = _load_all_items(current_user, scans, versions, refresh=refresh)
        matched = filter_items(all_items, q=q, status=status, code=code, source=source)
        return GiaPhaListResponse(
            total=len(matched),
            items=paginate(matched, page, page_size),
            total_all=len(all_items),
            page=page,
            page_size=page_size,
        )

    @router.get("/api/gia-pha/{gia_pha_id}/versions", response_model=List[ItemVersion])
    def list_gia_pha_versions(
        gia_pha_id: str,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
    ) -> List[ItemVersion]:
        scan = _find_scan_by_display_id(scans, current_user, gia_pha_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy bộ gia phả này.")
        return [
            _item_version_from(version, versions.steps_for(version.id))
            for version in versions.list_by_scan(scan.id)
        ]

    @router.get("/api/user/documents/{scan_id}/versions", response_model=List[ItemVersion])
    def list_scan_versions(
        scan_id: int,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
    ) -> List[ItemVersion]:
        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        return [_item_version_from(v, versions.steps_for(v.id)) for v in versions.list_by_scan(scan.id)]

    @router.post("/api/user/documents/{scan_id}/imports", response_model=LlmImportResult)
    def import_llm_results(
        scan_id: int,
        payload: LlmImportRequest,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> LlmImportResult:
        """Nhập kết quả {cn, sv, vi} từ tool LLM chạy NGOÀI web. Chủ bộ gia
        phả hoặc admin được nhập. dry_run=True: chỉ kiểm tra + xem trước."""
        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        pages = pages_repo.list_by_scan(scan.id)
        parent = versions.get_current(scan.id)
        if not pages or parent is None:
            raise HTTPException(
                status_code=400,
                detail="Bộ gia phả chưa có trang/version — cần OCR hoặc import corpus trước khi nhập kết quả LLM.",
            )
        page_ids = {p.page_number: p.id for p in pages}
        parsed = parse_import(payload.model_dump(), set(page_ids))
        if not parsed.errors:
            contents = {c.page_id: c for c in pages_repo.list_content_for_version(parent.id)}
            add_coverage_warnings(
                parsed,
                {number: (contents[pid].hannom_text if pid in contents else None) for number, pid in page_ids.items()},
            )
        result = LlmImportResult(
            ok=not parsed.errors,
            dry_run=payload.dry_run,
            pages=len(parsed.pages),
            records=parsed.record_count,
            skipped_annotations=parsed.skipped_annotations,
            errors=parsed.errors,
            warnings=parsed.warnings,
        )
        if payload.dry_run:
            return result
        if parsed.errors:
            raise HTTPException(status_code=400, detail=result.model_dump())
        version = versions.create_import_version(
            user_scan_id=scan.id,
            parent_version_id=parent.id,
            source=parsed.source,
            model_note=parsed.model_note,
            pages={n: [{"cn": r.cn, "sv": r.sv, "vi": r.vi} for r in recs] for n, recs in parsed.pages.items()},
            page_ids=page_ids,
            created_by=current_user.id,
        )
        result.version = _item_version_from(version, versions.steps_for(version.id))
        return result

    @router.get("/api/user/documents/{scan_id}/pages/deleted", response_model=List[GiaPhaPageDeletedItem])
    def list_deleted_scan_pages(
        scan_id: int,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> List[GiaPhaPageDeletedItem]:
        """Các trang đã xoá mềm của bộ (để khôi phục). Chủ bộ hoặc admin."""
        from app.documents.storage import ObjectStorage
        from app.workspace.page_images import is_storage_key

        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        version = versions.get_current(scan.id)
        contents = {c.page_id: c for c in pages_repo.list_content_for_version(version.id)} if version else {}
        storage = ObjectStorage.from_env()
        items: List[GiaPhaPageDeletedItem] = []
        for page in pages_repo.list_deleted_by_scan(scan.id):
            image_url = None
            if is_storage_key(page.image_file_key) and storage.config.enabled:
                try:
                    image_url = storage.get_presigned_url(page.image_file_key)
                except Exception:  # noqa: BLE001 — MinIO lỗi thì vẫn liệt kê được
                    image_url = None
            content = contents.get(page.id)
            items.append(
                GiaPhaPageDeletedItem(
                    page_number=page.page_number,
                    deleted_at=page.deleted_at.isoformat() if page.deleted_at else None,
                    image_url=image_url,
                    hannom_text=content.hannom_text if content else None,
                )
            )
        return items

    @router.delete("/api/user/documents/{scan_id}/pages/{page_number}", response_model=GiaPhaPageDeleteResult)
    def delete_scan_page(
        scan_id: int,
        page_number: int,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> GiaPhaPageDeleteResult:
        """Xoá MỀM 1 trang: ẩn khỏi danh sách và khỏi văn bản gộp, nhưng nội
        dung mọi version và ảnh trên MinIO vẫn còn, khôi phục được bằng
        POST .../restore. Số trang của bộ được tính lại. Chủ bộ hoặc admin."""
        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        page = next((p for p in pages_repo.list_by_scan(scan.id) if p.page_number == page_number), None)
        if page is None:
            raise HTTPException(status_code=404, detail="Không có trang này.")
        pages_repo.set_deleted(page, deleted=True, user_id=current_user.id)
        active = pages_repo.sync_page_count(scan.id)
        current = versions.get_current(scan.id)
        if current is not None:
            pages_repo.sync_flat_cache(scans, scan.id, current.id)
        return GiaPhaPageDeleteResult(page_number=page_number, deleted=True, active_pages=active)

    @router.post("/api/user/documents/{scan_id}/pages/{page_number}/restore", response_model=GiaPhaPageDeleteResult)
    def restore_scan_page(
        scan_id: int,
        page_number: int,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> GiaPhaPageDeleteResult:
        """Khôi phục trang đã xoá mềm (giữ nguyên số trang và nội dung)."""
        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        page = next((p for p in pages_repo.list_deleted_by_scan(scan.id) if p.page_number == page_number), None)
        if page is None:
            raise HTTPException(status_code=404, detail="Không có trang đã xoá này.")
        pages_repo.set_deleted(page, deleted=False)
        active = pages_repo.sync_page_count(scan.id)
        current = versions.get_current(scan.id)
        if current is not None:
            pages_repo.sync_flat_cache(scans, scan.id, current.id)
        return GiaPhaPageDeleteResult(page_number=page_number, deleted=False, active_pages=active)

    @router.get("/api/admin/documents/deleted", response_model=DeletedScanListResponse)
    def list_deleted_documents(
        _: AdminUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> DeletedScanListResponse:
        """Các bộ đã xoá mềm (chỉ admin) để khôi phục."""
        items = [
            DeletedScanItem(
                id=scan.id,
                title=scan.title,
                ma_dinh_danh=scan.ma_dinh_danh,
                page_count=scan.page_count,
                deleted_at=scan.deleted_at.isoformat() if scan.deleted_at else None,
                deleted_by=scan.deleted_by,
            )
            for scan in scans.list_deleted()
        ]
        return DeletedScanListResponse(total=len(items), items=items)

    @router.delete("/api/user/documents/{scan_id}", response_model=DeletedScanItem)
    def delete_user_document(
        scan_id: int,
        current_user: AdminUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> DeletedScanItem:
        """Xoá MỀM cả bộ (chỉ admin): ẩn khỏi mọi danh sách và số thống kê
        công khai; trang, version, ảnh và mã định danh vẫn còn (mã không được
        cấp lại). Cây gia phả đã dựng từ bộ không bị đụng tới."""
        scan = scans.get(scan_id)
        if scan is None or scan.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        scan = scans.soft_delete(scan, user_id=current_user.id)
        return DeletedScanItem(
            id=scan.id,
            title=scan.title,
            ma_dinh_danh=scan.ma_dinh_danh,
            page_count=scan.page_count,
            deleted_at=scan.deleted_at.isoformat() if scan.deleted_at else None,
            deleted_by=scan.deleted_by,
        )

    @router.post("/api/user/documents/{scan_id}/restore", response_model=DeletedScanItem)
    def restore_user_document(
        scan_id: int,
        _: AdminUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> DeletedScanItem:
        """Khôi phục bộ đã xoá mềm (chỉ admin)."""
        scan = scans.get(scan_id)
        if scan is None or scan.deleted_at is None:
            raise HTTPException(status_code=404, detail="Không có tài liệu đã xoá này.")
        scan = scans.restore(scan)
        return DeletedScanItem(
            id=scan.id,
            title=scan.title,
            ma_dinh_danh=scan.ma_dinh_danh,
            page_count=scan.page_count,
            deleted_at=None,
            deleted_by=None,
        )

    @router.get("/api/user/documents/{scan_id}/pages", response_model=List[GiaPhaPageView])
    def list_scan_pages(
        scan_id: int,
        current_user: CurrentUser,
        version_id: Optional[int] = None,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> List[GiaPhaPageView]:
        """Từng trang của bộ gia phả: link ảnh tạm (chỉ khi ảnh đã lên MinIO) +
        chữ Hán / phiên âm / dịch nghĩa của version hiện tại (hoặc version_id).
        Chỉ chủ bộ hoặc admin — gia phả có thông tin nhạy cảm."""
        from app.documents.storage import ObjectStorage
        from app.workspace.page_images import is_storage_key

        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        version = versions.get(version_id) if version_id is not None else versions.get_current(scan.id)
        if version_id is not None and (version is None or version.user_scan_id != scan.id):
            raise HTTPException(status_code=404, detail="Không tìm thấy version.")
        contents = {c.page_id: c for c in pages_repo.list_content_for_version(version.id)} if version else {}
        storage = ObjectStorage.from_env()

        def image_url(key: Optional[str]) -> Optional[str]:
            if not is_storage_key(key) or not storage.config.enabled:
                return None
            try:
                return storage.get_presigned_url(key)
            except Exception:  # noqa: BLE001 — MinIO lỗi thì vẫn trả chữ
                return None

        result: List[GiaPhaPageView] = []
        for page in pages_repo.list_by_scan(scan.id):
            content = contents.get(page.id)
            result.append(
                GiaPhaPageView(
                    page_number=page.page_number,
                    image_url=image_url(page.image_file_key),
                    hannom_text=content.hannom_text if content else None,
                    transliteration_text=content.transliteration_text if content else None,
                    translation_text=content.translation_text if content else None,
                )
            )
        return result

    @router.get("/api/user/documents/{scan_id}/pages/{page_number}", response_model=GiaPhaPageDetail)
    def get_scan_page(
        scan_id: int,
        page_number: int,
        current_user: CurrentUser,
        version_id: Optional[int] = None,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> GiaPhaPageDetail:
        """1 trang đầy đủ: ảnh + chữ + OCR từng engine + vote. Tải theo trang
        (bộ lớn có tới 233 trang × 4 engine). Diff từng chữ tính lúc đọc
        (annotate_vote_diffs trên bản sao), không ghi DB. Chủ bộ hoặc admin."""
        import copy

        from app.documents.storage import ObjectStorage
        from app.hannom.vote_diff import annotate_vote_diffs
        from app.workspace.page_images import is_storage_key

        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        version = versions.get(version_id) if version_id is not None else versions.get_current(scan.id)
        if version is None or version.user_scan_id != scan.id:
            raise HTTPException(status_code=404, detail="Không tìm thấy version.")
        page = next((p for p in pages_repo.list_by_scan(scan.id) if p.page_number == page_number), None)
        if page is None:
            raise HTTPException(status_code=404, detail="Không có trang này.")
        content = next((c for c in pages_repo.list_content_for_version(version.id) if c.page_id == page.id), None)
        meta = copy.deepcopy(content.ocr_vote_meta) if content and isinstance(content.ocr_vote_meta, dict) else None
        if meta:
            annotate_vote_diffs(meta)
        image_url = None
        if is_storage_key(page.image_file_key):
            storage = ObjectStorage.from_env()
            if storage.config.enabled:
                try:
                    image_url = storage.get_presigned_url(page.image_file_key)
                except Exception:  # noqa: BLE001 — MinIO lỗi thì vẫn trả chữ/vote
                    image_url = None
        return GiaPhaPageDetail(
            page_number=page.page_number,
            image_url=image_url,
            hannom_text=content.hannom_text if content else None,
            transliteration_text=content.transliteration_text if content else None,
            translation_text=content.translation_text if content else None,
            ocr_vote_meta=meta,
            ocr_bbox=content.ocr_bbox if content and isinstance(content.ocr_bbox, list) else None,
        )

    @router.patch("/api/user/documents/{scan_id}/pages/{page_number}", response_model=GiaPhaPageEditResult)
    def edit_scan_page(
        scan_id: int,
        page_number: int,
        payload: GiaPhaPageEditRequest,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> GiaPhaPageEditResult:
        """Sửa tay chữ Hán / phiên âm / dịch nghĩa của 1 trang. KHÔNG ghi đè
        bản gốc: lần sửa đầu fork version mới (source="manual-edit", không đặt
        làm hiện tại); các lần sau gửi version_id đó để sửa tại chỗ. Muốn
        thành bản chính thì admin make-current. OCR/vote/bbox giữ nguyên làm
        bằng chứng (có thể không còn khớp chữ đã sửa). Chủ bộ hoặc admin."""
        if payload.hannom_text is None and payload.transliteration_text is None and payload.translation_text is None:
            raise HTTPException(status_code=400, detail="Không có nội dung nào để sửa.")
        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        page = next((p for p in pages_repo.list_by_scan(scan.id) if p.page_number == page_number), None)
        if page is None:
            raise HTTPException(status_code=404, detail="Không có trang này.")
        base = versions.get(payload.version_id) if payload.version_id is not None else versions.get_current(scan.id)
        if base is None or base.user_scan_id != scan.id:
            raise HTTPException(status_code=404, detail="Không tìm thấy version.")
        forked = base.source != MANUAL_EDIT_SOURCE
        target = base
        if forked:
            target = versions.create_derived_version(
                user_scan_id=scan.id,
                parent_version_id=base.id,
                source=MANUAL_EDIT_SOURCE,
                review_status=None,
                note=f"Sửa tay (từ v{base.version_number})",
                created_by=current_user.id,
                text_step_status=None,
            )
        content = pages_repo.upsert_content(
            version_id=target.id,
            page_id=page.id,
            hannom_text=payload.hannom_text,
            transliteration_text=payload.transliteration_text,
            translation_text=payload.translation_text,
        )
        if target.is_current:
            pages_repo.sync_flat_cache(scans, scan.id, target.id)
        return GiaPhaPageEditResult(
            version=_item_version_from(versions.get(target.id), versions.steps_for(target.id)),
            page=GiaPhaPageView(
                page_number=page.page_number,
                hannom_text=content.hannom_text,
                transliteration_text=content.transliteration_text,
                translation_text=content.translation_text,
            ),
            forked=forked,
        )

    @router.post("/api/user/documents/{scan_id}/pages/{page_number}/ocr", response_model=GiaPhaPageOcrResult)
    def ocr_scan_page(
        scan_id: int,
        page_number: int,
        payload: GiaPhaPageOcrRequest,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> GiaPhaPageOcrResult:
        """OCR lại 1 trang bằng Kim Hán Nôm (TỐN TIỀN, cần confirm_paid=true).
        Kết quả (chữ Hán + khung chữ) ghi vào version sửa tay — cùng cơ chế
        với PATCH pages/{n}: lần đầu fork version mới, không đặt làm hiện tại,
        bản gốc giữ nguyên. Vote cũ của trang bị xoá (không còn đúng). Phiên
        âm/dịch của trang giữ theo chữ cũ và được báo là chưa khớp. Chủ bộ
        hoặc admin."""
        from app.documents.storage import ObjectStorage, ObjectStorageError
        from app.hannom import engines as hannom_engines
        from app.workspace.page_images import is_storage_key

        if payload.engine != "kimhannom":
            raise HTTPException(status_code=400, detail="Hiện chỉ hỗ trợ engine kimhannom.")
        if not payload.confirm_paid:
            raise HTTPException(status_code=400, detail="OCR Kim Hán Nôm tốn tiền: cần xác nhận (confirm_paid=true).")
        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        page = next((p for p in pages_repo.list_by_scan(scan.id) if p.page_number == page_number), None)
        if page is None:
            raise HTTPException(status_code=404, detail="Không có trang này.")
        base = versions.get(payload.version_id) if payload.version_id is not None else versions.get_current(scan.id)
        if base is None or base.user_scan_id != scan.id:
            raise HTTPException(status_code=404, detail="Không tìm thấy version.")
        if not is_storage_key(page.image_file_key):
            raise HTTPException(status_code=409, detail="Ảnh trang này chưa lên MinIO nên chưa OCR được.")
        storage = ObjectStorage.from_env()
        if not storage.config.enabled:
            raise HTTPException(status_code=503, detail="Chưa cấu hình lưu trữ ảnh (MinIO).")
        try:
            image = storage.read_file_bytes(page.image_file_key)
        except ObjectStorageError as error:
            raise HTTPException(status_code=502, detail=f"Không đọc được ảnh: {error}") from error
        if not image:
            raise HTTPException(status_code=409, detail="File ảnh trên MinIO rỗng.")

        # Gọi OCR TRƯỚC khi tạo version: lỗi/không có chữ thì không để lại version rác.
        result = hannom_engines.run_kimhannom(image, page.image_file_key.rsplit("/", 1)[-1])
        text = "\n".join(result.lines).strip() if result else ""
        if not text:
            raise HTTPException(
                status_code=502,
                detail="Kim Hán Nôm không trả về chữ (kiểm tra token, hạn mức hoặc kết nối).",
            )
        bbox = result.bbox or []

        forked = base.source != MANUAL_EDIT_SOURCE
        target = base
        if forked:
            target = versions.create_derived_version(
                user_scan_id=scan.id,
                parent_version_id=base.id,
                source=MANUAL_EDIT_SOURCE,
                review_status=None,
                note=f"OCR lại trang {page_number} bằng Kim Hán Nôm (từ v{base.version_number})",
                created_by=current_user.id,
                text_step_status=None,
            )
        previous = next((c for c in pages_repo.list_content_for_version(target.id) if c.page_id == page.id), None)
        stale = bool(previous and (previous.transliteration_text or previous.translation_text))
        content = pages_repo.upsert_content(
            version_id=target.id,
            page_id=page.id,
            hannom_text=text,
            ocr_bbox=bbox,
            clear_vote_meta=True,
        )
        if target.is_current:
            pages_repo.sync_flat_cache(scans, scan.id, target.id)
        return GiaPhaPageOcrResult(
            version=_item_version_from(versions.get(target.id), versions.steps_for(target.id)),
            page=GiaPhaPageView(
                page_number=page.page_number,
                hannom_text=content.hannom_text,
                transliteration_text=content.transliteration_text,
                translation_text=content.translation_text,
            ),
            forked=forked,
            engine="kimhannom",
            box_count=len(bbox),
            downstream_stale=stale,
        )

    @router.put("/api/user/documents/{scan_id}/pages/{page_number}/image", response_model=GiaPhaPageImageResult)
    async def replace_scan_page_image(
        scan_id: int,
        page_number: int,
        current_user: CurrentUser,
        file: UploadFile = File(...),
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> GiaPhaPageImageResult:
        """Thay ảnh gốc của 1 trang. Ảnh mới lên MinIO với key MỚI rồi mới đổi
        key trong DB; object cũ giữ nguyên (không xoá) để hoàn tác. Loại ảnh
        xét theo chữ ký đầu file (jpg/png/webp/tiff), không theo tên file.
        Chữ và OCR của các version KHÔNG đổi — khung chữ cũ có thể không còn
        khớp ảnh mới, cần OCR lại. Chủ bộ hoặc admin."""
        import io
        import os

        from app.documents.storage import ObjectStorage, ObjectStorageError
        from app.workspace.page_images import replacement_image_key, sniff_image

        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        page = next((p for p in pages_repo.list_by_scan(scan.id) if p.page_number == page_number), None)
        if page is None:
            raise HTTPException(status_code=404, detail="Không có trang này.")
        storage = ObjectStorage.from_env()
        if not storage.config.enabled:
            raise HTTPException(status_code=503, detail="Chưa cấu hình lưu trữ ảnh (MinIO).")
        max_bytes = int(os.getenv("MINIO_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
        content = await file.read(max_bytes + 1)
        if not content:
            raise HTTPException(status_code=400, detail="File ảnh rỗng.")
        if len(content) > max_bytes:
            raise HTTPException(status_code=400, detail=f"Ảnh vượt giới hạn {max_bytes} byte.")
        kind = sniff_image(content)
        if kind is None:
            raise HTTPException(status_code=400, detail="Chỉ nhận ảnh JPG, PNG, WEBP hoặc TIFF.")
        ext, content_type = kind
        new_key = replacement_image_key(scan.id, page_number, ext)
        try:
            storage.upload_file(new_key, io.BytesIO(content), content_type=content_type, size=len(content))
        except ObjectStorageError as error:
            raise HTTPException(status_code=502, detail=f"Không tải ảnh lên được: {error}") from error
        previous = page.image_file_key
        page = pages_repo.set_image_key(page, new_key)
        try:
            image_url = storage.get_presigned_url(new_key)
        except ObjectStorageError:
            image_url = None
        contents = {c.page_id: c for c in pages_repo.list_content_for_version(
            versions.get_current(scan.id).id)} if versions.get_current(scan.id) else {}
        c = contents.get(page.id)
        return GiaPhaPageImageResult(
            page=GiaPhaPageView(
                page_number=page.page_number,
                image_url=image_url,
                hannom_text=c.hannom_text if c else None,
                transliteration_text=c.transliteration_text if c else None,
                translation_text=c.translation_text if c else None,
            ),
            previous_image_key=previous,
        )

    @router.post("/api/user/documents/{scan_id}/ma-dinh-danh/auto", response_model=MaDinhDanhAutoResult)
    def auto_ma_dinh_danh(
        scan_id: int,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> MaDinhDanhAutoResult:
        """Tự tạo mã định danh cho bộ chưa có mã: Gemini trích 5 thông tin từ
        bản dịch (tốn 1 lượt gọi Gemini). Bộ đã có mã → trả mã cũ, không gọi."""
        from app.workspace.ma_dinh_danh_auto import ensure_ma_dinh_danh

        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        scan, problems = ensure_ma_dinh_danh(scans, scan)
        return MaDinhDanhAutoResult(
            ma_dinh_danh=scan.ma_dinh_danh, ma_dinh_danh_nguon=scan.ma_dinh_danh_nguon, problems=problems
        )

    @router.get("/api/user/text-engines", response_model=List[str])
    def list_enabled_text_engines(_: CurrentUser) -> List[str]:
        """Engine phiên âm/dịch đang bật — để người dùng chọn khi bấm Chạy."""
        from app.config import _get_setting
        from app.hannom import text_engines

        return text_engines.enabled_engines(_get_setting(text_engines.SETTING_KEY))

    @router.post("/api/user/documents/{scan_id}/text-engine-runs", response_model=ItemVersion)
    def run_text_engine(
        scan_id: int,
        payload: TextEngineRunRequest,
        current_user: AdminUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> ItemVersion:
        """Xếp hàng 1 lần chạy engine phiên âm/dịch cho bộ gia phả (chạy nền,
        trả về ngay version mới với bước pending). CHỈ ADMIN (chốt 04/10/2026 —
        engine thật như kim_gemini gọi dịch vụ tốn tiền theo trang; trước đó ai
        mở được bộ gia phả cũng chạy được). Kết quả không cần duyệt."""
        from app.config import _get_setting
        from app.hannom import text_engines
        from app.hannom.text_engine_runner import (
            ENGINE_RESULT_REVIEW_STATUS,
            SOURCE_PREFIX,
            EngineJob,
            get_runner,
        )

        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        if payload.engine not in text_engines.enabled_engines(_get_setting(text_engines.SETTING_KEY)):
            raise HTTPException(status_code=400, detail=f"Engine '{payload.engine}' chưa được đăng ký hoặc đang tắt.")
        parent = versions.get_current(scan.id)
        pages = pages_repo.list_by_scan(scan.id)
        if parent is None or not pages:
            raise HTTPException(status_code=400, detail="Bộ gia phả chưa có trang/version — cần OCR trước.")
        contents = {c.page_id: c for c in pages_repo.list_content_for_version(parent.id)}
        wanted = set(payload.pages) if payload.pages else None
        job_pages = [
            (p.page_number, contents[p.id].hannom_text)
            for p in pages
            if (wanted is None or p.page_number in wanted) and p.id in contents and contents[p.id].hannom_text
        ]
        if not job_pages:
            raise HTTPException(status_code=400, detail="Không có trang nào có văn bản Hán Nôm để chạy.")
        version = versions.create_derived_version(
            user_scan_id=scan.id,
            parent_version_id=parent.id,
            source=SOURCE_PREFIX + payload.engine,
            review_status=ENGINE_RESULT_REVIEW_STATUS,
            note=f"{payload.engine}: đang chờ chạy {len(job_pages)} trang",
            created_by=current_user.id,
        )
        get_runner().submit(
            EngineJob(
                scan_id=scan.id,
                version_id=version.id,
                engine=payload.engine,
                pages=job_pages,
                page_ids={p.page_number: p.id for p in pages},
            )
        )
        return _item_version_from(version, versions.steps_for(version.id))

    @router.patch("/api/user/documents/{scan_id}/versions/{version_id}/review", response_model=ItemVersion)
    def review_imported_version(
        scan_id: int,
        version_id: int,
        payload: VersionReviewRequest,
        _: AdminUser,
        versions: GiaPhaVersionRepository = Depends(version_repo),
    ) -> ItemVersion:
        """Chỉ admin duyệt. Duyệt KHÔNG đổi version hiện tại — chỉ quyết định
        cặp câu của version này có vào dữ liệu train không."""
        version = versions.get(version_id)
        if version is None or version.user_scan_id != scan_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy version.")
        if version.source is None:
            raise HTTPException(status_code=400, detail="Chỉ duyệt được version nhập từ LLM.")
        updated = versions.set_review_status(version_id, payload.review_status)
        return _item_version_from(updated, versions.steps_for(updated.id))

    @router.post("/api/user/documents/{scan_id}/versions/{version_id}/make-current", response_model=ItemVersion)
    def make_version_current(
        scan_id: int,
        version_id: int,
        _: AdminUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> ItemVersion:
        """Chỉ admin: đặt 1 version có sẵn làm version hiện tại (không tạo bản
        sao như /clone) + đồng bộ cache phẳng của bộ (tab Trích xuất). Version
        engine đang chờ / đang chạy / lỗi → 400."""
        from app.hannom.text_engine_runner import SOURCE_PREFIX

        version = versions.get(version_id)
        if version is None or version.user_scan_id != scan_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy version.")
        steps = versions.steps_for(version.id)
        if (version.source or "").startswith(SOURCE_PREFIX):
            text_steps = [s.status for s in steps if s.step_type.value in ("transliteration", "translation")]
            if not text_steps or any(status != "done" for status in text_steps):
                raise HTTPException(status_code=400, detail="Engine chưa chạy xong (hoặc bị lỗi) — chưa đặt làm hiện tại được.")
        versions.set_current(scan_id, version.id)
        pages_repo.sync_flat_cache(scans, scan_id, version.id)  # commit cả set_current
        return _item_version_from(versions.get(version.id), versions.steps_for(version.id))

    @router.get("/api/admin/training-export", response_class=PlainTextResponse)
    def export_training_pairs(
        _: AdminUser,
        versions: GiaPhaVersionRepository = Depends(version_repo),
    ) -> PlainTextResponse:
        """JSONL các cặp câu đã duyệt: {scan_id, version_id, source, page, cn, sv, vi}."""
        import json as _json

        lines = [_json.dumps(row, ensure_ascii=False) for row in versions.approved_pairs()]
        return PlainTextResponse(
            "\n".join(lines) + ("\n" if lines else ""),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": 'attachment; filename="gia_pha_training_pairs.jsonl"'},
        )

    @router.post("/api/user/documents/{scan_id}/versions/{version_id}/clone", response_model=ItemVersion)
    def clone_gia_pha_version(
        scan_id: int,
        version_id: int,
        payload: GiaPhaVersionCloneRequest,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
    ) -> ItemVersion:
        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        source_version = versions.get(version_id)
        if source_version is None or source_version.user_scan_id != scan.id:
            raise HTTPException(status_code=404, detail="Không tìm thấy version nguồn.")
        new_version = versions.clone_version(version_id, created_by=current_user.id)
        if payload.make_current:
            versions.set_current(scan.id, new_version.id)
        return _item_version_from(new_version, versions.steps_for(new_version.id))

    @router.get("/api/user/stats", response_model=UserStatsResponse)
    def get_user_stats(
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> UserStatsResponse:
        cache_key = f"user_stats:{current_user.id}"
        cached = STATS_CACHE.get(cache_key)
        if cached is not None:
            return cached
        store = get_tree_store()
        history_repo = get_history_repo()
        try:
            trees = store.list_trees_by_user(current_user.id)
        except Exception as error:
            _raise_store_error(error)
        history_total = 0
        if history_repo.enabled:
            history_total, _ = history_repo.list_recent(1, user_id=current_user.id)
        result = UserStatsResponse(
            scanned_documents=scans.count_by_user(current_user.id),
            family_trees=len(trees),
            history_total=history_total,
        )
        STATS_CACHE.set(cache_key, result)
        return result

    @router.get("/api/user/documents", response_model=UserScanListResponse)
    def list_user_documents(
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> UserScanListResponse:
        items = scans.list_by_user(current_user.id)
        return UserScanListResponse(
            total=len(items),
            items=[UserScanResponse.model_validate(item) for item in items],
        )

    @router.post("/api/user/documents", response_model=UserScanResponse, status_code=status.HTTP_201_CREATED)
    def create_user_document(
        payload: UserScanCreateRequest,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> UserScanResponse:
        created = scans.create(
            user_id=current_user.id,
            title=payload.title,
            file_name=payload.file_name,
            file_type=payload.file_type,
            page_count=payload.page_count,
            source_text=payload.source_text,
            hannom_text=payload.hannom_text,
            transliteration_text=payload.transliteration_text,
            ocr_bbox=payload.ocr_bbox,
        )
        return UserScanResponse.model_validate(created)

    @router.get("/api/user/documents/{scan_id}", response_model=UserScanResponse)
    def get_user_document(
        scan_id: int,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> UserScanResponse:
        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        return UserScanResponse.model_validate(scan)

    @router.patch("/api/user/documents/{scan_id}", response_model=UserScanResponse)
    def update_user_document(
        scan_id: int,
        payload: UserScanUpdateRequest,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> UserScanResponse:
        scan = scans.get_accessible(current_user, scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")
        updated = scans.update(
            scan,
            title=payload.title,
            ocr_status=payload.ocr_status,
            tree_status=payload.tree_status,
            family_tree_id=payload.family_tree_id,
            request_id=payload.request_id,
            source_text=payload.source_text,
            source_file_key=payload.source_file_key,
            hannom_text=payload.hannom_text,
            transliteration_text=payload.transliteration_text,
            ocr_bbox=payload.ocr_bbox,
        )
        return UserScanResponse.model_validate(updated)

    @router.get("/api/user/family-trees", response_model=WorkspaceTreeListResponse)
    def list_user_family_trees(
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> WorkspaceTreeListResponse:
        store = get_tree_store()
        try:
            items = store.list_trees_by_user(current_user.id)
        except Exception as error:
            _raise_store_error(error)

        user_scans = {scan.family_tree_id: scan.title for scan in scans.list_by_user(current_user.id) if scan.family_tree_id}
        summaries = [
            _to_tree_summary(item, source_document_title=user_scans.get(item["id"]))
            for item in items
        ]
        return WorkspaceTreeListResponse(total=len(summaries), items=summaries)

    @router.post("/api/user/family-trees", response_model=WorkspaceTreeDocument, status_code=status.HTTP_201_CREATED)
    def create_user_family_tree(
        payload: UserFamilyTreeCreateRequest,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        db: Session = Depends(get_db),
    ) -> WorkspaceTreeDocument:
        store = get_tree_store()
        try:
            created = store.create_tree(
                name=payload.name,
                description=payload.description,
                nodes=payload.nodes,
                user_id=current_user.id,
                is_public=False,
                has_source_document=payload.source_scan_id is not None,
            )
        except Exception as error:
            _raise_store_error(error)

        source_title = None
        if payload.source_scan_id is not None:
            scan = scans.get_accessible(current_user, payload.source_scan_id)
            if scan is not None:
                source_title = scan.title
                scans.update(
                    scan,
                    tree_status=TreeStatus.CREATED,
                    family_tree_id=created["id"],
                )

        summary = _to_tree_summary(created, source_document_title=source_title)
        return WorkspaceTreeDocument(**summary.model_dump(), nodes=created.get("nodes", []))

    @router.get("/api/user/family-trees/{tree_id}", response_model=WorkspaceTreeDocument)
    def get_user_family_tree(tree_id: str, current_user: CurrentUser) -> WorkspaceTreeDocument:
        store = get_tree_store()
        try:
            item = store.get_tree(tree_id)
        except Exception as error:
            _raise_store_error(error)
        if item.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Bạn không có quyền xem cây gia phả này.")
        summary = _to_tree_summary(item)
        return WorkspaceTreeDocument(**summary.model_dump(), nodes=item.get("nodes", []))

    @router.get("/api/admin/stats", response_model=AdminStatsResponse)
    def get_admin_stats(
        _: AdminUser,
        users: UserRepository = Depends(user_repo),
        scans: UserScanRepository = Depends(scan_repo),
        db: Session = Depends(get_db),
    ) -> AdminStatsResponse:
        cached = STATS_CACHE.get("admin_stats")
        if cached is not None:
            return cached
        store = get_tree_store()
        history_repo = get_history_repo()
        try:
            all_trees = store.list_trees()
            public_trees = store.list_public_trees()
        except Exception as error:
            _raise_store_error(error)

        # Không tính bộ đã xoá mềm (trước đây đếm cả chúng).
        total_scans = scans.page_stats(None)["scans"]
        history_total = 0
        if history_repo.enabled:
            history_total, _ = history_repo.list_all(1)

        result = AdminStatsResponse(
            total_trees=len(all_trees),
            public_trees=len(public_trees),
            total_users=users.count_users(),
            total_scans=total_scans,
            history_total=history_total,
        )
        STATS_CACHE.set("admin_stats", result)
        return result

    @router.get("/api/public/hannom-progress", response_model=HannomProgressResponse)
    def get_hannom_progress(
        scans: UserScanRepository = Depends(scan_repo),
        db: Session = Depends(get_db),
    ) -> HannomProgressResponse:
        require_workspace_database()
        cached = STATS_CACHE.get("hannom_progress")
        if cached is not None:
            return cached
        from sqlalchemy import and_, case, select

        def has_text(column):
            # Chỉ hỏi "có chữ không" ngay trong SQL: KHÔNG kéo cả nội dung LONGTEXT (mỗi bộ hàng trăm KB)
            # về Python như trước — đó là lý do endpoint công khai này mất ~2,4 giây.
            return case((and_(column.is_not(None), column != ""), True), else_=False)

        # Query scans từ hannom-corpus import
        stmt = (
            select(
                UserScan.file_name,
                UserScan.title,
                UserScan.page_count,
                UserScan.ma_dinh_danh,
                has_text(UserScan.hannom_text).label("has_ocr"),
                has_text(UserScan.transliteration_text).label("has_translit"),
                has_text(UserScan.source_text).label("has_translation"),
            )
            .where(UserScan.request_id.like(f"{HANNOM_CORPUS_REQUEST_ID_PREFIX}%"), UserScan.deleted_at.is_(None))
        )
        rows = sorted(db.execute(stmt).all(), key=lambda r: r.file_name)

        total_books = len(rows)
        total_pages = sum(r.page_count for r in rows)
        pages_with_ocr = sum(r.page_count for r in rows if r.has_ocr)
        pages_with_transliteration = sum(r.page_count for r in rows if r.has_translit)
        pages_with_translation = sum(r.page_count for r in rows if r.has_translation)

        books = [
            HannomProgressItem(
                doc_id=r.file_name,
                title_vn=r.title,
                page_count=r.page_count,
                has_ocr=bool(r.has_ocr),
                has_transliteration=bool(r.has_translit),
                has_translation=bool(r.has_translation),
                ma_dinh_danh=r.ma_dinh_danh,
                flags=[],  # TODO: thêm flags từ corpus metadata
            )
            for r in rows
        ]

        ocr_pct = round(100 * pages_with_ocr / total_pages, 1) if total_pages > 0 else 0.0
        translit_pct = round(100 * pages_with_transliteration / total_pages, 1) if total_pages > 0 else 0.0
        trans_pct = round(100 * pages_with_translation / total_pages, 1) if total_pages > 0 else 0.0

        result = HannomProgressResponse(
            total_books=total_books,
            total_pages=total_pages,
            pages_with_ocr=pages_with_ocr,
            pages_with_transliteration=pages_with_transliteration,
            pages_with_translation=pages_with_translation,
            ocr_percent=ocr_pct,
            transliteration_percent=translit_pct,
            translation_percent=trans_pct,
            books=books,
        )
        STATS_CACHE.set("hannom_progress", result)
        return result

    @router.get("/api/admin/history")
    def list_admin_history(
        _: AdminUser,
        limit: int = 50,
    ) -> Dict[str, Any]:
        history_repo = get_history_repo()
        safe_limit = max(1, min(limit, 200))
        if history_repo.enabled:
            total, items = history_repo.list_all(safe_limit)
            return {"total": total, "items": items}
        return {"total": 0, "items": []}

    return router
