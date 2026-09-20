# Contributing to AdvisorOps

AdvisorOps is currently a portfolio/demo project. Contributions should preserve its product boundaries: simulated data only, explainable rules, complete Activity history, and human-confirmed interpretive AI changes.

## Local checks

Backend:

    cd backend
    uv sync --frozen
    uv run python -m compileall -q app tests
    uv run pytest -q

Frontend:

    cd frontend
    npm ci
    npm run typecheck
    npm run build

## Change guidelines

- Keep business rules out of React components and FastAPI route functions.
- Put SQL in repository.py rather than scattering queries through services.
- Preserve Customer Snapshot / Activity / WorkItem / Change Proposal separation.
- Do not turn Priority into a black-box AI score.
- Do not commit real customer data, local databases, uploaded attachments or credentials.
- New import aliases or normalization rules should include tests.
- Destructive operations require explicit UI confirmation.

## Commit style

- feat: new product capability
- fix: defect correction
- refactor: internal structure without product-behavior change
- test: tests only
- docs: documentation
- chore: repository / tooling maintenance

## Pull requests

A pull request should explain:

1. the user problem;
2. what behavior changed;
3. how it was validated;
4. whether data model, privacy or AI boundaries changed.
