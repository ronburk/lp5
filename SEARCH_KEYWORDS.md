# Search articles by keyword

To inspect the indexed vocabulary first, use `./lp5 list-keywords`.
See [LIST_KEYWORDS.md](LIST_KEYWORDS.md) for its XML output contract.

```sh
./lp5 [-s source-dir] [-o output-file] search-keywords [--all] -- KEYWORD [KEYWORD ...]
```

Examples:

```sh
./lp5 search-keywords -- persistence "save article"
./lp5 search-keywords --all -- "save article" persistence
./lp5 search-keywords -- "O'Reilly, C++" "</keyword>" "-o" "--all"
./lp5 -s other.lp5 -o matches.xml search-keywords -- persistence
```

One shell argument is one complete keyword. Commas and spaces inside an argument
are ordinary data. The first standalone `--` is required; every subsequent
argument is a literal keyword, including another `--` or strings equal to options.
Before the separator, `--all` is allowed once; other command arguments are errors.
Global `-s`, `-o`, and `LP5Source` retain their existing behavior. Global options
are removed before dispatch only up to `--`. `-m` is invalid for search.

At least one keyword is required. Empty normalized terms, invalid UTF-8, and
characters forbidden in XML 1.0 are errors. Terms are canonicalized using XPath
`normalize-space()` (trim and collapse space, tab, CR, and LF), then ASCII A-Z
to a-z conversion. All other characters are preserved: Unicode case, non-XML
whitespace, and Unicode normalization are unchanged. Canonical query duplicates
are removed, retaining the first occurrence. Stored empty terms are ignored;
duplicate stored terms count once. Matching is whole-term equality.

Default `any` mode returns articles matching at least one query term. `--all`
returns articles matching every distinct term. Score is the number of distinct
matched query terms. Results sort by descending score, with weave order breaking
ties. Every match is returned, including orphans; there is no result cap or
pagination. Scores indicate keyword overlap, and weave order represents hierarchy
and orphan ordering. Agents should consider the complete candidate set.

## Returned document

Output is one UTF-8 XML 1.0 document without a namespace, ending with a newline:

```xml
<lp5-keyword-search version="1" mode="any" total="1">
  <query><keyword>persistence</keyword><keyword>save article</keyword></query>
  <results>
    <article file="23.lp5" score="2">
      <matched-keywords><keyword>persistence</keyword><keyword>save article</keyword></matched-keywords>
      <heading>Saving &amp; reloading articles</heading>
      <code-name>project_io</code-name>
      <excerpt truncated="false">Writes revised articles through the project store.</excerpt>
    </article>
  </results>
</lp5-keyword-search>
```

- Root attributes are exactly `version="1"`, `mode="any"` or `"all"`, and
  `total` (the returned article count). Children are exactly `query`, then `results`.
- `query` contains each canonical distinct term as a text-only `keyword`, in
  first occurrence order. `results` contains every qualifying `article`.
- Each result has exactly `file` (weave `@file` verbatim, relative to the selected
  source directory) and `score` (canonical decimal match count).
- Result children, in order: `matched-keywords`, optional `heading`, optional
  `code-name`, optional `excerpt`. Matched terms are text-only `keyword` children
  in query order.
- `heading` is present exactly when the article has a heading, and contains
  `normalize-space(string(heading))`.
- `code-name` is present exactly when the article has a code section, and contains
  `normalize-space(string(section[@data-lp5-kind='code']/name))`. Empty means
  unnamed code; absence means no code section.
- `excerpt` is present exactly when the article has an explanation section. Its
  normalized XPath string value is limited to 200 Unicode characters, without
  an ellipsis. The sole attribute `truncated` is `true` when the full normalized
  value exceeds 200 characters, otherwise `false`.
- Present empty metadata produces an empty element. Scalars contain text only;
  inline markup is flattened by XPath string value, without invented separators.
  Heading and code-name case is preserved.

Integer attributes have canonical decimal values. No other elements or attributes
are introduced. XML formatting and entity spellings are not contractual; parse
the document. Data resembling schema names, closing tags, or old parameter
sentinels remains literal data, escaped by the XML serializer. Previews are not
unique identifiers; read the article identified by `file` for complete content.

## Cache and errors

Search uses the existing shared `ensure_weave_current()` preflight and reads
`weave.xml` from the working directory. Its keyword index provides membership;
the article records provide metadata and ordering. A fresh older cache lacking
the keyword index is supported by deriving membership from its article records.
Search never edits articles; refreshing the generated cache is permitted.

Success is status 0, including no matches (`total="0"` and empty `results`).
Output goes to stdout, or to the existing `-o` destination with stdout empty.
Diagnostics and refresh warnings go to stderr. Invalid arguments, index reads,
or transforms return status 1 without result XML. The index must have an
`lp5-weave` root with exactly one direct `articles` child; an empty collection
is allowed. Output starts only after the transform succeeds. Output I/O failures
may leave partial output; discard output whenever the exit status is nonzero.

## Checks

Build with the gcc command at the top of `lp5.c`, then run:

```sh
python3 test/search_keywords.py /path/to/lp5
```

The fixtures exercise ranking, normalization, escaping, complete result lists,
metadata, literal option-like terms, invalid input, cache errors and refresh,
project selection, and output failures through the production command.
