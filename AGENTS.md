# lp5 Agent Instructions

Each agent must use its own private clone of lp5. Never search for or reuse a
checkout, worktree, or branch created by another agent, even if it appears
clean. If you do not already have your own clone, create one:

```sh
git clone https://github.com/ronburk/lp5.git lp5
```

An extra Git worktree is unnecessary when your private clone is isolated.

Before editing, fetch from GitHub and verify the checkout's branch and base commit. Preserve unrelated local changes and use a task-specific branch. Before merging a PR, fetch again; if `main` has advanced, update the branch and rerun relevant checks. Merge only when the PR is conflict-free. Use the GitHub connector for remote writes when available.

## GitHub connector tool interface

For all GitHub remote writes, use the established
`mcp__codex_apps__github_*` tool family when available. This applies throughout
publication: `create_blob`, `create_tree`, `create_commit`, `create_branch`,
`update_ref`, `create_pull_request`, and `merge_pull_request`, as well as other
remote-write operations. Prefer the same family for reads when available.
Discover the exposed tools and inspect their schemas before choosing an
interface; do not invent a tool name or assume a tool is unavailable without
checking.

For example, `mcp__codex_apps__github_create_blob` takes:

```json
{
    "repository_full_name": "ronburk/lp5",
    "content": "<base64-file-contents>",
    "encoding": "base64"
}
```

Supply the actual encoded file contents. The tool also accepts `encoding`
`"utf-8"` for literal text. Check every result before passing its returned SHA
to the next operation; do not proceed after a failed write.

For remote branch creation, `mcp__codex_apps__github_create_branch` takes:

```json
{
    "repository_full_name": "ronburk/lp5",
    "branch_name": "<task-branch>",
    "sha": "<commit-sha>"
}
```

Supply the actual task branch and existing commit SHA; when publishing a
connector-created commit, use that commit's SHA. The tool also accepts
`base_ref` instead of `sha`; provide exactly one. Creating a local branch with
`git switch -c <task-branch>` is a separate operation.

A different exposed interface has been observed through generic `call_tool`
paths such as `/connector_.../link_.../create_branch` and
`/connector_.../link_.../create_blob`. Its branch arguments include `Repository`,
`Branch`, and `base_ref`; its blob arguments include `Repository`, `Content`,
and `encoding`. Both interfaces access GitHub, but do not assume they share
tool identity or remembered approvals. The interface preference applies to
every operation, not only branch creation: do not switch to generic
`call_tool` paths while the corresponding established tool is available. If
that tool is unavailable, report that and identify the alternative tool
before switching interfaces; do not silently substitute it. Inspect the
available tool's schema rather than reusing another interface's argument names.

Repeated "Always allow" prompts have been observed, but their cause and the
scope of saved approvals are not established. An interface change is a
possible explanation, not a confirmed diagnosis.

## OpenAI Work environment recovery

Before reporting that setup is blocked, inspect the exact error and the active
filesystem, network, and approval permissions. Try the recovery paths those
permissions allow, and continue any work that is still possible.

- `Failed to connect to browser-proxy port 8889` from Git or curl can result
  from the command sandbox denying the socket. A socket error such as
  `PermissionError: [Errno 1] Operation not permitted` confirms a permission
  failure. If escalation is allowed, retry a minimal read-only check through
  `exec_command` with `sandbox_permissions: "require_escalated"`:

  ```sh
  git ls-remote https://github.com/ronburk/lp5.git refs/heads/main
  ```

  If that succeeds, use the same permitted execution mode for clone, fetch,
  and network-dependent package installation. Do not repeatedly request
  escalation when the active policy disallows it or a request is rejected.
- Apt's `Read-only file system` error for `/var/lib/apt/lists` is a filesystem
  permission failure; running as root does not overcome it. Use a supported
  permission escalation if available, or recheck after the environment's
  filesystem permissions change. The temporary archive cache below addresses
  apt's cache and privilege-drop errors; it does not make a read-only lists
  directory or installation destination writable.
