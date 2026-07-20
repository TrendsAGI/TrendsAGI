# TrendsAGI repository instructions

## Long-lived branches

- `main` is production.
- `staging` is the release candidate branch.
- Do not make unrelated direct commits independently on both branches.
- Feature and fix work belongs on short-lived branches.
- `staging` must contain `main`; `main` must never be promoted from an independently recreated merge.

## Mandatory push launcher

When the user asks to push to staging, main, or both, or when an agent decides a completed change should be pushed, use the repository launcher and no alternative direct-push procedure:

```bash
./scripts/release-launcher.sh --staging
./scripts/release-launcher.sh --main
./scripts/release-launcher.sh --both
```

After the launcher prints a line beginning with `LAUNCHED`, report that launch and end the Codex chat. Do not wait for, poll, or watch GitHub Actions, Cloudflare builds, or deployment checks in that chat unless the user explicitly asks for follow-up verification in a later message.

The launcher only dispatches the controlled GitHub Actions release workflow. It does not wait for the workflow to finish.

## Safety rules

- Never bypass the launcher with a direct push to `main` or `staging`.
- Never force-push `main`.
- Never use an unguarded force push to `staging`.
- `--main` promotes the exact current remote `staging` SHA.
- `--both` updates `main` and `staging` to one exact candidate SHA through an atomic remote update.
- Do not print, commit, or copy secret values into logs or repository files.
- If the launcher is missing or fails before printing `LAUNCHED`, stop and report the exact failure instead of silently using another method.
