from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import InteractionRequest
from .service import (
    CustomerNotFoundError,
    InvalidWorkStateError,
    WorkbenchService,
    WorkItemNotFoundError,
)


app = FastAPI(
    title="证券客户经营工作台 API",
    version="0.2.0",
    description="仅使用模拟数据的客户经营工作流原型。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = WorkbenchService()


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (CustomerNotFoundError, WorkItemNotFoundError)):
        return HTTPException(status_code=404, detail="目标记录不存在")
    if isinstance(exc, InvalidWorkStateError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="未处理的服务错误")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": "phase-1-demo",
        "data": "simulated",
    }


@app.get("/api/meta")
def meta():
    return {
        "product_name": "客户经营工作台",
        "working_name": True,
        "positioning": "证券客户经理日常客户经营辅助原型",
        "data_notice": "全部客户均为模拟数据，不连接任何券商内部系统。",
        "ai_status": "本阶段尚未接 AI；结构化字段由客户经理确认。",
        "compliance": [
            "发现区优先级仅用于安排客户经理工作顺序",
            "涉及具体产品时仍需遵循真实机构适当性流程",
            "客户状态变化保留人工确认与活动记录",
            "不自动发送金融建议，不自动替客户做投资决策",
        ],
    }


@app.get("/api/workbench")
def workbench():
    return service.workbench()


@app.get("/api/customers/{customer_id}")
def customer_detail(customer_id: str):
    try:
        return service.customer_detail(customer_id)
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/discovery/{customer_id}/start")
def start_work(customer_id: str):
    try:
        return service.start_work(customer_id)
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/work-items/{work_item_id}/interactions")
def record_interaction(work_item_id: int, payload: InteractionRequest):
    try:
        return service.record_interaction(work_item_id, payload.model_dump())
    except Exception as exc:
        raise _http_error(exc)


@app.post("/api/demo/reset")
def reset_demo():
    return service.reset_demo()
