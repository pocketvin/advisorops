# Project Instructions

## Current phase

AdvisorOps v0.6 is implemented and is now in GitHub-readiness / user-experience iteration.

The docs under `docs/` remain the architecture source of truth. Preserve the completed V1 boundaries: simulated customers, deterministic Discovery/Priority rules, complete Activity history, WorkItem state, human-confirmed AI Change Proposals, and no implication of real brokerage-system integration.

## Product goal

Build AdvisorOps, a lightweight, explainable securities client-manager workbench prototype. It is not a brokerage CRM replacement and must never imply connection to CITIC Securities or any real brokerage internal system.

## Product model

- Work Area: work already accepted by the relationship manager.
- Discovery Area: customers for whom a new actionable reason currently exists.
- Customer Activity: full interaction/event history from manual or external sources.
- Current Snapshot: confirmed current customer operating state.
- Work Item: one currently executable piece of relationship-management work.
- Change Proposal: AI/rules may propose interpretive field changes; human confirmation applies them.

## Product principles

- V1 is rule-based, not machine-learning based.
- Customer relationship stage, follow-up state, and daily work state are separate concepts.
- Every priority contribution must be explainable in plain Chinese.
- Priority means work-order priority, not conversion probability or investment value.
- Recently contacted customers are suppressed only when there is no new actionable reason.
- Preserve full activity history; never replace it with only extracted fields.
- Next Best Action is a workflow suggestion, not an investment recommendation.
- Product/service-specific discussion remains gated by suitability and human confirmation.
- Never auto-send financial recommendations or auto-make investment decisions.
- Use simulated customer data only.

## Import and destructive actions

- CSV import must always preview normalized data before commit.
- Existing customer IDs are not overwritten by default.
- Batch deletion requires explicit confirmation and cleans cascaded local records/unused attachments.
- Import/export examples must remain simulated and free of direct identifiers.

## AI principle

AI understands and summarizes; deterministic rules enforce key constraints; humans make the final decision.

AI must not silently overwrite authority-owned customer facts.

## Planned technical baseline

- Frontend: React + TypeScript + Vite.
- Server state: TanStack Query.
- Backend: Python + FastAPI.
- Models/data access: Python sqlite3 + a thin repository layer for V1.
- Data: SQLite with WAL for V1.
- Validation: pytest, TypeScript typecheck, production build, API/live-browser smoke.
- Keep rule logic framework-independent and unit-testable.

Do not introduce Redis, Celery, Kafka, vector databases, microservices, or autonomous agent infrastructure without a concrete demonstrated need.

## Source of truth

Read before implementation:

1. `docs/PRODUCT-MODEL.md`
2. `docs/ARCHITECTURE.md`
3. `docs/FLOWS.md`
4. `docs/DATA-MODEL.md`
5. `docs/IMPLEMENTATION-PLAN.md`

## Git

- main should end each completed task clean.
- Do not push without explicit user authorization.
- Do not commit secrets, .env, real customer data, or local DB files.
- Use small descriptive commits.

## File placement

Project root: /Users/yu0/Workspace/10-Projects/Securities-Client-Workbench
Work files: /Users/yu0/Workspace/10-Projects/Securities-Client-Workbench/work
Project outputs: /Users/yu0/Workspace/10-Projects/Securities-Client-Workbench/outputs

Follow /Users/yu0/Workspace/80-System/file-governance/FILE-PLACEMENT.md and /Users/yu0/Workspace/AGENTS.md.
