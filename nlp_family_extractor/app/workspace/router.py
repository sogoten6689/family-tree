from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
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


class ItemVersion(BaseModel):
    version_id: int
    version_number: int
    is_current: bool
    ocr_engines: Optional[List[str]] = None
    status: str
    steps: List[ItemVersionStep] = Field(default_factory=list)


class GiaPhaItem(BaseModel):
    id: str
    ma_dinh_danh_pending: bool = False
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
        steps=[ItemVersionStep(step_type=s.step_type.value, status=s.status) for s in steps],
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
        title=scan.title,
        status="built" if scan.tree_status == TreeStatus.CREATED else "pending",
        updated_at=scan.uploaded_at.isoformat(),
        scan_id=scan.id,
        tree_id=scan.family_tree_id,
        current_version=current_version,
    )


def _tree_to_gia_pha_item(tree: Dict[str, Any]) -> GiaPhaItem:
    return GiaPhaItem(
        id=tree["id"],
        ma_dinh_danh_pending=False,
        title=tree["name"],
        status="built",
        is_public=bool(tree.get("is_public")),
        updated_at=tree["updated_at"],
        tree_id=tree["id"],
        node_count=tree.get("node_count"),
        current_version=None,
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

        items = [_tree_to_gia_pha_item(tree) for tree in trees]
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
