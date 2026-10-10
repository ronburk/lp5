# Add a source article

```sh
./lp5 [-s source-dir] [-w weave-file] add-article <parent-id> <article-file> [before-child-id]
```

`parent-id` is the filename of an existing article under the selected source
directory. The source directory defaults to `lp5.lp5` and can be set through
`LP5Source` or overridden with `-s`. `article-file` is a path to a complete new
article template in normal LP5 XML format. The input file is left untouched.

The command validates the template, chooses an unused numeric `.lp5` filename,
installs the article in the selected source directory, and adds a link to it in
the parent article. These changes happen in one command. For example:

```sh
./lp5 -s articles add-article lp5.lp5 /tmp/draft.lp5
```

On success, the command reports the generated filename, such as
`added article: 3.lp5`, on stderr. If `before-child-id` is supplied, it must be
an existing direct child of the parent, and the new link is inserted before
that child. Otherwise, the new link is inserted at the beginning of the child
list. Other parent content and existing child order are preserved.

The command does not rewrite the selected weave index. If `-w` is supplied, it
selects the index that will be considered stale; the next command that needs
the index refreshes it through the normal freshness check. Without `-w`, the
default `<source-dir>/weave.xml` index is used. The legacy index-first form remains accepted when
`-w` is omitted:

```sh
./lp5 add-article <weave-file> <parent-id> <article-file> [before-child-id]
```

The article and updated parent are staged before installation. If installing
the updated parent fails, the newly installed article is removed. Validation,
input, or transformation failures leave the source articles unchanged. Do not
pass `-o`: the parent is updated in place. Use `--` after the command when an
operand is spelled like a global option.

Build `./lp5` in the checkout root as described in `AGENTS.md`, then test:

```sh
python3 test/add_article.py ./lp5
```
