# Read one complete source article

```sh
./lp5 [-s source-dir] [-o output-file] show-article [article-file.lp5]
```

With no filename, reads `lp5.lp5` in the selected source directory. A supplied
filename must be a single filename ending in `.lp5`, as returned by weave and
keyword search. It is resolved only under `LP5Source`; a same-named file in the
working directory does not take precedence. Paths and suffix-free article IDs
are not accepted. Global `-s`, `-o`, and the `LP5Source` environment variable
work as usual; `-m` is invalid.

Output is one UTF-8 XML document without a wrapper namespace, ending in a newline:

```xml
<lp5-article version="1" file="4.lp5">
  <template>
    <children><li id="5.lp5"/></children>
    <heading>Example <em>article</em></heading>
    <keywords><li>save article</li></keywords>
    <section data-lp5-kind="explanation"><p>The complete explanation.</p></section>
    <section data-lp5-kind="code">
      <name>Example bundle</name>
      <code><![CDATA[int example;
]]><lp5- ref="other bundle"/></code>
    </section>
  </template>
</lp5-article>
```

The root has exactly `version="1"` and `file` attributes. `file` is the source
filename, verbatim, relative to the selected directory. The sole child is the
complete source `template`, preserving its attributes, element order, absent
and empty fields, child links, raw keywords, inline markup, text whitespace,
comments, processing instructions, and code directives. No content is truncated,
normalized, expanded, or replaced with weave metadata. Following `children/li/@id`
with another `show-article` call provides the next navigation step.

This is a parsed XML copy, not a byte-for-byte file transfer. XML declarations,
entity spellings, quote styles, and original CDATA boundaries are not preserved.
Text inside `code` elements is serialized as CDATA, with references remaining
XML elements. Document-level comments, processing instructions, and the doctype
outside `template` are not part of the returned template.

The existing weave freshness preflight runs before dispatch, as with other read
commands. The article is then read directly from its source file and validated
with the same article validator as `check`. The command itself does not follow
child links or code references. Source files are not modified; refreshing the
generated weave cache is permitted.

Status 0 means success. Output goes to stdout, or to `-o` with stdout empty.
Diagnostics go to stderr. Invalid arguments, missing/malformed/invalid articles,
freshness failures, or transform failures return status 1 without result XML and
without truncating an existing output destination. Output I/O failures may leave
partial output; discard output whenever exit status is nonzero.

Build using the command at the top of `lp5.c`, then test:

```sh
python3 test/show_article.py /path/to/lp5
```
