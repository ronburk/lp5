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

An **article** is one `.lp5` file. Its XML document has a `<template>` root. An article contains sections such as `<explanation>` and `<code>`; `<heading>` (article title), `<name>` (code-section name), and `<children>` (links to child articles using `<li id="…lp5">`) are metadata or structure, not sections.

In `<code>`, CDATA holds literal code and `<lp5- ref="…"/>` marks a code reference. The older `<script>` code-section format still appears in some articles. No separate convention for HTML formatting inside code has been established.
