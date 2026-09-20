from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .ai_client import KimiError, KimiUnavailableError
from .attachments import attachments_dir
from .schemas import (
    AIExtractRequest,
    BulkDeleteCustomersRequest,
    ContextPackRequest,
    CustomerImportRequest,
    DeferRequest,
    DemoTimeRequest,
    InteractionRequest,
    PinRequest,
    QuickRecordPrepareRequest,
)
from .service import (
    CustomerNotFoundError,
    InvalidWorkStateError,
    ProposalNotFoundError,
    WorkbenchService,
    WorkItemNotFoundError,
)


app = FastAPI(
    title="AdvisorOps API",
    version="0.6.0",
    description="仅使用模拟数据的客户经营工作流原型。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/attachments",
    StaticFiles(directory=str(attachments_dir()), check_dir=False),
    name="attachments",
)

service = WorkbenchService()


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(
        exc,
        (
            CustomerNotFoundError,
            WorkItemNotFoundError,
            ProposalNotFoundError,
        ),
    ):
        return HTTPException(status_code=404, detail="目标记录不存在")
    if isinstance(exc, InvalidWorkStateError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, KimiUnavailableError):
        return HTTPException(status_code=503, detail="智能整理服务尚未配置，可继续手工记录")
    if isinstance(exc, KimiError):
        return HTTPException(status_code=502, detail="智能整理服务暂时不可用，可继续手工记录")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="未处理的服务错误")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": "demo",
        "data": "simulated",
    }


@app.get("/api/meta")
def meta():
    return service.meta()


@app.get("/api/workbench")
def workbench():
    return service.workbench()


@app.get("/api/customers")
def customers(
    search: str = "",
    stage: str = "",
    risk_level: str = "",
    intent: str = "",
    customer_level: str = "",
    total_assets_band: str = "",
    sort_by: str = "priority",
):
    return service.customers(
        search=search,
        stage=stage,
        risk_level=risk_level,
        intent=intent,
        customer_level=customer_level,
        total_assets_band=total_assets_band,
        sort_by=sort_by,
    )


@app.get("/api/customers/import-template")
def customer_import_template():
    return Response(
        content=service.customer_import_template(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                'attachment; filename="advisorops-customer-import-template.csv"'
            )
        },
    )


@app.get("/api/customers/import-sample")
def customer_import_sample():
    return Response(
        content=service.customer_import_sample(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                'attachment; filename="advisorops-customer-import-sample.csv"'
            )
        },
    )


@app.post("/api/customers/import/preview")
def customer_import_preview(payload: CustomerImportRequest):
    try:
        return service.preview_customer_import(payload.csv_text)
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/customers/import/commit")
def customer_import_commit(payload: CustomerImportRequest):
    try:
        return service.commit_customer_import(payload.csv_text)
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/customers/bulk-delete")
def customer_bulk_delete(payload: BulkDeleteCustomersRequest):
    try:
        return service.bulk_delete_customers(
            payload.customer_ids,
            confirm=payload.confirm,
        )
    except Exception as exc:
        raise _http_error(exc)


@app.get("/api/customers/{customer_id}")
def customer_detail(customer_id: str):
    try:
        return service.customer_detail(customer_id)
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/quick-record/prepare")
def quick_record_prepare(payload: QuickRecordPrepareRequest):
    try:
        return service.quick_record_prepare(
            raw_content=payload.raw_content,
            channel=payload.channel,
            attachments=[item.model_dump() for item in payload.attachments],
        )
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/customers/{customer_id}/manual-work")
def manual_work(customer_id: str):
    try:
        return service.ensure_manual_work(customer_id)
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/customers/{customer_id}/pin")
def pin_customer(customer_id: str, payload: PinRequest):
    try:
        return service.set_pin(customer_id, payload.pinned)
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/customers/{customer_id}/defer")
def defer_customer(customer_id: str, payload: DeferRequest):
    try:
        return service.defer_customer(
            customer_id,
            days=payload.days,
            next_contact_at=payload.next_contact_at,
        )
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/discovery/{customer_id}/start")
def start_work(customer_id: str):
    try:
        return service.start_work(customer_id)
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/customers/{customer_id}/ai/extract")
def ai_extract(customer_id: str, payload: AIExtractRequest):
    try:
        return service.ai_extract_interaction(
            customer_id,
            raw_content=payload.raw_content,
            channel=payload.channel,
            attachments=[item.model_dump() for item in payload.attachments],
        )
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/customers/{customer_id}/ai/brief")
def ai_brief(customer_id: str):
    try:
        return service.ai_customer_brief(customer_id)
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/customers/{customer_id}/ai-context")
def ai_context(customer_id: str, payload: ContextPackRequest):
    try:
        return service.ai_context(
            customer_id,
            question=payload.question,
        )
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/work-items/{work_item_id}/interactions")
def record_interaction(work_item_id: int, payload: InteractionRequest):
    try:
        return service.record_interaction(work_item_id, payload.model_dump())
    except Exception as exc:
        raise _http_error(exc)


@app.get("/api/activities")
def activity_feed(limit: int = Query(default=50, ge=1, le=100)):
    return service.activity_feed(limit=limit)


@app.post("/api/change-proposals/{proposal_id}/apply")
def apply_proposal(proposal_id: int):
    try:
        return service.apply_change_proposal(proposal_id)
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/change-proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: int):
    try:
        return service.reject_change_proposal(proposal_id)
    except Exception as exc:
        raise _http_error(exc)


@app.get("/api/sync/status")
def sync_status():
    return service.sync_status()


@app.post("/api/sync/refresh")
def sync_refresh():
    return service.refresh_sources()


@app.post("/api/demo/time")
def demo_time(payload: DemoTimeRequest):
    return service.advance_demo_time(days=payload.days, hours=payload.hours)


@app.post("/api/demo/reset")
def reset_demo():
    return service.reset_demo()
