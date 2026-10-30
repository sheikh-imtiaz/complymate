# Billing and plan limits — requirements

## User story

As a firm owner I want simple plans with clear limits so I pay for what my firm needs.

## Acceptance criteria (EARS)

1. Plans SHALL be Solo A$79/mo (2 users), Practice A$249/mo (10 users), onboarding A$299 one-off; 14-day trial.
2. THE SYSTEM SHALL use Stripe Checkout and the customer portal; webhooks SHALL update plan, status and seats idempotently.
3. THE SYSTEM SHALL meter agent turns, documents, clients and users per month, warn at 80% and block above the limit.
4. Practice-only features (custom roles, IP allow-list, scheduled reports, API keys) SHALL be gated by plan.

## Out of scope

* Legal advice. ComplyMate provides general information; firms make their own decisions.
