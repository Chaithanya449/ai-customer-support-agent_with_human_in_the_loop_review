# Customer Support Frontend

Next.js chat UI for the FastAPI and LangGraph customer support backend.

## Run locally

In one terminal, start the backend from the project root:

```powershell
uvicorn api:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The frontend sends chat requests to `http://127.0.0.1:8000` by default. To change it, create `.env.local` from `.env.local.example` and set `NEXT_PUBLIC_API_URL`.

The customer chat follows the provided mockup at `/`. The human review panel at `/review` reads pending requests from the backend and records reviewer decisions and notes. Approving a request can update payment and order status in the local SQLite database.
