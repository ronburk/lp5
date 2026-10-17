# Displaying loaded articles

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/view_articles.html` at the returned host. Click **Test article display**.
Expect PASS with 83 assertions, including unclipped editor focus outlines,
tighter title spacing, Source as the initial selected pane, and Ctrl-F search
confined to the selected pane.

The find-bar checks cover shortcut capture, match counting and navigation, and
scope changes when the selected pane changes. The article layout check keeps the
first explanation line close to its title. The test runs the complete generated
application, including startup hooks,
command routing, model loading, and the view's private model subscription. It
selects a controlled local fixture, then checks article order, headings,
explanation HTML and SVG, literal code and references, internal explanation
links, and context menu behavior. It exercises the structured Edit Article
dialog: fields load from the article, the code reference marker is converted
back to an `<lp5- ref>` element, malformed XML markup is rejected, typing code
creates a code section, and clearing its name and code removes it. Saved fields
update the article and refresh Source and TOC; Cancel leaves storage unchanged.
The fixture also verifies markup rendering stays independent of the model XML
and checks pane-owned scrolling.

Internal links select and scroll the target article in Source without changing
the URL or Output scroll. Long code lines scroll horizontally within each
block, without wrapping or vertical clipping, and follow narrower and wider
pane sizes. Short blocks need no horizontal scrollbar. Reload and project
replacement must replace the display and reset its scroll. Native picker
permissions and persistence are bypassed before startup. The edited three-
article fixture is left visible for inspection.

The editor panes are separately scrollable and their divider supports pointer
dragging and arrow-key adjustment. Manually resize the editor and verify the
fields remain usable at narrower and wider sizes.

The Source Pane, TOC, and Output rebuild together. `test/VIEW_SPLITS.md` covers two-view split behavior, independent scroll positions, and shared data state. `test/VIEW_TOC.md` covers hierarchy and navigation; `test/VIEW_OUTPUT.md` covers expansion and cross-pane navigation.
