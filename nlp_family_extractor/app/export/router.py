from __future__ import annotations

from typing import Any, Callable, Dict

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.auth.dependencies import AdminUser
from app.export.service import ExportFormat, FamilyTreeExportService
from app.family_tree_store import FamilyTreeNotFoundError, FamilyTreeStoreError, MySqlFamilyTreeStore


def _raise_store_error(error: Exception) -> None:
    if isinstance(error, FamilyTreeNotFoundError):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, FamilyTreeStoreError):
        raise HTTPException(status_code=400, detail=str(error)) from error
    raise HTTPException(status_code=500, detail=str(error)) from error


def create_export_router(
    *,
    get_tree: Callable[[str], Dict[str, Any]],
    get_public_tree: Callable[[str], Dict[str, Any]] | None = None,
) -> APIRouter:
    router = APIRouter(tags=["Export"])
    export_service = FamilyTreeExportService()

    def _export_response(doc: Dict[str, Any], fmt: ExportFormat) -> Response:
        content, filename, media_type = export_service.export(doc, fmt)
        return Response(
            content=content.encode("utf-8"),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get(
        "/api/family-trees/{tree_id}/export",
        summary="Xuất cây gia phả (admin)",
    )
    def export_family_tree_admin(
        tree_id: str,
        _: AdminUser,
        format: ExportFormat = Query(..., alias="format"),
    ) -> Response:
        try:
            doc = get_tree(tree_id)
        except Exception as error:
            _raise_store_error(error)
        return _export_response(doc, format)

    if get_public_tree is not None:

        @router.get(
            "/api/public/family-trees/{tree_id}/export",
            summary="Xuất cây gia phả công khai (D4 — chỉ is_public=true)",
        )
        def export_public_family_tree(
            tree_id: str,
            format: ExportFormat = Query(..., alias="format"),
        ) -> Response:
            try:
                doc = get_public_tree(tree_id)
            except Exception as error:
                _raise_store_error(error)
            return _export_response(doc, format)

    return router


def create_node_meta_router(
    *,
    get_tree_store: Callable[[], Any],
) -> APIRouter:
    router = APIRouter(tags=["Node meta"])

    def _meta_store():
        store = get_tree_store()
        primary = getattr(store, "_primary", store)
        if not isinstance(primary, MySqlFamilyTreeStore):
            raise HTTPException(status_code=503, detail="Node meta requires MySQL store.")
        return primary

    @router.get(
        "/api/family-trees/{tree_id}/nodes/{node_id}/meta",
        summary="VGP node meta (admin)",
    )
    def get_node_meta_admin(tree_id: str, node_id: int, _: AdminUser) -> Dict[str, Any]:
        try:
            meta = _meta_store().get_node_meta(tree_id, node_id)
        except Exception as error:
            _raise_store_error(error)
        if meta is None:
            raise HTTPException(status_code=404, detail="Node meta not found")
        return {"tree_id": tree_id, "node_id": node_id, "meta": meta}

    @router.get(
        "/api/family-trees/{tree_id}/node-meta",
        summary="Danh sách node meta của cây (admin)",
    )
    def list_node_meta_admin(tree_id: str, _: AdminUser) -> Dict[str, Any]:
        try:
            items = _meta_store().list_node_meta(tree_id)
        except Exception as error:
            _raise_store_error(error)
        return {"tree_id": tree_id, "total": len(items), "items": items}

    @router.get(
        "/api/public/family-trees/{tree_id}/nodes/{node_id}/meta",
        summary="VGP node meta (public)",
    )
    def get_public_node_meta(tree_id: str, node_id: int) -> Dict[str, Any]:
        store = get_tree_store()
        try:
            store.get_public_tree(tree_id)
            primary = getattr(store, "_primary", store)
            if not isinstance(primary, MySqlFamilyTreeStore):
                raise HTTPException(status_code=503, detail="Node meta requires MySQL store.")
            meta = primary.get_node_meta(tree_id, node_id)
        except Exception as error:
            _raise_store_error(error)
        if meta is None:
            raise HTTPException(status_code=404, detail="Node meta not found")
        return {"tree_id": tree_id, "node_id": node_id, "meta": meta}

    return router
