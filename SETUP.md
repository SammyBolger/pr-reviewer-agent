# Setup Guide

How to run your own instance of `pr-reviewer-agent` on your own GitHub repos, using your own hosting and your own Anthropic API key.

**Heads up.** My public deployment (`pr-reviewer-agent.fly.dev`) is locked to my own GitHub account. You cannot install my hosted App on your repos. You need to fork the code and stand up your own instance. This guide walks you through it, end to end.

---

## Prerequisites

- A GitHub account
- Python 3.11 or newer if you want to run locally first
- An Anthropic API key with a monthly budget cap (I set mine to $5)
- A place to host it. This guide uses [Fly.io](https://fly.io) because it's cheap (about $4 a month), always on, and easy. Render, Railway, a $5 VPS, or your own always-on machine with Cloudflare Tunnel all work too.

Rough monthly cost if you follow this guide exactly: **$4 to $9**, depending on how many PRs the bot reviews.

---

## 1. Fork the repo

Click **Fork** on https://github.com/SammyBolger/pr-reviewer-agent.

Then clone your fork:

```bash
git clone https://github.com/<your-username>/pr-reviewer-agent.git
cd pr-reviewer-agent
```

## 2. Create your own GitHub App

You need your own App because a GitHub App is tied to one account and one webhook URL. Mine points at my Fly server. Yours needs to point at yours.

**Register the App:**

1. Go to https://github.com/settings/apps → **New GitHub App**
2. Fill in:
   - **GitHub App name:** anything unique, like `<your-name>-pr-reviewer`
   - **Homepage URL:** your fork's URL
   - **Webhook URL:** leave blank for now, you'll fill it in after deploying
   - **Webhook secret:** generate one with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` and paste it. Save this string, you need it later.
3. **Repository permissions:**
   - Pull requests: **Read & write**
   - Issues: **Read & write**
   - Contents: **Read**
   - Metadata: **Read** (auto)
4. **Subscribe to events:**
   - Pull request
   - Issue comment
5. **Where can this GitHub App be installed?** → **Only on this account**. This is important. Do not leave it as "Any account" or strangers can install it on their repos and hit your API budget.
6. Click **Create GitHub App**

**Grab your credentials:**

- Copy the **App ID** (a number near the top)
- Scroll to **Private keys** → **Generate a private key**. A `.pem` file downloads.

**Install the App on your own repos:**

Left sidebar → **Install App** → your account → **Only select repositories** → pick the repos you want reviews on.

## 3. Get an Anthropic API key with a budget cap

1. Sign up at https://console.anthropic.com
2. Add a payment method
3. **Set a monthly usage limit** at https://console.anthropic.com/settings/billing. Recommend $5 or $10. If usage hits the cap, the API pauses and the bot goes quiet until next month. Prevents runaway bills.
4. Create an API key: **Settings → API Keys → Create Key**. Save it.

## 4. Deploy to Fly.io

**Sign up:**

- Go to https://fly.io/app/sign-up
- Requires a credit card. Fly does not bill on the free tier, but they check the card for fraud prevention.

**Install the CLI:**

```bash
brew install flyctl
fly auth login
```

**Launch the app:**

From your fork's root:

```bash
fly launch --no-deploy
```

Answer the prompts:
- Copy existing `fly.toml`? **Yes**
- App name? pick something unique (Fly names are global)
- Region? pick the closest to you (`ord` is Chicago)
- Postgres / Redis? **No** to both
- Deploy now? **No**

If you picked a different app name, edit `fly.toml` and update the `app = "..."` line to match.

**Create the storage volume:**

```bash
fly volumes create prreviewer_data --region <your-region> --size 1
```

**Set your secrets:**

```bash
fly secrets set \
  GITHUB_APP_ID="<your app id number>" \
  GITHUB_WEBHOOK_SECRET="<the webhook secret you generated in step 2>" \
  ANTHROPIC_API_KEY="<your anthropic key>" \
  DASHBOARD_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  GITHUB_APP_PRIVATE_KEY="$(cat ~/Downloads/<your-app>.<date>.private-key.pem)"
```

Change the path to wherever the `.pem` from step 2 downloaded. The `cat` preserves the real newlines. Do not paste the PEM into Fly's web UI, it can mangle newlines.

**Deploy:**

```bash
fly deploy
```

Takes about 3 minutes. Wait for `deployed successfully`.

Verify:

```bash
curl https://<your-app-name>.fly.dev/health
# should return {"ok":true}
```

## 5. Point your GitHub App at your Fly URL

Back at https://github.com/settings/apps → your App → **General**:

- **Webhook URL:** `https://<your-app-name>.fly.dev/webhook`
- Save

## 6. Test it

Open a small PR on one of the repos you installed the App on. Within about 20 seconds you should see a bot comment show up.

If nothing happens after a minute:

```bash
fly logs -a <your-app-name>
```

Watch for `ERROR` or `Traceback` lines. Most likely: a secret is wrong or the PEM got mangled somewhere.

## 7. Optional: auto-deploy on every push

The repo includes a GitHub Actions workflow at `.github/workflows/fly-deploy.yml`. To use it:

1. On Fly: dashboard → your name (top right) → **Access Tokens** → **Create Token**. Copy the token.
2. On GitHub: your fork → **Settings → Secrets → Actions → New repository secret**
3. Name: `FLY_API_TOKEN`. Value: paste the Fly token.

Now every push to `main` triggers a fresh deploy.

## 8. Customize per repo (optional)

Drop a `.reviewbot.yml` at the root of any repo the App is installed on:

```yaml
skip_paths:
  - "docs/**"
  - "*.md"
min_diff_lines: 10
extra_instructions: |
  Focus on security-sensitive changes. Ignore style comments.
```

The bot picks this up on the next review of that repo.

---

## Troubleshooting

**Bot doesn't respond to PRs.**
Check `fly logs` for errors. Usually a missing or mangled secret.

**`FileNotFoundError: secrets/github-app.pem`.**
`GITHUB_APP_PRIVATE_KEY` env var is empty. Re-run the `fly secrets set` command with the `$(cat ...)` pattern.

**OOM crashes.**
Bump `[[vm]] memory` in `fly.toml` to `"1gb"` and redeploy. Chroma's embedder needs the headroom.

**Webhook returns 401.**
Signature verification failing. The `GITHUB_WEBHOOK_SECRET` in Fly does not match the one on your GitHub App. Regenerate and set both to the same string.

**Deploy fails with `no access token available`.**
`FLY_API_TOKEN` secret in GitHub isn't set. See step 7.

---

## Cost summary

- Fly compute: ~$4 per month
- Anthropic API: ~$1 to $5 per month depending on PR volume, capped by your monthly usage limit
- Total: **$5 to $9 per month**
