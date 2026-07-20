#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/release-launcher.sh --staging|--main|--both

--staging  Publish the current committed HEAD to staging through GitHub Actions.
--main     Promote the exact current remote staging SHA to main.
--both     Publish the current committed HEAD to staging and main atomically.
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ $# -eq 1 ]] || { usage >&2; exit 2; }
case "$1" in
  --staging) target="staging" ;;
  --main) target="main" ;;
  --both) target="both" ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

command -v git >/dev/null 2>&1 || fail "git is required"
command -v gh >/dev/null 2>&1 || fail "GitHub CLI (gh) is required"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || fail "not inside a Git repository"
cd "$repo_root"

[[ -z "$(git status --porcelain)" ]] || fail "working tree must be clean; commit or stash changes first"
gh auth status >/dev/null 2>&1 || fail "GitHub CLI is not authenticated"

remote="${TRENDSAGI_RELEASE_REMOTE:-origin}"
git remote get-url "$remote" >/dev/null 2>&1 || fail "remote '$remote' does not exist"
git fetch --prune "$remote" main staging

main_sha="$(git rev-parse "refs/remotes/${remote}/main")"
staging_sha="$(git rev-parse "refs/remotes/${remote}/staging")"
repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"

case "$target" in
  main)
    candidate_sha="$staging_sha"
    candidate_ref="staging"
    git merge-base --is-ancestor "$main_sha" "$candidate_sha" \
      || fail "remote staging does not contain remote main"
    ;;
  staging|both)
    candidate_sha="$(git rev-parse HEAD)"
    git merge-base --is-ancestor "$main_sha" "$candidate_sha" \
      || fail "current HEAD does not contain remote main"
    if [[ "$target" == "both" ]]; then
      git merge-base --is-ancestor "$staging_sha" "$candidate_sha" \
        || fail "current HEAD does not contain remote staging; refusing to discard staged work"
    fi

    short_sha="$(git rev-parse --short=12 "$candidate_sha")"
    candidate_ref="codex/candidate-${short_sha}"
    existing_sha="$(git ls-remote "$remote" "refs/heads/${candidate_ref}" | awk '{print $1}')"
    if [[ -n "$existing_sha" && "$existing_sha" != "$candidate_sha" ]]; then
      fail "remote candidate ref ${candidate_ref} exists at an unexpected SHA"
    fi
    if [[ "$existing_sha" != "$candidate_sha" ]]; then
      git push "$remote" "${candidate_sha}:refs/heads/${candidate_ref}"
    fi
    ;;
esac

gh workflow run release-promotion.yml \
  --repo "$repo" \
  --ref main \
  -f "target=${target}" \
  -f "candidate_sha=${candidate_sha}" \
  -f "candidate_ref=${candidate_ref}"

printf 'LAUNCHED target=%s sha=%s candidate_ref=%s\n' "$target" "$candidate_sha" "$candidate_ref"
