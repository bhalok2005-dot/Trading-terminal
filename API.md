# API

## Authentication

- `POST /api/auth/register`
- `POST /api/auth/login`

## Accounts

- `GET /api/accounts`
- `POST /api/accounts`

## Trades

- `GET /api/trades`
- `POST /api/trades/import-demo`

## Analytics

- `GET /api/analytics/dashboard?account_id={id}` (optional account filter)
- `GET /api/analytics/summary`
- `GET /api/analytics/strategies`
- `GET /api/analytics/analyst`

## Risk

- `PUT /api/accounts/{account_id}/risk-rules`
- `GET /api/accounts/{account_id}/risk`

Risk assessments include daily loss, total loss, maximum drawdown, profit target, minimum trading days, consistency, position size, news restriction, and weekend restriction. A zero numeric threshold disables its check; zero minimum days also disables its progress check.

Consistency is measured as the largest positive UTC trading-day net profit divided by the sum of positive trading-day net profits. Weekend restriction checks whether an entry-to-exit interval includes Saturday or Sunday in UTC. News restriction is `not_evaluable` until a news calendar is connected. Missing timestamps can also make a check `not_evaluable`; minimum trading days remain `in_progress` until the configured count is reached. Loss and drawdown limits breach when reached; position-size and consistency limits breach only when exceeded. The assessment is `breached` if any limit is breached, `review_required` if an enabled check cannot be evaluated and none is breached, or `on_track` otherwise.

## Notes

- authenticated endpoints require a valid bearer token
- unauthorized access is rejected by the auth middleware
- zero-trade analytics safely return empty metrics
- R-multiple is returned as `N/A` when no valid risk amount exists
