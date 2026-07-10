# PageDoctor — Internal Rollout Checklist

How to take the add-on from "works on a test doc" to "every BookHub PM has it under
Extensions, in every doc." Two tracks run in parallel: the **backend** (a reachable HTTPS API)
and the **add-on publish** (a private Google Workspace Marketplace app installed domain-wide).

This is an ops/handoff note. It records the exact console paths and the load-bearing choices.

---

## 0. Current state

- **Backend deployed** on the netcup VPS `152.53.206.224` (Debian 12): the FastAPI app under
  systemd (`pagedoctor.service`), native Postgres 15 (migrated), 4 GB swap, ufw (22/80/443).
  `pagedoctor`, `caddy`, and `postgresql` are all **enabled on boot** — the stack comes back after
  a reboot.
- **Public HTTPS is live and stable** at **`https://lektorat.mybookhub.de`** — Caddy terminates TLS
  on our own box with an auto-renewing **Let's Encrypt** cert (no third party sees plaintext). The
  earlier Cloudflare quick tunnel was **retired** (it was ephemeral and terminated TLS at
  Cloudflare's edge).
- **Add-on code** (`Code.gs`, `Sidebar.html`, `appsscript.json`) is pushed via `clasp` to the
  Apps Script project linked to GCP project `internal-proofreading-bookhub` (415778707338).

The add-on's `BACKEND_URL` is a **Script Property**, so the URL can be swapped later with **zero
PM action** — only this one value changes.

---

## 1. Prerequisite — access to the company GCP project

The add-on lives in the company project **`internal-proofreading-bookhub` (415778707338)**. To
configure the consent screen + Marketplace SDK you need **Owner** on it.

- Ask the project owner (Tech Lead) to grant your BookHub account **`roles/owner`** on
  `415778707338`. (Do **not** use the console's "Request access" screen — its suggested roles,
  e.g. Project Mover, only grant a view sliver.)
- Confirm the project sits under the **mybookhub.de** organization, so an "Internal" publish
  targets our domain.

The final domain-wide install (step 6) always needs a **Workspace super-admin** (Admin console),
regardless of your project role.

---

## 2. Backend — stable HTTPS (DONE)

Owner: ops (handled by the developer/agent on the server).

1. **DNS A/AAAA records** for `lektorat.mybookhub.de` -> `152.53.206.224` (+ IPv6) are live on the
   mybookhub.de authoritative nameservers. Done.
2. `/etc/caddy/Caddyfile` points at `lektorat.mybookhub.de` -> `reverse_proxy 127.0.0.1:8000`;
   Caddy is `enable --now` and obtained a **Let's Encrypt** cert (auto-renews). The Cloudflare
   tunnel is retired. TLS terminates on our own server (no third party sees plaintext — required
   for confidential manuscripts). Done.
3. **Remaining:** set the add-on's `BACKEND_URL` Script Property to `https://lektorat.mybookhub.de`
   (step 3 below). This is the only switch left for go-live.
4. **Harden the box** (recommended, not yet done): rotate the root password, add SSH keys + disable
   password auth, keep ufw.

---

## 3. Apps Script project + Script Properties

In the Apps Script project (linked to `internal-proofreading-bookhub`):

1. Confirm the latest code is present (`clasp push` from `addon/` already did this).
2. **Project Settings -> Script Properties** -> add:
   - `BACKEND_URL` = `https://lektorat.mybookhub.de` (the live, stable HTTPS URL).
   - `ADDON_TOKEN` = the exact value from the backend `.env` (the endpoint's bearer token).

---

## 4. OAuth consent screen (Google Auth Platform)

In `internal-proofreading-bookhub`, under **Google Auth Platform**:

- **Audience** -> **User type = Internal** (restricts to mybookhub.de; no Google verification review
  needed for internal apps).
- **Branding** -> app name ("PageDoctor"), support email, app logo.
- **Data Access** -> add exactly these scopes:
  - `https://www.googleapis.com/auth/documents.currentonly`
  - `https://www.googleapis.com/auth/script.container.ui`
  - `https://www.googleapis.com/auth/script.external_request`
- **Clients** -> leave empty. A Workspace add-on does **not** use a manually-created OAuth client;
  it authorizes through its Apps Script deployment.

---

## 5. Create the add-on deployment + Marketplace SDK

1. **Apps Script editor -> Deploy -> New deployment -> type: Add-on** -> create. Note the
   deployment (and the script ID).
2. In the GCP project: **APIs & Services -> Library -> "Google Workspace Marketplace SDK" -> Enable.**
3. Open the SDK -> **App Configuration**:
   - **Visibility: Private** (mybookhub.de only).
   - **Integration: Editor Add-on** -> reference the Apps Script deployment (script ID + deployment).
   - List the same three OAuth scopes as in step 4.
   - Fill developer name / links as required.
4. **Store Listing**: app name, icon(s), short + long description, at least one screenshot,
   category, and the terms/privacy/support URLs. Then **Publish** (internal apps publish
   immediately — no review).

---

## 6. Domain-wide install (Workspace admin)

In the **Admin console** (admin.google.com), a super-admin:

- **Apps -> Google Workspace Marketplace apps** -> find the private PageDoctor app.
- **Install** -> grant to **everyone** or the PMs' **organizational unit** -> accept the scopes.

After this, every PM opens any Google Doc -> **Extensions -> PageDoctor -> "PageDoctor öffnen"** —
nothing to paste, in any doc.

---

## 7. Verify end-to-end

- A PM (not the developer) opens a reviewed doc -> the sidebar lists Sophie's findings.
- **Review starten** runs; **Übernehmen/Verwerfen** resolve the comment (no reappearance on reload).
- Editing a paragraph then re-checking only re-reviews the changed section (the "Dokument geändert"
  banner appears).
- Backend logs show requests arriving over `https://lektorat.mybookhub.de`; no manuscript text is
  logged (counts/ids only).

---

## Notes

- **Swapping the backend URL** post-launch is one Script Property change (step 3) — no PM action.
- The add-on stores nothing; it re-derives findings from the comments Sophie posts. The backend
  DB holds metadata only.
- Keep the netcup box off Docker (2 vCPU / ~2 GB RAM); native Postgres + systemd + Caddy is the
  intended footprint.
