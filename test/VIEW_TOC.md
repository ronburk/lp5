# Table of Contents

Build with `./lp5 lp5 tangle`, run `sites-preview start "$PWD"`, and open
`/test/view_toc.html` at the returned host. Click **Test table of contents**.
Expect PASS with 48 assertions. The complete generated app selects a controlled fixture through
the real startup dialog before testing the model/view connection.

Checks cover nested document order, filename fallback and duplicate titles,
accessible disclosure controls, nested collapse state, selection highlighting,
filenames containing quotes/brackets, Source Pane selection from headings,
explanations and code without scrolling or disturbing text selection, and navigation that changes only Source
scrolling while other panes have nonzero scroll positions. Reload must replace
both panes, refresh titles, preserve collapse state, and clear selection. A new
storage selection with the same root and article filenames must start expanded.
New parents added on reload start expanded. The model loader suite separately
checks selection IDs in load notifications.

Also run the article-display and selection/loading suites for presentation and
local/remote integration. Native directory permissions/persistence are bypassed.
Collapse state is retained within the current selection, not across browser
sessions. Reopening a location through a new storage object is a new selection.
