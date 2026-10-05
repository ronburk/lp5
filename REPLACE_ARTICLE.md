# Replace one complete source article

```sh
./lp5 [-s source-dir] replace-article <article-id> <article-file>
```

`article-id` is an existing filename ending in `.lp5`, such as `12.lp5` or
`lp5.lp5`. It is resolved only under the selected source directory, which
defaults to `lp5.lp5` and can be set through `LP5Source` or overridden with `-s`.
Paths and suffix-free IDs are not accepted. The target must be a regular file.

`article-file` is a path to one complete article in the normal LP5 XML format.
The command validates it with the same article validator as `check`, then
replaces the target with exactly the validated input bytes. It preserves XML
declarations, whitespace, CDATA, comments, and encoding without reserialization.
The target keeps its existing filename. The input may be the target itself.

The complete replacement includes its desired `<children>` links. Content and
hierarchy may therefore change together; omitted fields are removed rather
than retained from the old article. Only this article file is replaced. The
old target need not be valid XML, so the command can repair a broken article.
Validation does not follow child links or code references.

The command skips the weave freshness preflight and does not create, refresh,
or rewrite `weave.xml`. An explicit `-w` index is also left untouched. A later
command that normally checks freshness regenerates the selected index when
needed. After changing hierarchy, validate the project with the normal project
checks, for example `./lp5 -o output.html tangle`.

The replacement is fully written and closed in a temporary file in the source
directory before it is installed with `rename` on POSIX or `MoveFileEx` on
Windows. The old target is never truncated or removed first. Basic POSIX file
permissions are retained. Temporary-file, write, close, or replacement failures
leave the old target unchanged and report an error.

Success returns status 0 with no stdout output. Errors return status 1 and
diagnostics on stderr. `-o` is rejected because the destination is always the
existing article filename; `-m` is also invalid. Use `--` after the command
when an operand is spelled like a global option.

Build `./lp5` in the checkout root as described in `AGENTS.md`, then test:

```sh
python3 test/replace_article.py ./lp5
```
