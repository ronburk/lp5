# lp5 Agent Instructions

Use the existing agent-specific lp5 checkout; an extra Git worktree is unnecessary when that checkout is isolated. If there is no usable checkout, clone the public repository:

```sh
git clone https://github.com/ronburk/lp5.git lp5
```

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
