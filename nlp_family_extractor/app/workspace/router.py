from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser, CurrentUser
from app.auth.user_repository import UserRepository
from app.database import database_enabled, get_db
from app.documents.repository import DocumentRepository
from app.documents.schemas import DocumentListResponse, DocumentResponse
from app.documents.storage import ObjectStorage
from app.family_tree_store import FamilyTreeNotFoundError, FamilyTreeStoreError
from app.workspace.models import OcrStatus, TreeStatus
from app.workspace.repository import UserScanRepository
from app.workspace.utils import compute_generation_count


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


class UserScanListResponse(BaseModel):
    total: int
    items: List[UserScanResponse]


class UserScanCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    file_name: str = Field(min_length=1, max_length=255)
    file_type: str = Field(default="unknown", max_length=64)
    page_count: int = Field(default=1, ge=1)
    source_text: Optional[str] = None


class UserScanUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    ocr_status: Optional[OcrStatus] = None
    tree_status: Optional[TreeStatus] = None
    family_tree_id: Optional[str] = None
    request_id: Optional[str] = None
    source_text: Optional[str] = None


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
        source_document_title=source_document_title,
    )


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
        )
        return UserScanResponse.model_validate(created)

    @router.get("/api/user/documents/{scan_id}", response_model=UserScanResponse)
    def get_user_document(
        scan_id: int,
        current_user: CurrentUser,
        scans: UserScanRepository = Depends(scan_repo),
    ) -> UserScanResponse:
        scan = scans.get_for_user(current_user.id, scan_id)
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
        scan = scans.get_for_user(current_user.id, scan_id)
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
            scan = scans.get_for_user(current_user.id, payload.source_scan_id)
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
