# Split pane views

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/view_splits.html` at the returned host. Click **Test split views**. The
complete generated application runs against a controlled project fixture.

The browser test checks that Source, TOC, and Output can each split into two
views at the current scroll position; each pair then scrolls independently.
Article selection, TOC collapse, and Output folding are shared. Pane scoped
Find searches the active copy, Source reference navigation targets the active
Output copy, and joining a split keeps the active view.

Also verify the pointer interaction in the application: drag the grip at the
top of an unsplit pane downward and confirm the preview line tracks the pointer.
Release to create a split at that position. Drag the horizontal divider to
resize the views, then activate **Join views**. Pointer cancellation must clear
the resizing cursor without creating or resizing a split.

Split state lasts for the current page session. Reloading the project rebuilds
both copies and resets their scroll positions; the split arrangement itself
remains in place.
