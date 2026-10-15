# Expanded output

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/view_output.html` at the returned host. Click **Test expanded output**.
Expect PASS with 34 assertions; the complete fixture is restored for inspection.
The fixture endpoint invokes `test/output_fixture.py`, which tangles a temporary
project through the current harness. Default and named display text must match
those actual generated files exactly for the complete fixture.

Checks cover multiple definitions, repeated/nested/inline references, XML
wrappers containing references, literal entities and HTML-looking code,
occurrence identity, article ownership/highlighting, Output-to-Source navigation,
Source-reference navigation without moving Source or TOC, switching to the
containing output, previewing unreferenced bundles, undefined-reference markers,
reload cache replacement, and article-only or named-output-only projects.

Expansion and formatting live in separate View fragments. This first formatter
preserves whitespace rather than reconstructing indentation. Reference offsets
and authored fragment text remain in the expansion structure for the later pass.
No output files are written by the application and no expanded code executes.
The fixture bypasses native directory permissions/persistence before startup.
