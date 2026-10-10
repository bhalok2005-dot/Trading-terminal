# Architecture

## Overview

The platform follows a layered architecture:

Trading Account
↓
Connector / uploader
↓
Trade normalizer
↓
PostgreSQL storage
↓
Analytics + risk services
↓
FastAPI REST API
↓
Next.js dashboard

## Modules

### Backend

- `backend/app/main.py`: API entry point, auth, dashboard routes
- `backend/app/models.py`: SQLAlchemy schema
- `backend/app/services/analytics.py`: KPI, drawdown, and R-multiple logic
- `backend/app/seed_demo.py`: demo data creation
- `backend/app/security.py`: JWT and password hashing

### Frontend

- `frontend/app/page.tsx`: trading dashboard UI
- `frontend/app/layout.tsx`: app shell and metadata
- `frontend/app/globals.css`: dark trading terminal styling

## Design principles

- universal account and trade model
- no direct broker password exposure to frontend
- user-scoped auth and account access
- analytics computed from normalized trade rows
- simple connector extension points for future MT4/MT5/csv adapters
