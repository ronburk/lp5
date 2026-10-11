# Repository workflow

These rules apply to every LP5 task. `AGENTS.md` routes agents here before work
begins.

## Start and continue work

- Before a new change, fetch from GitHub, establish the checkout's branch and
  base commit, and use a task-specific branch.
- Preserve completed edits, builds, test results, commits, branches, and PRs
  across turns. Reuse them when still applicable.
- A follow-up on the same change does not require repeating setup.
- Preserve unrelated local changes. Do not reset, overwrite, or clean files
  unless they are part of the requested change.
- Run checks relevant to the change. Stop a test sequence at the first failure;
  diagnose it before attempting additional checks. Repeat successful checks only
  when code, dependencies, or the relevant base changed, or a required gate
  demands it. Documentation changes normally need review and
  `git diff --check`, not an application build.

## Publish and merge

- For GitHub remote writes, use the established
  `mcp__codex_apps__github_*` tools when available. Inspect their definitions
  before first use; follow their actual schemas and inspect each result before
  dependent operations. Prefer the same connector for GitHub reads when
  available. Reuse verified repository details and existing task branches or
  PRs; do not create duplicates.
- Prefer publishing related file changes in one commit when supported. Avoid
  redundant API calls and tight polling while GitHub calculates mergeability or
  runs checks.
- Before merging, check current mergeability and required checks. Merge when
  conflict-free and checks pass. When supported, provide the expected PR head
  commit so an unexpected update cannot be merged unreviewed.
- Do not routinely fetch, rebase, or rerun tests only because publication is
  next. If the base changed or merge fails, inspect the cause and update the
  branch or rerun affected checks as needed.
- Confirm a successful merge. Then fast-forward the local checkout when
  appropriate, preserving unrelated work.
- PR descriptions explain the problem, changes, resulting behavior,
  validation, and material limitations. Include useful harness observations,
  not routine logs.

### Shortcuts

In LP5 project chats, `smpr` means finish implementation and relevant checks,
publish, submit a detailed PR, and merge it when conflict-free and checks pass.
`pr` means the same through PR submission, leaving it open. `test` means run
relevant tests and report results. Reuse work already completed for the change.

## GitHub and environment recovery

- A `user rejected MCP tool call` result is an approval rejection, not a GitHub
  API failure. Report the exact result and stop dependent writes. Do not retry
  through another interface to bypass the rejection. A user-authorized retry
  should be limited to the requested operation.
- For repeated “Always allow” prompts, record the exposed tool definition, the
  literal invocation (excluding large payloads and secrets), exact result, and
  whether the prompt repeated for the same operation. A success in another chat
  does not establish this chat's permissions. When investigating approval
  behavior, consult the current official guidance:
  [OpenAI Work cloud security](https://learn.chatgpt.com/docs/enterprise/chatgpt-work-cloud-security)
  and [agent approvals](https://learn.chatgpt.com/docs/agent-approvals-security).
- A Git/curl failure mentioning browser-proxy port 8889 can mean the shell
  sandbox denied its socket. Inspect the exact error and permissions. If
  escalation is allowed, use the documented read-only connectivity check:

  ```sh
  git ls-remote https://github.com/ronburk/lp5.git refs/heads/main
  ```

  If it succeeds, use the same permitted execution mode for clone, fetch, and
  network-dependent installs. Check the GitHub connector independently when
  shell networking fails. Do not infer a service outage from a socket error.
- If checking for an OpenAI outage, consult
  [status.openai.com](https://status.openai.com) and verify incident date and
  timezone.
- Apt's `/var/lib/apt/lists` read-only error is a filesystem permission issue;
  being root does not fix it. If escalation is allowed, use the temporary-cache
  apt recovery documented in [HARNESS.md](HARNESS.md). If escalation is
  unavailable or rejected, report the exact result. Do not stop after a default
  sandbox failure when documented recovery is permitted.
