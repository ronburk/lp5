# LP5 article format

Read this when creating or editing `.lp5` source articles, discussing bundles,
or changing the article parser or tangler. The harness and its commands are
documented in [HARNESS.md](HARNESS.md).

An **article** is one `.lp5` file. It is an XML document with one `<template>`
root. The root may contain at most one each of these direct children, in any
order:

- `<children>` (optional): child-article links as `<li id="name.lp5"/>`.
- `<heading>` (optional): display title.
- `<keywords>` (optional): zero or more `<li>` elements, each with a text-only
  keyword. Whitespace between list items is allowed. The editor trims terms,
  ignores empty terms, and permits an empty element for legacy articles.
- `<section data-lp5-kind="explanation">` (optional): explanatory HTML/XML
  content. Inline HTML `<code>` elements here are ordinary inline code.
- `<section data-lp5-kind="code">` (optional): one code section containing
  exactly one `<name>` and one `<code>` child.

Each permitted direct child may appear at most once. Each section kind may
appear at most once, and no other `data-lp5-kind` value is allowed. In a code
section, `<name>` is required but may be empty; an empty name denotes the
unnamed/root fragment. `<code>` is required but may be empty. Its children must
be CDATA sections containing literal code or XML elements whose names start
with `lp5-` (for example, `<lp5- ref="name"/>`) representing code
directives/references. Ordinary literal code belongs in CDATA; whitespace
between child nodes is formatting whitespace. If an article has no code
fragment, omit the code section.

`data-lp5-kind` distinguishes explanation and code sections from inline HTML
`<code>` markup in explanations.

A **bundle** is the ordered set of code sections that share the same `<name>`
value. A named bundle is not required to be unique to one article; all matching
sections combine in source weave order. `<lp5- ref="name"/>` expands that
bundle at the reference site.

## Output bundles

A nonempty bundle name whose trimmed value begins with `<` and ends with `>` is
also an output declaration. Its interior is the output filename; for example,
`<app.js>` names both a bundle and an output file. Every section in that bundle
contributes to the output in normal bundle order. References to an output bundle
expand its code just like references to any other named bundle. The unnamed
bundle remains the default output `X.out` for project `X`, with map `X.map`.

Output names must be plain filenames inside the project source directory. The
harness rejects path separators, unsafe platform filename characters,
collisions, and output bundles defined only in orphan articles. See
[HARNESS.md](HARNESS.md) for output paths and tangle invocation.
