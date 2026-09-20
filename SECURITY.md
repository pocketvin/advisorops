# Security

This repository is a demo prototype and must contain **simulated customer data only**.

## Do not commit

- API keys, tokens, passwords, certificates or private keys
- `.env` files with real credentials
- real brokerage customer data
- phone numbers, identity documents, securities account numbers or addresses
- local SQLite databases or model-provider logs containing sensitive inputs

Use environment variables or repository secrets for credentials.

## AI boundary

The V1 product treats AI output as a proposal, not an authoritative customer fact.

- KYC / identity / risk / suitability / account facts are authority-owned.
- Kimi K3 may propose interpretive relationship fields.
- Interpretive changes require human confirmation.
- The external AI Context Pack is whitelist-based and removes direct identifiers by default.

## Production note

This project does not claim production security or compliance readiness. A real brokerage deployment requires organization-approved identity, authorization, audit, data-retention, network, model-gateway and personal-information controls.
