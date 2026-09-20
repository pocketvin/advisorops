# Security

AdvisorOps is a portfolio/demo prototype and must contain **simulated customer data only**.

## Do not commit

- API keys, tokens, passwords, certificates or private keys
- `.env` files with real credentials
- real brokerage customer data
- phone numbers, identity documents, securities account numbers or bank account numbers
- precise home addresses
- local SQLite databases, uploaded attachments or model-provider logs containing sensitive inputs

Use local environment variables or repository secrets for credentials.

## AI boundary

AI output is treated as a proposal, not an authoritative customer fact.

- KYC / identity / risk / suitability / account facts are authority-owned.
- AI may summarize interactions and propose interpretive relationship fields.
- Interpretive changes require human confirmation.
- The external AI Context Pack is whitelist-based and removes direct identifiers by default.
- The UI does not expose provider/API details.

## Import boundary

CSV import intentionally excludes direct identity and account fields. The public template is designed for coarse customer-operation context only. Exact addresses or account identifiers should not be placed in demo files.

## Reporting

For a public GitHub repository, security issues should be reported through a private security advisory when possible rather than by posting credentials or sensitive data in a public issue.

## Production note

This project does not claim production security or regulatory readiness. A real brokerage deployment requires organization-approved identity, authorization, audit, data-retention, network, model-gateway and personal-information controls.
