# Discover and read code bundles

```sh
./lp5 show-bundle                  # list every bundle name
./lp5 show-bundle "Bundle name"    # read one bundle from weave.xml
./lp5 show-bundle weave.xml        # read the bundle named "weave.xml"
./lp5 show-bundle ""               # read the unnamed bundle
./lp5 show-bundle -- "weave.xml"   # read a bundle named weave.xml
./lp5 show-bundle -- "-o"          # read a name equal to a global option
```

The index defaults to `weave.xml` in the working directory. The shared freshness
check runs first, using `LP5Source` (including environment and `-s` overrides).
Global `-o` redirects output, and `-m` is invalid. No source articles are modified.

With no name, returns one UTF-8 XML document ending with a newline:

```xml
<bundles><bundle name=""/><bundle name="Bundle name"/></bundles>
```

The no-namespace `bundles` root has no attributes. Each child is an empty `bundle`
with exactly one `name` attribute. Names are distinct, in first-occurrence weave
order, including bundles belonging to orphans. No bundles returns `<bundles/>`.
The empty name denotes unnamed code. Names are the indexed XPath-normalized
string values, including flattened inline markup; they are not lowercased.
Parse XML to retrieve names containing quotes, ampersands, or other special text.

A supplied name, including an explicit empty string, retains the existing
extraction format: `<bundle name="..."><section data-lp5-kind="code"
article="..."><name>...</name><code>...</code></section>...</bundle>`.
The supplied name undergoes XPath `normalize-space()`. Sections follow bundle
order and retain code text, whitespace, inline name markup, and code references;
references are not expanded. A nonexistent name succeeds with an empty bundle.

The old two-argument form remains supported for selecting an explicit index:

```sh
./lp5 show-bundle other-index.xml "Bundle name"
```

With one argument, that argument is always the bundle name, even when it ends
in `.xml` or matches a filename such as `weave.xml`. Use `--` when a bundle name
collides with a global option; the token following it is always treated as the
bundle name. The legacy two-argument form selects an explicit index and extracts
the named bundle. Listing and extraction also work when applying the stylesheet
directly: omitted `code_name` lists names, and a string parameter (including
empty) extracts one bundle. No string is reserved as an omission marker.

The index must have a no-namespace `lp5-weave` root and exactly one direct
`bundles` child. Empty `bundles` is valid. Invalid arguments/index/transforms or
freshness failures return status 1, with diagnostics on stderr, no result XML,
and no truncation of an existing output destination. Output I/O failures may
leave partial output; discard it on nonzero exit status.

Build with the command at the top of `lp5.c`, then run:

```sh
python3 test/show_bundle.py /path/to/lp5
```
