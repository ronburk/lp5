# List the indexed keyword vocabulary

```sh
./lp5 [-s source-dir] [-w weave-file] [-o output-file] list-keywords
```

The command accepts no positional arguments or command-specific options. Global
`-s`, `-w`, `-o`, and the `LP5Source` environment variable work as usual; `-m`
is invalid. It refreshes `weave.xml` by default through the same freshness check
as `search-keywords`; `-w` selects a different index for both refresh and reading.

Output is a UTF-8 XML document without a namespace, ending with a newline:

```xml
<lp5-keywords version="1" total="2">
  <keyword article-count="3">persistence</keyword>
  <keyword article-count="2">save article</keyword>
</lp5-keywords>
```

The root attributes are exactly `version="1"` and `total`, the number of distinct
keywords. Each direct child is a text-only `keyword` with exactly one attribute,
`article-count`, the number of distinct articles containing that keyword.
Integer attributes are canonical decimal values. Keywords sort in ascending
XSLT text order, as in the weave index. All terms are returned, including those
belonging to orphan articles. Empty vocabulary succeeds with `total="0"`.

Terms have the same canonical form used by search: XPath `normalize-space()`
followed by ASCII A-Z to a-z folding. Empty terms are ignored. Duplicate terms
within one article count once. Unicode case and normalization remain unchanged;
commas, option-like names, quotes, and markup-like strings are ordinary data.
Parse the XML; formatting and entity spellings are not contractual. Listed text
can be passed as one literal keyword argument after search's `--` separator.

The compiled keyword index provides membership. A fresh older cache without that
index is supported using its article records. Source articles are not modified.
The cache must have a no-namespace `lp5-weave` root with exactly one direct
`articles` child, which may be empty.

Status 0 means success, including no keywords. Output goes to stdout, or to `-o`
with stdout empty. Diagnostics go to stderr. Invalid arguments, cache failures,
and transform failures return status 1 without result XML or truncating an
existing output destination. Output I/O failures may leave partial output;
discard output on nonzero exit status.

Build using the command at the top of `lp5.c`, then test:

```sh
python3 test/list_keywords.py /path/to/lp5
```
