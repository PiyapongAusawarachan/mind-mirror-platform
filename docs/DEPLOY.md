# Deploy Mind Mirror Publicly

This project is ready to deploy as a public website on Render.

## Render Blueprint

1. Push this repository to GitHub.
2. Open Render and choose **New > Blueprint**.
3. Select the GitHub repository.
4. Render will read `render.yaml` and create:
   - `mind-mirror-platform` web service on the free plan
5. Add the required secret environment variable:
   - `GEMINI_API_KEY`
6. Deploy.

## Required Environment Variables

Render sets most values from `render.yaml`. Add this manually in the Render dashboard:

```text
GEMINI_API_KEY=<your Google AI Studio API key>
```

Recommended values already configured:

```text
ENV=production
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
DEFAULT_LANG=th
SECURE_COOKIES=true
```

The free Render blueprint uses local SQLite. This is enough for demo/presentation
and avoids requiring a payment card. For durable production data, add a managed
Postgres database later and set `DATABASE_URL`.

## Verify

After deploy, open:

```text
https://<your-render-service>.onrender.com/healthz
```

It should return:

```json
{"status":"ok"}
```

Then test:

- Register a student and teacher
- Create a lesson
- Add explanation
- Run analysis
- Generate quiz
- Open teacher dashboard

## Notes

- Do not commit `.env`.
- Free hosting may cold-start, so the first request can be slow.
- Uploaded files and SQLite data on a free web container may not be durable long-term.
  This is enough for MVP/demo. For production, use managed Postgres plus object
  storage for uploads.
