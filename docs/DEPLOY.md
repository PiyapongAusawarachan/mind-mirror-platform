# Deploy Mind Mirror Publicly

This project is ready to deploy as a public website on Render.

## Render Blueprint

1. Push this repository to GitHub.
2. Open Render and choose **New > Blueprint**.
3. Select the GitHub repository.
4. Render will read `render.yaml` and create:
   - `mind-mirror-platform` web service on the free plan
   - `mind-mirror-db` Postgres database for persistent accounts/lessons
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
REQUIRE_PERSISTENT_DB=true
DATABASE_URL=<set automatically from mind-mirror-db>
```

`DATABASE_URL` must point to managed Postgres in production. Without it, the app
will refuse to start because SQLite inside a free Render web container is
ephemeral: accounts, lessons, uploads metadata, and quiz history can disappear
after redeploys/restarts.

If you already deployed an older SQLite-based version, open the Render Blueprint
and click **Sync** (or recreate the Blueprint) so Render creates `mind-mirror-db`
and injects `DATABASE_URL` into the web service.

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
- Accounts and app records are durable through Render Postgres.
- Uploaded file binaries still live on the web service filesystem. On a free
  Render web container those files can be lost after redeploy/restart. The app
  stores extracted text in Postgres, so normal learning history remains usable.
  For full production file durability, add object storage later.
- Free Render Postgres can expire according to Render's free-plan limits. Upgrade
  the database before a real long-term launch.
