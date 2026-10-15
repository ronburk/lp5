# Displaying loaded articles

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/view_articles.html` at the returned host. Click **Test article display**.
Expect PASS with 30 assertions.

The test runs the complete generated application, including startup hooks,
command routing, model loading, and the view's private model subscription. It
selects a controlled local fixture through the real dialog, then checks article
order, filename fallback, explanation HTML and SVG, code names, literal CDATA
and code references, independence from model XML, and pane-owned scrolling.
Reload and project replacement must replace the display and reset its scroll.
Native picker permissions and persistence are bypassed before startup.
The original three-article fixture is left visible for visual inspection.

The Source Pane and TOC rebuild together; expanded output remains unfinished.
`test/VIEW_TOC.md` covers hierarchy, navigation, and collapse state. Also run
the selection/loading browser tests to check integration.
