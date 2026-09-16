# Namma Mitra — web

Frontend for the Karnataka government schemes analyzer.

Next.js (App Router) · TypeScript · Tailwind CSS v4 · next-intl (`/en`, `/kn`).

## Run

```bash
npm install
npm run dev        # http://localhost:3000 → redirects to /en
```

## Docker

From the repo root:

```bash
docker compose up --build   # serves on port 3000
```

## Notes

- Design tokens live in `src/app/globals.css` (`@theme` block) — the single
  source for colors, radii, and fonts. No raw hex outside that block.
- UI copy lives in `messages/en.json` and `messages/kn.json`.
- Scheme/question data is not bundled here — it comes from the FastAPI API
  (`/questions`, `/schemes`, `/match`, `/csc`). Point the app at it with
  `API_URL` (server-side) and `NEXT_PUBLIC_API_URL` (browser, inlined at
  build time); both default to `https://8000-kode-ws-169dee1f0.hebbale.academy`.