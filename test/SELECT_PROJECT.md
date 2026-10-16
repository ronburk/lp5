# Selecting and loading a project

Run `python3 test/select_project.py` for the async-work bundle checks. These
verify persistence before loading, success only after loading finishes, abort
behavior, and fatal picker/persistence/loading errors. The code under test is
obtained through the LP5 harness.

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/select_project.html` at the returned host. Click **Test selection and
loading**. It must report PASS with 49 assertions.

The page loads the complete generated application in fresh iframes. Before
startup it installs a controlled picker and bypasses handle persistence; the
controller, operations, dialog mounting/cleanup, and model loader are real.
It verifies loading keeps the dialog modal and ignores another Select, success
removes the dialog and its styles, abort permits retry, and a loading error
(including AbortError) displays the fatal modal. It also verifies Local/Remote
field switching, disabled remote Create, required URL validation, and the
absence of a root-filename override. A remote project stored as real temporary
files is selected through its directory URL, loading its identically named
root and linked child over HTTP without invoking the picker. The deliberate
local loading failure produces an expected console diagnostic.

This does not test native picker permissions or native handle persistence.
Successful local and remote selections also verify that articles appear in the
Source Pane. Detailed presentation checks are in `test/VIEW_ARTICLES.md`.
