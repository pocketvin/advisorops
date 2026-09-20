from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    BehaviorSignalRequest,
    ConsiderRequest,
    FollowUpRequest,
    PinRequest,
    RejectRequest,
)
from .service import CustomerNotFoundError, WorkbenchService


app = FastAPI(
    title="证券客户经营工作台 API",
    version="0.1.0",
    description="仅使用模拟数据的可解释客户经营工作流原型。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = WorkbenchService()


def _not_found(customer_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"客户 {customer_id} 不存在")


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "demo", "data": "simulated"}


@app.get("/api/meta")
def meta():
    return {
        "product_name": "客户经营工作台",
        "working_name": True,
        "positioning": "证券客户经理日常客户经营决策辅助原型",
        "data_notice": "全部客户均为模拟数据，不连接任何券商内部系统。",
        "compliance": [
            "优先级仅用于安排客户经理工作顺序",
            "涉及具体产品时需先完成投资者适当性核验",
            "所有客户动作保留人工确认",
            "不自动发送金融建议，不自动替客户做投资决策",
        ],
    }


@app.get("/api/workbench")
def workbench(limit: int = Query(default=12, ge=1, le=50)):
    return service.workbench(limit=limit)


@app.get("/api/customers")
def customers(
    search: str = "",
    stage: str = "",
    risk_level: str = "",
    intent: str = "",
    customer_level: str = "",
):
    return service.list_customers(
        search=search,
        stage=stage,
        risk_level=risk_level,
        intent=intent,
        customer_level=customer_level,
    )


@app.get("/api/customers/{customer_id}")
def customer_detail(customer_id: str):
    try:
        return service.detail(customer_id)
    except CustomerNotFoundError:
        raise _not_found(customer_id)


@app.post("/api/customers/{customer_id}/pin")
def set_pin(customer_id: str, payload: PinRequest):
    try:
        return service.set_pin(customer_id, payload.pinned)
    except CustomerNotFoundError:
        raise _not_found(customer_id)


@app.post("/api/customers/{customer_id}/reject")
def reject(customer_id: str, payload: RejectRequest):
    try:
        return service.reject(
            customer_id,
            feedback=payload.feedback,
            cooldown_days=payload.cooldown_days,
        )
    except CustomerNotFoundError:
        raise _not_found(customer_id)


@app.post("/api/customers/{customer_id}/consider")
def consider(customer_id: str, payload: ConsiderRequest):
    try:
        return service.mark_considering(
            customer_id,
            feedback=payload.feedback,
            follow_up_days=payload.follow_up_days,
        )
    except CustomerNotFoundError:
        raise _not_found(customer_id)


@app.post("/api/customers/{customer_id}/follow-ups")
def record_follow_up(customer_id: str, payload: FollowUpRequest):
    try:
        return service.record_follow_up(customer_id, payload.model_dump())
    except CustomerNotFoundError:
        raise _not_found(customer_id)


@app.post("/api/customers/{customer_id}/signals")
def add_signal(customer_id: str, payload: BehaviorSignalRequest):
    try:
        return service.add_behavior_signal(
            customer_id,
            asset_change_30d_pct=payload.asset_change_30d_pct,
            recent_product_interest=payload.recent_product_interest,
            recent_consult_topic=payload.recent_consult_topic,
        )
    except CustomerNotFoundError:
        raise _not_found(customer_id)


@app.post("/api/demo/reset")
def reset_demo():
    return service.reset_demo()
