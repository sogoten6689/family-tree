from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.database import database_enabled, get_db
from app.family_tree_store import FamilyTreeNotFoundError
from app.pipeline.models import PipelineStepId
from app.pipeline.schemas import (
    PipelineContextResponse,
    PipelineResponse,
    PipelineResyncRequest,
    PipelineRunAllResponse,
    PipelineSkipRequest,
    PipelineStepDetailResponse,
    PipelineStepResponse,
    PipelineStepUpdateRequest,
)
from app.pipeline.service import PipelineConflictError, PipelineService


def require_pipeline_database() -> None:
    if not database_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database chưa được cấu hình. Thiết lập biến môi trường MYSQL_*.",
        )


def create_pipeline_router(get_tree: Callable[[str], dict]) -> APIRouter:
    router = APIRouter(
        tags=["Pipeline"],
        dependencies=[Depends(require_pipeline_database)],
    )

    def get_service(db: Session = Depends(get_db)) -> PipelineService:
        return PipelineService(db, get_tree=get_tree)

    def _serialize_step(item) -> PipelineStepResponse:
        return PipelineStepResponse(
            step_id=item.step_id.value,
            status=item.status.value,
            skipped_reason=item.skipped_reason,
            input_ref=item.input_ref,
            output_ref=item.output_ref,
            content_hash=item.content_hash,
            error_message=item.error_message,
            manual_override=bool(item.manual_override),
            admin_note=item.admin_note,
            started_at=item.started_at,
            finished_at=item.finished_at,
            updated_at=item.updated_at,
            document_id=item.document_id,
        )

    def _to_response(
        family_tree_id: str,
        steps,
        context: PipelineContextResponse,
    ) -> PipelineResponse:
        return PipelineResponse(
            family_tree_id=family_tree_id,
            context=context,
            steps=[_serialize_step(item) for item in steps],
        )

    @router.get(
        "/api/family-trees/{tree_id}/pipeline",
        response_model=PipelineResponse,
        summary="Trạng thái pipeline 7 bước",
    )
    def get_pipeline(tree_id: str, service: PipelineService = Depends(get_service)) -> PipelineResponse:
        try:
            steps, context = service.get_pipeline(tree_id)
        except FamilyTreeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _to_response(tree_id, steps, context)

    @router.get(
        "/api/family-trees/{tree_id}/pipeline/{step_id}",
        response_model=PipelineStepDetailResponse,
        summary="Chi tiết một bước pipeline",
    )
    def get_pipeline_step(
        tree_id: str,
        step_id: str,
        service: PipelineService = Depends(get_service),
    ) -> PipelineStepDetailResponse:
        try:
            parsed_step = PipelineStepId(step_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid step_id: {step_id}") from exc
        try:
            item, artifact, context = service.get_step(tree_id, parsed_step)
        except FamilyTreeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Pipeline detail failed: {exc}") from exc
        base = _serialize_step(item)
        return PipelineStepDetailResponse(
            **base.model_dump(),
            artifact=artifact,
            context=context,
        )

    @router.patch(
        "/api/family-trees/{tree_id}/pipeline/{step_id}",
        response_model=PipelineStepResponse,
        summary="Cập nhật metadata một bước pipeline",
    )
    def update_pipeline_step(
        tree_id: str,
        step_id: str,
        req: PipelineStepUpdateRequest,
        _: AdminUser,
        service: PipelineService = Depends(get_service),
    ) -> PipelineStepResponse:
        try:
            parsed_step = PipelineStepId(step_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid step_id: {step_id}") from exc
        try:
            item = service.update_step(tree_id, parsed_step, req)
        except FamilyTreeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PipelineConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_step(item)

    @router.post(
        "/api/family-trees/{tree_id}/pipeline/resync",
        response_model=PipelineResponse,
        summary="Đồng bộ lại pipeline từ trạng thái cây",
    )
    def resync_pipeline(
        tree_id: str,
        req: PipelineResyncRequest,
        _: AdminUser,
        service: PipelineService = Depends(get_service),
        db: Session = Depends(get_db),
    ) -> PipelineResponse:
        parsed_step = None
        if req.step_id:
            try:
                parsed_step = PipelineStepId(req.step_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid step_id: {req.step_id}") from exc
        try:
            steps = service.resync_pipeline(tree_id, step_id=parsed_step)
            context = service.build_context(tree_id)
            db.commit()
        except FamilyTreeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _to_response(tree_id, steps, context)

    @router.post(
        "/api/family-trees/{tree_id}/pipeline/{step_id}/run",
        response_model=PipelineStepResponse,
        summary="Chạy một bước pipeline",
    )
    def run_pipeline_step(
        tree_id: str,
        step_id: str,
        _: AdminUser,
        service: PipelineService = Depends(get_service),
    ) -> PipelineStepResponse:
        try:
            parsed_step = PipelineStepId(step_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid step_id: {step_id}") from exc
        try:
            item = service.run_step(tree_id, parsed_step)
        except FamilyTreeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_step(item)

    @router.post(
        "/api/family-trees/{tree_id}/pipeline/{step_id}/skip",
        response_model=PipelineStepResponse,
        summary="Bỏ qua một bước pipeline",
    )
    def skip_pipeline_step(
        tree_id: str,
        step_id: str,
        req: PipelineSkipRequest,
        _: AdminUser,
        service: PipelineService = Depends(get_service),
    ) -> PipelineStepResponse:
        try:
            parsed_step = PipelineStepId(step_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid step_id: {step_id}") from exc
        try:
            item = service.skip_step(tree_id, parsed_step, reason=req.reason)
        except FamilyTreeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_step(item)

    @router.post(
        "/api/family-trees/{tree_id}/pipeline/run-all",
        response_model=PipelineRunAllResponse,
        summary="Chạy tuần tự các bước chưa xong",
    )
    def run_all_pipeline_steps(
        tree_id: str,
        _: AdminUser,
        service: PipelineService = Depends(get_service),
    ) -> PipelineRunAllResponse:
        try:
            result = service.run_all(tree_id)
        except FamilyTreeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return PipelineRunAllResponse(family_tree_id=tree_id, **result)

    return router
