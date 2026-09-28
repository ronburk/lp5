# lp5 Agent Instructions

Before making changes, check for an existing lp5 checkout. If there is no usable checkout, clone the public repository:

```sh
git clone https://github.com/ronburk/lp5.git lp5
```

Preserve unrelated local changes. Verify the checkout's branch and commit against GitHub before editing. Use the GitHub connector for remote writes when available.

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

## Article terminology and format

An **article** is one `.lp5` file. Each file is an XML document with one `<template>` root. The root may contain at most one each of these direct children, in any order:

- `<children>` (optional): contains child-article links as `<li id="name.lp5">`.
- `<heading>` (optional): the article's display title.
- `<lp5-explanation>` (optional): the article's explanatory HTML/XML content. Inline HTML `<code>` elements here are ordinary inline code.
- `<lp5-code>` (optional): one code fragment, containing exactly one `<name>` and one `<code>` child.

When `<lp5-code>` is present, `<name>` is required but may be empty; an empty name denotes an unnamed/root fragment. `<code>` is required and may be empty. Its children must be CDATA sections containing literal code or XML elements whose names start with `lp5-` (for example, `<lp5- ref="name">`) representing code directives/references. Ordinary literal code belongs in CDATA; whitespace between child nodes is formatting whitespace.

The `<lp5-code>` wrapper distinguishes the code fragment from inline `<code>` markup in the explanation. If an article has no code fragment, omit `<lp5-code>` rather than writing an empty one.

A **bundle** is the ordered set of code sections that share the same `<name>` value.
