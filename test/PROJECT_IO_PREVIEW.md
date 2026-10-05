# LP5 project-I/O cloud-browser test

This is a test-only preview server. It serves only `new.html`, the test-control
and regression modules, and the three fixture articles; all other paths return 404. It is not part of the production
application.

Run it with the preview system's provided bind host and forwarded port, if any:

```sh
python3 test/preview_server.py --host 0.0.0.0 --port 8000
```

The server also accepts an optional positional `host port` pair and the
`HOST` / `PORT` environment variables. Open the preview system's HTTP(S) URL
for `/new.html?test=1`; use that supplied URL rather than `file://` or a guessed
loopback address. The ordinary `/new.html` URL keeps the native production
backend.

## Visible browser checks

1. Load `/new.html?test=1`. The Select or Create dialog should appear.
2. Select **Select**. The test adapter returns `lp5-test-project.lp5` without
   invoking a browser picker. Confirm the root title and both child titles are
   visible, and the explanation text identifies the HTTP fixture.
3. Confirm the output pane contains `Hello from the named Greeting section.`;
   this proves that the unnamed child fragment expanded its reference to the
   named section in `0.lp5`.
4. Click **View**. The View Settings dialog should open; click **Cancel** and
   confirm it closes and returns to the project.
5. Use the visible test controls to edit the root article. Change its heading
   or explanation in the application's editor and save. Click **Reload project**
   and confirm the change remains in the rendered article.
6. Click **Create article**. The application model's article-creation method
   should choose the next unused integer filename, write it in memory, and add
   it to the project tree.
7. Click **Add after article 0**, select **Add article**, and save the dialog.
   The code name should be prefilled with `Added after article 0`. The new
   article should appear immediately after `0.lp5` in the navigation order,
   and its entered title, explanation, and code should render after reloading.
8. Click **Add root child**, select **Add article**, and save. The new article
   should appear after the existing root children with `Added as root child`
   prefilled as its code name.
9. Open either add-article dialog again and click **Cancel**. No additional
   article should appear in navigation or in the test adapter's writes.
10. Click **Export output**. The adapter records the generated text at
   `window.LP5.testProjectIO.lastGeneratedOutput`.
11. In a fresh tab load `/new.html?test=1&fail=1.lp5` and select the fixture.
   The missing child should render the application's normal failed-load
   article, including `Controlled fixture read failure: 1.lp5`.

The adapter exposes its in-memory writes only in explicit test mode as
`window.LP5.testProjectIO.writes`, so browser checks can confirm exact filenames
and saved contents. It contains no native picker, IndexedDB, or filesystem
handle calls.

## Article deletion checks

Run `node test/delete_article.js` for the project-store removal contract, then
check the visible UI with `/new.html?test=1`:

1. Right-click the root article. It should offer first-child insertion but no
   **Delete Article** action.
2. Right-click a child and choose **Delete Article**. Cancel the confirmation;
   the source and navigation should remain unchanged.
3. Delete the leaf `1.lp5` and accept the confirmation. Reload the project;
   it should remain absent from source and navigation. Click **Inspect storage**
   and confirm `Removed files: 1.lp5` and a root child list containing only `0.lp5`.
4. In a fresh tab, add a first child under `0.lp5` using its context menu and
   save it with a recognizable heading. Delete `0.lp5`. Its child should take
   its place before `1.lp5`, survive reload, and remain editable. The root's
   heading and explanation should be preserved. The code reference to Greeting
   should become unresolved; deleting an article does not rewrite code references.
5. In a fresh tab use `/new.html?test=1&fail-remove=0.lp5`. Attempt to delete
   `0.lp5` and accept the confirmation. The normal error dialog should report
   `Controlled fixture removal failure: 0.lp5`. The stored root's children
   should still be `0.lp5`, `1.lp5`, and the removed-file set should be empty.
   Press Escape to close the error dialog, then click **Inspect storage** to
   see the stored parent XML and removal log.

