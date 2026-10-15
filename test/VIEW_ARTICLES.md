# Displaying loaded articles

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/view_articles.html` at the returned host. Click **Test article display**.
Expect PASS with 42 assertions.

The test runs the complete generated application, including startup hooks,
command routing, model loading, and the view's private model subscription. It
selects a controlled local fixture through the real dialog, then checks article
order, filename fallback, explanation HTML and SVG, code names, literal CDATA
and code references, independence from model XML, and pane-owned scrolling.
Long code lines scroll horizontally within each block, without wrapping or
vertical clipping, and follow narrower and wider pane sizes. Short blocks need
no horizontal scrollbar.
Reload and project replacement must replace the display and reset its scroll.
Native picker permissions and persistence are bypassed before startup.
The original three-article fixture is left visible for visual inspection.

The first rendering pass fills only the Source Pane. Table-of-contents
navigation and expanded output are not implemented here. Also run the existing
selection/loading and unit-startup browser tests to check integration.
