# Database design

## Core tables

- users
- accounts
- trades
- risk_rules
- sync_logs

## Notes

- all timestamps are stored in UTC internally
- trade duplication is prevented with a per-account external trade ID constraint
- account access is restricted by user ownership
- risk rules are configurable per account

## Example schema

- `users`: `id`, `email`, `hashed_password`, `created_at`
- `accounts`: `id`, `user_id`, `name`, `broker`, `currency`, `initial_balance`, `current_balance`, `status`
- `trades`: `id`, `account_id`, `external_trade_id`, `symbol`, `side`, `net_profit`, `risk_amount`, `r_multiple`, `strategy_id`, `session`
- `risk_rules`: `id`, `account_id`, `daily_loss_limit`, `max_drawdown`, `position_size_limit`
- `sync_logs`: `id`, `account_id`, `started_at`, `ended_at`, `trades_fetched`, `inserted`, `updated`, `status`

## Data integrity

- foreign keys are enforced in the relational model
- duplicate imports are prevented at the database level
- trade changes are safely upserted through account+external ID matching
