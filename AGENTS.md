# lp5 Agent Instructions

Each agent must use its own private clone of lp5. Never search for or reuse a
checkout, worktree, or branch created by another agent, even if it appears
clean. If you do not already have your own clone, create one:

```sh
git clone https://github.com/ronburk/lp5.git lp5
```

An extra Git worktree is unnecessary when your private clone is isolated.

Before editing, fetch from GitHub and verify the checkout's branch and base commit. Preserve unrelated local changes and use a task-specific branch. Before merging a PR, fetch again; if `main` has advanced, update the branch and rerun relevant checks. Merge only when the PR is conflict-free. Use the GitHub connector for remote writes when available.

## Install xsltproc

Install `xsltproc` before building or testing XSLT work. On Ubuntu or Debian, use:

```sh
sudo apt-get update
sudo apt-get install -y xsltproc
```

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
    install -y xsltproc
```

## Build the HTML program

The main program is generated from the root article `lp5.lp5/lp5.lp5` by
`tangle.xsl`. Run this command from the repository root:

```sh
xsltproc -o lp5.html tangle.xsl lp5.lp5/lp5.lp5
```

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

`./lp5 list-keywords` lists the canonical vocabulary and distinct article counts
from the same snapshot. See [LIST_KEYWORDS.md](LIST_KEYWORDS.md) for its contract.

`./lp5 show-article [article-file.lp5]` returns the filename and complete source
template; omitting the filename selects `lp5.lp5` under `LP5Source`.
See [SHOW_ARTICLE.md](SHOW_ARTICLE.md) for its XML contract and navigation.

`./lp5 show-bundle` lists all bundle names. Supply a name to read its code sections
from `weave.xml`, or `""` for unnamed code. See [SHOW_BUNDLE.md](SHOW_BUNDLE.md).

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