- Check the GitHub connector independently if shell networking fails. It can
  still verify the remote branch, commit, and file contents. A failed shell
  command does not establish that the connector or browser is unavailable.
- Do not infer an OpenAI outage from these errors. If checking for an outage,
  consult https://status.openai.com and verify the incident date and timezone.
  For a remaining blocker, report the exact failure and the permitted recovery
  attempts already made.

## Install build dependencies

Install `xsltproc` before building or testing XSLT work. On Ubuntu or Debian, use:

```sh
sudo apt-get update
sudo apt-get install -y xsltproc libxml2-dev libxslt1-dev
```

Omit `sudo` when already running as root. The development packages provide
the headers, libraries, and `xslt-config` needed to build the C launcher.

Confirm the installation with:

```sh
xsltproc --version
```

In the managed Ubuntu container used for this project, apt's default privilege drop may fail with `setgroups: Operation not permitted`, and its default archive cache may not be writable. If the normal install fails for those reasons, use a temporary archive cache and disable apt's sandbox user:

```sh
mkdir -p /tmp/apt-cache/archives/partial
chmod -R 700 /tmp/apt-cache
apt-get -o APT::Sandbox::User=root \
    -o Dir::Cache::archives=/tmp/apt-cache/archives update
apt-get -o APT::Sandbox::User=root \
    -o Dir::Cache::archives=/tmp/apt-cache/archives \
    install -y xsltproc libxml2-dev libxslt1-dev
```

## Build the C launcher

Build `./lp5` in the checkout root before running CLI commands or their tests:

```sh
gcc -std=c99 -Wall -Wextra -pedantic -o lp5 lp5.c $(xslt-config --cflags --libs) -lexslt
```

Keep the executable in the checkout directory; `lp5` is already in `.gitignore`.

## Build the HTML program

The main program is generated from the root article `lp5.lp5/lp5.lp5` by
`tangle.xsl`. Run this command from the repository root:

```sh
./lp5 -o lp5.html tangle lp5.lp5/lp5.lp5
```

The launcher registers the `my:ls` extension required by the current
stylesheets; running `tangle.xsl` or `weave.xsl` directly with ordinary
`xsltproc` fails with an unregistered-function error. For setup checks, use
`-w` and `-o` with temporary paths to avoid changing the tracked `lp5.html`
or creating `weave.xml` in the checkout.

The transform follows each `<children>` link and assembles the unnamed code
sections, recursively expanding named code references. It validates articles
as it reads them. `weave.xsl` generates the separate `weave.xml` source index;
it does not build the HTML program.

The generated `/lp5-weave/keyword-index` contains one `<keyword value="...">`
per nonempty canonical keyword, sorted by XSLT text order. Each entry contains
`<article file="..."/>` references, once per matching article in weave order,
including orphans. Canonicalization applies XPath `normalize-space()` followed
by ASCII A-Z to a-z folding; other characters are preserved exactly. Keyword
entries are whole terms, so commas and other punctuation are ordinary data.
The original `<keywords><li>` entries remain in the article records.

`./lp5 search-keywords [--all] -- KEYWORD [KEYWORD ...]` searches this snapshot
after the shared weave freshness check. See [SEARCH_KEYWORDS.md](SEARCH_KEYWORDS.md)
for the CLI grammar, normalization rules, and returned XML contract.

`./lp5 search [--all] -- TEXT [TEXT ...]` searches article text in this snapshot
after the same freshness check. See [SEARCH.md](SEARCH.md) for searchable fields,
literal matching, excerpts, and the returned XML contract.

`./lp5 list-keywords` lists the canonical vocabulary and distinct article counts
from the same snapshot. See [LIST_KEYWORDS.md](LIST_KEYWORDS.md) for its contract.

`./lp5 show-article [article-file.lp5]` returns the filename and complete source
template; omitting the filename selects `lp5.lp5` under `LP5Source`.
See [SHOW_ARTICLE.md](SHOW_ARTICLE.md) for its XML contract and navigation.

