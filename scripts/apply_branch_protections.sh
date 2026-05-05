#!/usr/bin/env bash
# Apply branch-protection rules for `main` and `dev` via the GitHub API.
#
# Idempotent — safe to re-run. Requires `gh` CLI authenticated as an admin
# of the repo. Run once after the branches exist on origin.
#
#   ./scripts/apply_branch_protections.sh

set -euo pipefail

REPO="${REPO:-lucasduport/uni-fly}"

# Names must exactly match the `name:` field on each CI job.
REQUIRED_CHECKS_MAIN='["Lint (ruff)","Type check (mypy)","Test (pytest)","pre-commit","Build site"]'
REQUIRED_CHECKS_DEV='["Lint (ruff)","Type check (mypy)","Test (pytest)","pre-commit","Build site"]'

protect() {
  local branch="$1" required_checks="$2" required_reviews="$3"

  echo "→ Protecting ${branch} on ${REPO}"

  # `gh api` accepts JSON via stdin to avoid shell-quoting nightmares.
  jq -n \
    --argjson contexts "${required_checks}" \
    --argjson reviews "${required_reviews}" \
    '{
      required_status_checks: {
        strict: true,
        contexts: $contexts
      },
      enforce_admins: false,
      required_pull_request_reviews: (
        if $reviews > 0 then {
          dismiss_stale_reviews: true,
          require_code_owner_reviews: true,
          required_approving_review_count: $reviews
        } else null end
      ),
      restrictions: null,
      allow_force_pushes: false,
      allow_deletions: false,
      required_conversation_resolution: true,
      required_linear_history: true,
      block_creations: false
    }' | gh api \
      --method PUT \
      --header "Accept: application/vnd.github+json" \
      "/repos/${REPO}/branches/${branch}/protection" \
      --input -

  echo "  ✓ ${branch} protected"
}

protect "main" "${REQUIRED_CHECKS_MAIN}" 1
protect "dev"  "${REQUIRED_CHECKS_DEV}"  0

echo
echo "Done. Set the default branch to 'dev' if not already:"
echo "  gh repo edit ${REPO} --default-branch dev"
