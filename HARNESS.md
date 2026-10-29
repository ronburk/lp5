# LP5 harness and build

Read this when using or changing `./lp5`, building its outputs, or inspecting
and editing articles. For the XML schema and bundle naming rules, also read
[ARTICLE_FORMAT.md](ARTICLE_FORMAT.md).

## Build dependencies

Check dependencies when a task needs them or after an environment reset. On
Ubuntu or Debian, install them as root (or prepend `sudo` when needed):

```sh
apt-get update
apt-get install -y xsltproc libxml2-dev libxslt1-dev
```

These development packages provide the headers, libraries, and `xslt-config`
needed to build the C launcher. Confirm the installation with:

```sh
xsltproc --version
```

In the managed Ubuntu container, apt's default privilege drop may fail with
`setgroups: Operation not permitted`, its default archive cache may not be
writable, and the default sandbox may deny writes to system apt directories. If
the normal install fails for these reasons and escalation is allowed, run:

```sh
mkdir -p /tmp/apt-cache/archives/partial
chmod -R 700 /tmp/apt-cache
apt-get -o APT::Sandbox::User=root \
    -o Dir::Cache::archives=/tmp/apt-cache/archives update
apt-get -o APT::Sandbox::User=root \
    -o Dir::Cache::archives=/tmp/apt-cache/archives \
    install -y xsltproc libxml2-dev libxslt1-dev
```

## Build the launcher and project output