The weave index defaults to `weave.xml`. Use `-w <file>` to choose another index;
the freshness check reads and refreshes that selected file. `weave` writes there
by default. `add-article` uses it as input, and `show-bundle`, `search`,
`search-keywords`, and `list-keywords` read it. `show-bundle` lists bundle names,
or reads the named bundle; pass `""` for unnamed code. See
[SHOW_BUNDLE.md](SHOW_BUNDLE.md).

```sh
./lp5 [-w weave-file] weave [root-article]
./lp5 [-w weave-file] add-article <parent-id> <article-file> [before-child-id]
./lp5 remove-article <article-id.lp5>
./lp5 replace-article <article-id> <article-file>
```

`./lp5 replace-article <article-id> <article-file>` validates and replaces one
existing source article, including its desired child links. It skips the weave
freshness preflight and leaves the index untouched until a later command needs
it. See [REPLACE_ARTICLE.md](REPLACE_ARTICLE.md) for failure handling and tests.

`remove-article` removes a non-root leaf article and its unique parent link.
It stages and validates the updated parent before changing either source file;
the command leaves the selected weave file for the normal freshness check to
regenerate.
See [REMOVE_ARTICLE.md](REMOVE_ARTICLE.md) for refusal behavior.

## Check one article

Use the `check` command to validate one article without tangling the whole
article tree:

```sh
./lp5 check lp5.lp5/1.lp5
```

It applies the same article-format validation used by `tangle`. A valid file
prints its filename; invalid XML or an invalid article structure reports an
error and exits unsuccessfully.

For a bare filename that cannot be opened as given, `check` tries appending
`.lp5` when the name has no suffix, then looks for that resulting filename
under `LP5Source`. Arguments containing `/` or `\` are used as paths and do
not get these fallbacks. If no candidate exists, the error reports the
original argument.

## Article terminology and format

An **article** is one `.lp5` file. Each file is an XML document with one `<template>` root. The root may contain at most one each of these direct children, in any order:

- `<children>` (optional): contains child-article links as `<li id="name.lp5">`.
- `<heading>` (optional): the article's display title.
- `<keywords>` (optional): contains zero or more `<li>` elements, each with a text-only keyword. Whitespace between list items is allowed. The editor trims terms, ignores empty terms, and permits an empty element for legacy articles.
- `<section data-lp5-kind="explanation">` (optional): the article's explanatory HTML/XML content. Inline HTML `<code>` elements here are ordinary inline code.
- `<section data-lp5-kind="code">` (optional): one code section containing exactly one `<name>` and one `<code>` child.

Each permitted direct child may appear at most once in an article. Each kind of `<section>` may appear at most once, and no other `data-lp5-kind` values are allowed. In a code section, `<name>` is required but may be empty; an empty name denotes an unnamed/root fragment. `<code>` is required and may be empty. Its children must be CDATA sections containing literal code or XML elements whose names start with `lp5-` (for example, `<lp5- ref="name">`) representing code directives/references. Ordinary literal code belongs in CDATA; whitespace between child nodes is formatting whitespace.

The `data-lp5-kind` attribute distinguishes the explanation and code sections, and distinguishes both from inline HTML `<code>` markup in the explanation. If an article has no code fragment, omit the code section rather than writing an empty one.

A **bundle** is the ordered set of code sections that share the same `<name>` value.

### Cloud-browser testing in OpenAI Work

In OpenAI Work, cloud Chrome may reject `file://` URLs and may have
`showDirectoryPicker` undefined. This is an environment limitation, not
evidence that browser testing is unavailable.

Use the provided `sites-preview` runner and CUA browser:

1. Keep the checkout beneath `/workspace`.
2. Provide a `dev` script or `.openai/hosting.json`.
3. Run `sites-preview start "$PWD"` and open the returned
   `http://terminal.local:...` URL.
4. Exercise the visible UI through CUA.

For applications using native file I/O, add an explicit test adapter selected
before startup (for example, via a query parameter). The page evaluator is
read-only and cannot install a shim after the application starts.

If preview setup fails, first check `command -v sites-preview`, the checkout
location, the project startup configuration, and the exact runner error.
Native picker behavior, real disk permissions, and IndexedDB persistence
remain separate tests.
