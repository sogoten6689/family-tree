from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.database import database_enabled, get_db
from app.family_tree_store import FamilyTreeNotFoundError
from app.pipeline.models import PipelineStepId
from app.pipeline.schemas import (
    PipelineResponse,
    PipelineRunAllResponse,
    PipelineSkipRequest,
    PipelineStepResponse,
)
from app.pipeline.service import PipelineService


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

    def _to_response(family_tree_id: str, steps) -> PipelineResponse:
        return PipelineResponse(
            family_tree_id=family_tree_id,
            steps=[
                PipelineStepResponse(
                    step_id=item.step_id.value,
                    status=item.status.value,
                    skipped_reason=item.skipped_reason,
                    input_ref=item.input_ref,
                    output_ref=item.output_ref,
                    content_hash=item.content_hash,
                    error_message=item.error_message,
                    started_at=item.started_at,
                    finished_at=item.finished_at,
                    updated_at=item.updated_at,
                    document_id=item.document_id,
                )
                for item in steps
            ],
        )

    @router.get(
        "/api/family-trees/{tree_id}/pipeline",
        response_model=PipelineResponse,
        summary="Trạng thái pipeline 7 bước",
    )
    def get_pipeline(tree_id: str, service: PipelineService = Depends(get_service)) -> PipelineResponse:
        try:
            steps = service.get_pipeline(tree_id)
        except FamilyTreeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _to_response(tree_id, steps)

    @router.post(
        "/api/family-trees/{tree_id}/pipeline/{step_id}/run",
        response_model=PipelineStepResponse,
        summary="Chạy một bước pipeline",
    )
    def run_pipeline_step(
        tree_id: str,
        step_id: str,
        service: PipelineService = Depends(get_service),
        _: AdminUser,
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
        return PipelineStepResponse(
            step_id=item.step_id.value,
            status=item.status.value,
            skipped_reason=item.skipped_reason,
            input_ref=item.input_ref,
            output_ref=item.output_ref,
            content_hash=item.content_hash,
            error_message=item.error_message,
            started_at=item.started_at,
            finished_at=item.finished_at,
            updated_at=item.updated_at,
            document_id=item.document_id,
        )

    @router.post(
        "/api/family-trees/{tree_id}/pipeline/{step_id}/skip",
        response_model=PipelineStepResponse,
        summary="Bỏ qua một bước pipeline",
    )
    def skip_pipeline_step(
        tree_id: str,
        step_id: str,
        req: PipelineSkipRequest,
        service: PipelineService = Depends(get_service),
        _: AdminUser,
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
        return PipelineStepResponse(
            step_id=item.step_id.value,
            status=item.status.value,
            skipped_reason=item.skipped_reason,
            input_ref=item.input_ref,
            output_ref=item.output_ref,
            content_hash=item.content_hash,
            error_message=item.error_message,
            started_at=item.started_at,
            finished_at=item.finished_at,
            updated_at=item.updated_at,
            document_id=item.document_id,
        )

    @router.post(
        "/api/family-trees/{tree_id}/pipeline/run-all",
        response_model=PipelineRunAllResponse,
        summary="Chạy tuần tự các bước chưa xong",
    )
    def run_all_pipeline_steps(
        tree_id: str,
        service: PipelineService = Depends(get_service),
        _: AdminUser,
    ) -> PipelineRunAllResponse:
        try:
            result = service.run_all(tree_id)
        except FamilyTreeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return PipelineRunAllResponse(family_tree_id=tree_id, **result)

    return router
