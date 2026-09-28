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
