# PageDoctor — Google Docs add-on

An internal Google Docs editor add-on for BookHub PMs. It opens a sidebar that lists Sophie's
findings for the current document and lets the PM jump to, and apply, each one. Source of truth
lives here and is pushed to the linked Apps Script project with `clasp`.

Findings come from the PageDoctor backend (`GET /docs/{docId}/findings`), which re-derives them
from the comments Sophie already posted — the add-on stores nothing.

## Files

- `Code.gs` — menu + sidebar; `getFindings` (calls the backend), `jumpToQuote`, `applyFix`.
- `Sidebar.html` — the sidebar UI.
- `appsscript.json` — manifest (OAuth scopes).
- `.clasp.json` — links to the Apps Script project (scriptId).

## Push

From this folder, with the Google account that has Editor access to the project:

```
cd addon
clasp login      # first time only
clasp push
```

## Configure

In the Apps Script project: **Project Settings → Script Properties**, add:

- `BACKEND_URL` — base URL of the PageDoctor backend, no trailing slash. In development this is the
  HTTPS tunnel to your local backend (e.g. `https://xxxx.trycloudflare.com`); the add-on runs on
  Google's servers and cannot reach `localhost`.
- `ADDON_TOKEN` — must equal the backend's `ADDON_TOKEN` (the bearer token the endpoint checks).

## Test

1. Run the backend reachable over HTTPS with `ADDON_TOKEN` set (a tunnel for dev).
2. In the Apps Script editor: **Deploy → Test deployments → Install**, choosing a document that is
   shared with the Sophie service account and already has her review comments.
3. Open that document → **Extensions → PageDoctor → PageDoctor öffnen**.
4. The sidebar lists the open findings. **Springen** scrolls to and highlights the quoted text;
   **Übernehmen** replaces it with Sophie's proposal.

> Quotes are re-located fresh in the live document on every action, so a finding whose text was
> edited reports "nicht gefunden" instead of changing the wrong place. Apply is a direct edit, made
> only when the PM clicks it.

## Notes

- Test-user authorization expires after ~7 days; re-run `clasp login` / re-authorize when prompted.
- The "unverified app" warning during authorization is expected for the internal testing phase.
- Do not switch the linked GCP project — it forces re-authorization for all users.
