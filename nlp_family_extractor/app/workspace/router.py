from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
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
from app.workspace.llm_import import add_coverage_warnings, parse_import
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository, UserScanRepository
from app.workspace.utils import compute_generation_count

# Phải khớp đúng tools/import_hannom_bilingual_corpus.py:REQUEST_ID_PREFIX
HANNOM_CORPUS_REQUEST_ID_PREFIX = "hannom-corpus:"


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
    title: str
    status: str  # "built" | "pending"
    is_public: Optional[bool] = None
    updated_at: str
    scan_id: Optional[int] = None
    tree_id: Optional[str] = None
    node_count: Optional[int] = None
    current_version: Optional[ItemVersion] = None


class GiaPhaListResponse(BaseModel):
    total: int
    items: List[GiaPhaItem]


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


def _scan_to_gia_pha_item(scan: UserScan, version_repo: GiaPhaVersionRepository) -> GiaPhaItem:
    gia_pha_id, pending = _scan_display_id(scan)
    current_version = None
    if scan.current_version_id:
        version = version_repo.get(scan.current_version_id)
        if version is not None:
            current_version = _item_version_from(version, version_repo.steps_for(version.id))
    return GiaPhaItem(
        id=gia_pha_id,
        ma_dinh_danh_pending=pending,
        ma_dinh_danh_nguon=scan.ma_dinh_danh_nguon,
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
) -> GiaPhaItem:
    """Cây đã dựng. Mã hiển thị lấy từ bộ gia phả nguồn (scan) — trước đây
    dùng id kỹ thuật của cây và ghi sai ma_dinh_danh_pending=False. Cây không
    có bộ nguồn → id cây + pending=True (chưa có mã chính thức).
    expose_scan=False (khách): chỉ hiện mã, không lộ scan_id/version riêng tư."""
    display_id, pending = _scan_display_id(source_scan) if source_scan else (tree["id"], True)
    current_version = None
    if expose_scan and source_scan is not None and version_repo is not None and source_scan.current_version_id:
        version = version_repo.get(source_scan.current_version_id)
        if version is not None:
            current_version = _item_version_from(version, version_repo.steps_for(version.id))
    return GiaPhaItem(
        id=display_id,
        ma_dinh_danh_pending=pending,
        ma_dinh_danh_nguon=source_scan.ma_dinh_danh_nguon if source_scan else None,
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
                    file_item.download_url = storage.presigned_get_url(file_item.file_key)
            items.append(response)
        return DocumentListResponse(total=len(items), items=items)

    @router.get("/api/gia-pha", response_model=GiaPhaListResponse)
    def list_gia_pha(
        current_user: OptionalUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
    ) -> GiaPhaListResponse:
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
        items = [
            _tree_to_gia_pha_item(
                tree, source_scans.get(tree["id"]), versions, expose_scan=current_user is not None
            )
            for tree in trees
        ]
        items.extend(_scan_to_gia_pha_item(scan, versions) for scan in pending_scans)
        return GiaPhaListResponse(total=len(items), items=items)

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
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
        versions: GiaPhaVersionRepository = Depends(version_repo),
        pages_repo: GiaPhaPageRepository = Depends(page_repo),
    ) -> ItemVersion:
        """Xếp hàng 1 lần chạy engine phiên âm/dịch cho bộ gia phả (chạy nền,
        trả về ngay version mới với bước pending). Ai mở được bộ gia phả thì
        chạy được (đã chốt). Kết quả không cần duyệt."""
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
        store = get_tree_store()
        history_repo = get_history_repo()
        try:
            trees = store.list_trees_by_user(current_user.id)
        except Exception as error:
            _raise_store_error(error)
        history_total = 0
        if history_repo.enabled:
            history_total, _ = history_repo.list_recent(1, user_id=current_user.id)
        return UserStatsResponse(
            scanned_documents=scans.count_by_user(current_user.id),
            family_trees=len(trees),
            history_total=history_total,
        )

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
        store = get_tree_store()
        history_repo = get_history_repo()
        try:
            all_trees = store.list_trees()
            public_trees = store.list_public_trees()
        except Exception as error:
            _raise_store_error(error)

        from sqlalchemy import func, select
        from app.workspace.models import UserScan

        total_scans = int(db.scalar(select(func.count()).select_from(UserScan)) or 0)
        history_total = 0
        if history_repo.enabled:
            history_total, _ = history_repo.list_all(1)

        return AdminStatsResponse(
            total_trees=len(all_trees),
            public_trees=len(public_trees),
            total_users=users.count_users(),
            total_scans=total_scans,
            history_total=history_total,
        )

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