## Move Article hierarchy checks

1. Select a navigation row, then right-click a source article and choose
   **Move Article**. Confirm the modal shows the root and all descendants in
   their source order, initially expanded, with the invoking article selected.
2. Select another row, collapse and expand a branch using its triangle, and
   close with **Close**. Repeat from a navigation row and close with Escape.
   The navigation selection must remain independent of the dialog selection.
3. Add a first child under `0.lp5` with documentation but no title or code name.
   Open **Move Article** for that child; its documentation excerpt and filename
   should label its row at the correct depth.
4. Clear the heading of `0.lp5`; its hierarchy label should use `Greeting`.
   Clear both heading and documentation of `1.lp5`; its label should use the
   literal code excerpt `Expanded section:`. Filenames remain visible for all
   rows, and a completely empty article uses `(empty article)`.
5. Open **Move Article** from the root. The root should appear selected, and
   the root context menu should still hide sibling insertion and deletion.
6. Drag a child onto the middle of another row. Confirm it becomes the first
   child, the dialog reports **Move saved**, and the moved article stays selected.
   Drop on the top/bottom third of a row to insert before/after it. Moving an
   article carries its descendants; article filenames and contents are retained.
7. Try dragging the root, dropping an article on itself or a descendant, and
   dropping beside the root. These must leave the hierarchy unchanged. A
   repeated move to the existing position must not write any files.
8. Close the dialog and click **Reload project**. Confirm the saved order and
   nesting remain in the source and navigation panes. **Inspect storage** shows
   the changed parent child lists; no article files are removed.
9. Click **Test article moves**. The browser runs `test/move_article.js` against
   the actual model operation with real XML DOMs and isolated in-memory stores.
   Expect **26 article move checks passed**. These cover all placements,
   subtree/content preservation, no-ops, invalid destinations, and rejected
   writes that have already modified their file, including restoration failures.
10. Open a fresh `/new.html?test=1&fail-write=2&write-delay=1500` tab. Move
    `0.lp5` into `1.lp5`. While saving, Close is disabled and Escape must not
    dismiss the dialog. The second parent write fails; the error is shown and
    the original hierarchy is restored. Repeat the drag; the one-time failure
    has passed and the move should succeed. The delay is in milliseconds and
    is capped at 5000; `fail-write` is the one-based write attempt to reject.

Each successful drop saves immediately. Same-parent moves write one article;
reparenting writes the destination parent first, then the old parent. On error,
all attempted writes are restored in reverse order from their original stored
text. Restoration failures identify the affected files and block further moves
in that dialog. The filesystem API cannot make the two writes crash-atomic.

## Output selection checks

1. Open `/new.html?test=1` and select the fixture project. Select the named
   Greeting article in Source or navigation. Its expanded text in Output should
   have a pale blue background; the unnamed caller's text should remain distinct.
2. Select the unnamed caller. Only `Expanded section:` should be highlighted;
   the expanded Greeting text belongs to its own article.
3. Click the Greeting text in Output. Its originating article should become
   selected in Source and its text highlighted in Output. Selecting the root,
   which has no code, should clear the Output highlight. Output must not scroll
   automatically when selection changes.
4. Click **Test output selection**. Expect **41 output selection checks passed**.
   The browser runs `test/output_selection.js` with the actual XML loader,
   Source/TOC/Output views, and isolated in-memory projects. It checks repeated
   and nested expansions, other sections in the same bundle, all three selection
   paths, quoted filenames, explanation-only/unreferenced/empty code, rerenders,
   same-project reloads and edited content, selection removal/project switching,
   and unchanged generated/displayed/exported text. It restores the original
   fixture project and selection after running.

## Validation boundaries

These checks exercise application behavior through the test adapter. They do
not test native directory selection, real filesystem permissions or disk
writes, or IndexedDB handle persistence. A cloud-browser result should be
reported only after opening the preview URL supplied by the environment and
completing the visible checks above.
