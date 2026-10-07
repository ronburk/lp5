# Search article text

```sh
./lp5 [-w weave-file] search [--all] [--] TEXT [TEXT ...]
```

The standalone `--` is optional. Every following argument is one literal search
string. Use `--` before terms that look like options. For example:

```sh
./lp5 search -- -o "save article"
./lp5 search --all -- -o "save article"
./lp5 search foo
```

Search looks in each article's heading, each keyword, explanation, code name,
and literal code text. It does not search filenames, child links, or text from
other articles referenced by code. Markup is flattened to its XML string value,
and each field is searched independently so a phrase cannot match across fields.

Terms and fields are normalized with XPath `normalize-space()` and ASCII A-Z to
a-z folding. Punctuation is preserved; matching is literal substring matching,
not regular-expression, whole-word, stemming, or token matching. Duplicate
canonical query terms are considered once. Default `any` mode returns articles
matching at least one term; `--all` requires each distinct term to occur in some
searched field of that article. Every matching article is returned, including
orphans, with no result cap. Results sort by descending weighted term score,
with weave order breaking ties.

## Returned document

Output is one UTF-8 XML document without a namespace, ending with a newline:

```xml
<lp5-search version="1" mode="any" total="1">
  <query><term>save article</term></query>
  <results>
    <article file="23.lp5" score="1">
      <matches>
        <match term="save article" field="explanation">
          <excerpt truncated-before="false" truncated-after="false">We save article text here.</excerpt>
        </match>
      </matches>
    </article>
  </results>
</lp5-search>
```

- `query` contains normalized, distinct terms in first-occurrence order.
- Each result's `score` is the sum of scores for its distinct matched query terms:
  2 points if a term matches any keyword, otherwise 1 point if it matches another
  searched field. Keyword matches use the same normalized literal substring
  rule as other fields. Repeated occurrences, matching multiple keywords, or
  matching both keywords and other fields do not add points for the same term.
  Results are in descending score, then weave order. `--all` still requires all
  distinct terms to match, regardless of their scores.
- `matches` contains one entry per matched term and field, ordered by query
  argument and then by the field's order in the article.
- Each `match` has exactly `term` and `field` attributes and one `excerpt` child.
- Excerpts preserve source case and normalized whitespace. They show up to 200
  characters centered around the first occurrence (or the whole term when it is
  longer), with a Unicode ellipsis where text was omitted. The two truncation
  attributes indicate whether text was omitted before or after the excerpt.
- A matching field may produce separate matches for multiple query terms. XML
  text and attributes are escaped by the serializer; parse the document rather
  than comparing entity spellings.

Search uses the shared weave freshness check and reads `weave.xml` in the working
directory by default. `-w <file>` selects another index for both freshness
checking and reading. It scans article records directly; `weave` does not
generate a separate full-text index. Output goes to stdout, or to the existing
`-o` destination with stdout empty. Invalid arguments, XML text, index, or
transform return status 1 with diagnostics on stderr.
