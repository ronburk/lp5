# Expanded output

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/view_output.html` at the returned host. Click **Test expanded output**.
Expect PASS with 51 assertions; the complete fixture is restored for inspection.
The fixture endpoint invokes `test/output_fixture.py`, which tangles a temporary
project through the current harness. Default and named display text must retain
the same non-whitespace code and wrappers as those generated files; the Output
formatter may adjust indentation and blank-line whitespace for readability.

Checks cover multiple definitions, repeated/nested/inline references, XML
wrappers containing references, literal entities and HTML-looking code,
occurrence identity, article ownership/highlighting, Output-to-Source navigation,
Source-reference navigation without moving Source or TOC, switching to the
containing output, previewing unreferenced bundles, undefined-reference markers,
reload cache replacement, nested reference indentation, common fragment dedenting,
and article-only or named-output-only projects. Fold markers retain leading
indentation within their code section. Ctrl-click folds or unfolds one code
occurrence, preserving its actual trailing newline (including intentionally
absent newlines), with browser geometry checks for consecutive folded sections;
Ctrl-Shift-click folds all descendant code sections, preserving independent fold
state when outputs are switched.

Expansion and formatting live in separate View fragments. The formatter removes
each fragment's common leading spaces and adds the reference site's indentation
to continuation lines. Reference offsets and authored fragment text remain in
the expansion structure for navigation. No output files are written by the
application and no expanded code executes.
The fixture bypasses native directory permissions/persistence before startup.
