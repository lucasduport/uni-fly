#!/usr/bin/env bash
# Apply branch-protection rules for `main` via the GitHub API.
#
# Idempotent — safe to re-run. Requires `gh` CLI authenticated as an admin
# of the repo. Run once after the branch exists on origin.
#
#   ./scripts/apply_branch_protections.sh

set -euo pipefail

REPO="${REPO:-lucasduport/uni-fly}"

# Names must exactly match the check names that GitHub actually reports.
# For matrix jobs, GitHub appends the matrix combination to the job name,
# so `Test (pytest)` with `python-version: ["3.12","3.13"]` reports as
# `Test (pytest) (3.12)` and `Test (pytest) (3.13)`. List both.
REQUIRED_CHECKS_MAIN='["Type check (mypy)","Test (pytest) (3.12)","Test (pytest) (3.13)","pre-commit","Build site"]'

protect() {
  local branch="$1" required_checks="$2" required_reviews="$3" code_owner="$4"

  echo "→ Protecting ${branch} on ${REPO}"

  # `gh api` accepts JSON via stdin to avoid shell-quoting nightmares.
  jq -n \
    --argjson contexts "${required_checks}" \
    --argjson reviews "${required_reviews}" \
    --argjson codeOwner "${code_owner}" \
    '{
      required_status_checks: {
        strict: true,
        contexts: $contexts
      },
      enforce_admins: false,
      required_pull_request_reviews: (
        if $reviews > 0 then {
          dismiss_stale_reviews: true,
          require_code_owner_reviews: $codeOwner,
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

# main: 1 code-owner review required (admin-merge for solo releases)
protect "main" "${REQUIRED_CHECKS_MAIN}" 1 true

echo
echo "Done."
