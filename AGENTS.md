# Project Instructions

## Product goal
Build a lightweight, explainable securities client-manager workbench prototype. It is not a brokerage CRM replacement and must never imply connection to CITIC Securities or any real brokerage internal system.

## Product principles
- V1 is rule-based, not machine-learning based.
- Customer relationship stage and daily work priority are separate concepts.
- Every priority contribution must be explainable in plain Chinese.
- Next Best Action is a workflow suggestion, not an investment recommendation.
- Product/service-specific discussion must remain gated by investor suitability and human confirmation.
- Never auto-send financial recommendations or auto-make investment decisions.
- Use simulated customer data only.

## Technical baseline
- Frontend: React + TypeScript + Vite.
- Backend: Python + FastAPI.
- Data: SQLite via Python sqlite3.
- Keep core priority logic framework-independent and unit-testable.

## Demo acceptance
1. Pinned active customer stays near the top.
2. Explicit rejection immediately lowers daily priority.
3. "Consider again" schedules a future follow-up; before due it falls back, at due it returns automatically.
4. New behavioral signals can raise priority with an explanation.
5. Recording a follow-up updates timeline, stage, next step, next-contact time, and priority.

## File placement
Project root: /Users/yu0/Workspace/10-Projects/Securities-Client-Workbench
Work files: /Users/yu0/Workspace/10-Projects/Securities-Client-Workbench/work
Project outputs: /Users/yu0/Workspace/10-Projects/Securities-Client-Workbench/outputs

Follow /Users/yu0/Workspace/80-System/file-governance/FILE-PLACEMENT.md and /Users/yu0/Workspace/AGENTS.md.
