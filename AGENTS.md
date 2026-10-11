# LP5 agent instructions

Read this file first. Follow [WORKFLOW.md](WORKFLOW.md) for checkout, change,
validation, and publication rules on every task. Then read only the task-specific
instructions below:

Explicit user and project instructions take precedence over repository
instructions. Reuse instructions already read unless the file changed.

- **Using or changing the harness, tangling, or editing articles:** read
  [HARNESS.md](HARNESS.md). For article XML structure or bundle naming, also
  read [ARTICLE_FORMAT.md](ARTICLE_FORMAT.md).
- **Changing browser behavior or verifying the UI:** read
  [BROWSER_TESTING.md](BROWSER_TESTING.md) and the relevant manual test notes in
  `test/*.md`.
- **Changing a documented harness command:** read its command contract, linked
  from [HARNESS.md](HARNESS.md), and run its focused test.

Do not read every task-specific document by default. Existing instructions read
for the same task remain applicable unless the file changed.

## Checkout setup

Reuse a usable checkout owned by this agent and preserve unrelated local work.
Never reuse another agent's checkout, worktree, or branch, even if it appears
clean. If there is no usable agent-owned checkout, create a private clone:

```sh
git clone https://github.com/ronburk/lp5.git lp5
```

An extra worktree is unnecessary when the private clone is isolated.
