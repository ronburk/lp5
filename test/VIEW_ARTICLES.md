# Displaying loaded articles

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/view_articles.html` at the returned host. Click **Test article display**.
Expect PASS with 43 assertions.

The test runs the complete generated application, including startup hooks,
command routing, model loading, and the view's private model subscription. It
selects a controlled local fixture through the real dialog, then checks article
order, heading omission for untitled articles, explanation HTML and SVG, code names, literal CDATA
and code references, independence from model XML, and pane-owned scrolling.
Long code lines scroll horizontally within each block, without wrapping or
vertical clipping, and follow narrower and wider pane sizes. Short blocks need
no horizontal scrollbar.
Reload and project replacement must replace the display and reset its scroll.
Native picker permissions and persistence are bypassed before startup.
The original three-article fixture is left visible for visual inspection.

The Source Pane and TOC rebuild together; expanded output remains unfinished.
`test/VIEW_TOC.md` covers hierarchy, navigation, and collapse state. Also run
the selection/loading browser tests to check integration.

After the test passes, drag each divider in the displayed application. Verify
that only its two neighboring panes exchange width and their combined width
stays constant. Drag beyond a neighbor's minimum: it should stop at 100 CSS
pixels when sufficient space exists. Release outside the narrow divider and
verify dragging stops and text selection works again. Resize the browser and
verify pane proportions remain useful without overflowing the main row.
Code blocks must continue to scroll horizontally without vertical clipping.
Pointer cancellation and lost capture must also clear the resizing style.
