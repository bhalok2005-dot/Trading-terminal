# Trading Intelligence Dashboard

A production-minded MVP for a multi-account trading analytics platform built with FastAPI and Next.js.

## Overview

This project follows a universal connector architecture and normalizes trading data into a single internal model before storing it in PostgreSQL. The MVP includes:

- user authentication
- account management
- trade import and demo seeding
- analytics and drawdown calculations
- dashboard UI with KPI cards and equity curve
- secure environment and deployment configuration

## Stack

- Backend: FastAPI, SQLAlchemy, Pydantic
- Frontend: Next.js 16, React 19, Tailwind CSS
- Database: PostgreSQL (Docker local, managed production)
- Deployment: Vercel + Render/Railway/Fly.io

## Local setup

1. Copy `.env.example` to `.env` and update values.
2. Start PostgreSQL with Docker:
   `docker compose up -d db`
3. Install backend dependencies:
   `python -m pip install -r backend/requirements.txt`
4. Install frontend dependencies:
   `cd frontend && npm install`
5. Start backend:
   `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
6. Start frontend:
   `cd frontend && npm run dev`
7. Open http://localhost:3000

## Environment variables

See `.env.example`.

Required variables:

- DATABASE_URL
- JWT_SECRET
- AI_API_KEY
- MT5_CONFIG
- NEXT_PUBLIC_API_URL
- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD

## Demo data

The backend includes a seeded demo account and demo trades via the auth flow. This is clearly isolated as demo data and is not intended to represent real trading performance.

## Database migrations

This project now includes Alembic for PostgreSQL migrations.

1. Start PostgreSQL locally with Docker:
   `docker compose up -d db`
2. Apply the schema:
   `cd backend && python -m alembic upgrade head`
3. For a fresh local reset:
   `cd backend && python -m alembic downgrade base`

## Scripts

- Backend tests:
  `pytest -q`
- Frontend build:
  `cd frontend && npm run build`

## Architecture notes

The app is intentionally built around a universal trade model so a new broker or connector can be added without rewriting the analytics engine.

## Production notes

- Do not commit `.env` files or real credentials.
- Use managed PostgreSQL in production.
- Deploy frontend to Vercel and backend to Render, Railway, or Fly.io.
- Use environment variables for all secrets and broker config.

## Security

- no broker credentials are stored in plaintext
- API secrets stay on the backend
- auth is JWT-based with hashed passwords
- account/trade access is user-scoped
