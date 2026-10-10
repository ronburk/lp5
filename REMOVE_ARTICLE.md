# `remove-article`

```sh
lp5 remove-article <article-id.lp5>
```

Removes an existing non-root article and its unique parent link. The article
must be a leaf; remove or move its children first. The command refuses missing
articles, orphan roots without a parent link, and the root. Weave validation
rejects ambiguous parent links before this command runs.

The updated parent is generated and validated before either source file is
changed. The command stages the original parent so ordinary filesystem errors
during the update can be rolled back. It does not rewrite the selected weave
file; the next command that needs it will refresh it through the normal
freshness check.