With [Blud](https://github.com/ronburk/blud) installed, run `blud` in the
repository root to build both `lp5` and `lp5mcp`. The bludfile uses GCC,
`xslt-config`, and `curl-config`; install the dependencies above plus
`libcurl4-openssl-dev` on Debian/Ubuntu. It targets a POSIX shell environment.

Use `blud lp5` or `blud lp5mcp` to build just one program, or `blud -B` to
force a rebuild after changing compiler flags or installed libraries. Both
executables stay in the repository root so the MCP server can find `lp5`
beside itself. Source changes rebuild the affected program; changing the
bludfile rebuilds both. The direct compiler commands below remain usable
without Blud.

Reuse `./lp5` if it was built from the current `lp5.c` and still runs. Build it
in the repository root if missing, if `lp5.c` changed, or if an environment
change made it unusable:

```sh
gcc -std=c99 -Wall -Wextra -pedantic -o lp5 lp5.c $(xslt-config --cflags --libs) -lexslt
```

The executable is ignored by Git. Build the project output when requested or
needed to validate source changes; reuse an applicable output for follow-up
publication. For project `lp5`:

```sh
./lp5 lp5 tangle
```

This writes the unnamed bundle to `lp5.lp5/lp5.out` and its source map to
`lp5.lp5/lp5.map`. See [ARTICLE_FORMAT.md](ARTICLE_FORMAT.md) for named output
bundles.

The launcher registers the `my:ls` extension required by current stylesheets;
running `tangle.xsl` or `weave.xsl` directly with ordinary `xsltproc` fails with
an unregistered-function error. `tangle` builds program output. `weave` creates
the source index; it does not build the program.

## MCP stdio server

`lp5mcp.c` builds a separate `lp5mcp` executable. It requires a local project
or future checkout directory and serves newline-delimited MCP JSON-RPC on stdio:

```sh
blud lp5mcp
./lp5mcp ./lp5.lp5
./lp5mcp --help
```

The positional argument is the actual local directory, including `.lp5` when
applicable. Relative paths are resolved from the caller's working directory.
Missing directories (including missing parents) are accepted without creating
them. Existing non-directories, empty paths, and URLs are rejected. Use `--`
before a path beginning with `-`. Help is available via `--help`, `-h`, or `-?`.

In local mode, a `NAME.lp5` directory selects project `NAME` immediately. If
another directory is supplied, use `select_project` before project operations.
That tool still takes a project stem: `demo` selects `demo.lp5` beneath the
startup directory; absolute stems are also accepted. It can switch projects.
The available operations are `check`, `show_article`, `show_bundle`, `weave`,
and `tangle`. They invoke the ordinary `lp5` executable beside `lp5mcp`; set
`LP5_EXECUTABLE` when it is elsewhere. A missing checkout can start the server,
but local operations need the actual project files before they can succeed.
Run `python3 test/lp5mcp.py ./lp5mcp` for startup and protocol checks.

### Optional HTTPS backend

Building lp5mcp now requires libcurl development files (on Debian/Ubuntu,
`libcurl4-openssl-dev`). Local mode remains the default; no HTTP request is
made unless `LP5_SERVER_URL` is set to a nonempty HTTPS endpoint URL.

```
LP5_SERVER_URL=https://your-server.example/lp5 ./lp5mcp ./checkout
```

In this first increment remote mode advertises only `select_project` and
`check`. The existing `path` argument to `select_project` is an opaque
server-side project identifier in this mode, not a local filesystem path.
The required startup directory remains local and is never used as the remote
project identifier. Remote mode starts without a server-side project selected.
Selection stores the identifier; the server validates it on the first check.
There is no silent fallback to local operations on network failure.

`check` POSTs JSON to the exact configured endpoint:

```json
{"op":"check","project":"demo","article":"12"}
```

The application endpoint need not speak MCP. It returns UTF-8 plain text
with a 2xx status on success; non-2xx statuses and transport failures become
MCP errors, with diagnostics on stderr. Responses are limited to 1 MiB and
must not contain NUL bytes. This small first version does not parse JSON
responses or configure authentication; a corresponding server is not included.

libcurl verifies the TLS certificate and hostname using its configured trust
store. Connection timeout is 10 seconds and total timeout is 30 seconds.
Redirects are not followed, and there is no insecure TLS switch or automatic
retry. Unset `LP5_SERVER_URL` to restore the original local harness behavior.

## Project naming and generated index

Every command takes the project name first: `./lp5 <project-name> <command>
[arguments...]`. Project `X` uses source directory `X.lp5/`, root article
`X.lp5/X.lp5`, and generated index `X.lp5/weave.xml`. `weave.xml` is a
regenerable index, refreshed automatically when a command that needs it detects
stale source. Let those commands perform the freshness check; do not manually
run `weave` before every read or operation. Commands that change source may
leave the index stale for the next command to refresh.

The index's `/lp5-weave/keyword-index` contains one `<keyword value="...">`
per nonempty canonical keyword, sorted in XSLT text order. Each entry contains
one `<article file="..."/>` per matching article in weave order, including
orphans. Canonicalization applies XPath `normalize-space()` followed by ASCII
A-Z to a-z folding; other characters are preserved. Keywords are whole terms;
commas and punctuation are ordinary data. Original `<keywords><li>` entries
remain in article records.

## Inspect and edit articles

Use the harness's supported commands rather than opening source articles
directly. Reuse article reads while their source is unchanged. Record harness
failures and concrete improvements that would make the work easier.
`show-article` is for inspecting a source article; its `<lp5-article>` output
wrapper is not an article file that can be passed to `add-article`.

```sh
./lp5 X show-article [article-file.lp5]
./lp5 X show-bundle                  # list bundle names
./lp5 X show-bundle "Bundle name"    # read one bundle
./lp5 X show-bundle ""               # read unnamed bundle
./lp5 X search [--all] [--] TEXT [TEXT ...]
./lp5 X search-keywords [--all] -- KEYWORD [KEYWORD ...]
./lp5 X list-keywords
./lp5 X check 1.lp5
./lp5 X weave
./lp5 X tangle
```

The project directory and weave index are derived from `X`; there are no
per-command path overrides. See the command contracts for exact CLI and output
behavior:

- [SHOW_ARTICLE.md](SHOW_ARTICLE.md)
- [SHOW_BUNDLE.md](SHOW_BUNDLE.md)
- [SEARCH.md](SEARCH.md)
- [SEARCH_KEYWORDS.md](SEARCH_KEYWORDS.md)
- [LIST_KEYWORDS.md](LIST_KEYWORDS.md)
- [ADD_ARTICLE.md](ADD_ARTICLE.md)
- [REMOVE_ARTICLE.md](REMOVE_ARTICLE.md)
- [REPLACE_ARTICLE.md](REPLACE_ARTICLE.md)

`check` validates a single article with the same format validator used by
`tangle`. A valid file prints its filename; malformed XML or invalid article
structure fails. For a bare filename that cannot be opened as given, `check`
tries appending `.lp5` if it has no suffix, then looks under the project
directory. Arguments containing `/` or `\\` are used as paths without these
fallbacks.

### Article mutation commands

```sh
./lp5 X add-article <parent-id> <article-file> [before-child-id]
./lp5 X remove-article <article-id.lp5>
./lp5 X replace-article <article-id> <article-file>
```

`add-article` validates the input, chooses an unused numeric `.lp5` filename,
installs the article, and adds its parent link atomically. It leaves the input
untouched and the weave index stale for normal refresh. The default insertion
point is the beginning of the parent's child list. `before-child-id`, when
provided, must be an existing direct child. It reports the generated filename
on stderr. The input must be a complete LP5 XML source document whose root is
`<template>`; do not pass the `<lp5-article>` wrapper returned by
`show-article`. Use `--` when an operand looks like an option. See
[ADD_ARTICLE.md](ADD_ARTICLE.md) for rollback behavior and its test.

`remove-article` removes a non-root leaf and its unique parent link; it refuses
roots, missing articles, child-bearing articles, and ambiguous parent links. It
stages and validates the revised parent before changing the source files. See
[REMOVE_ARTICLE.md](REMOVE_ARTICLE.md).

`replace-article` validates and replaces one existing article with the exact
input bytes, including its desired child links. It skips weave freshness and
leaves the index untouched until a later command needs it. After hierarchy
changes, validate the project with `./lp5 X tangle`. See
[REPLACE_ARTICLE.md](REPLACE_ARTICLE.md).

Focused acceptance tests are documented by the command contracts; run the
relevant one after changing that command.
