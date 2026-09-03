# Aarogya — Next.js frontend

Family health SaaS UI for [Aarogya](../Ai-health-App). **This repo is the only product frontend.** The FastAPI backend lives in `../Ai-health-App` (backend-only).

## Stack

- Next.js 15 (App Router) + React 18
- Tailwind CSS (Soft Structuralism marketing tokens)
- React Hook Form + Zod
- BFF routes under `/api/auth/*` → FastAPI `/api/v1/*` (httpOnly refresh cookie; access also mirrored as `aarogya_access`)

## Setup

```bash
cp .env.example .env.local
npm install
npm run dev
```

Requires the API at `API_INTERNAL_URL` (default `http://localhost:8000`).

## Routes

| Area | Paths |
|------|--------|
| Marketing | `/`, `/features`, `/pricing`, `/for-doctors`, `/for-labs` |
| Legal | `/legal/*` |
| Auth | `/login`, `/register`, `/verify`, `/forgot-password`, `/reset-password` |
| App (gated) | `/app`, `/app/reports`, `/app/members`, `/app/settings` |
| SEO | `/sitemap.xml`, `/robots.txt`, JSON-LD on home |

## Auth model

1. Register → OTP verify → login
2. Refresh token stays in httpOnly cookie (`aarogya_refresh`, path `/` after BFF rewrite from `/api/v1/auth`)
3. Access token returned in JSON and set as httpOnly `aarogya_access` for middleware; also mirrored in `sessionStorage` for client `Authorization` headers

## Scripts

- `npm run dev` — port 3000
- `npm run build` / `npm start`
- `npm run lint`
