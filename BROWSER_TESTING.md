# Browser testing in OpenAI Work

Read this when verifying browser behavior or changing UI code. Also read the
relevant manual test notes under `test/*.md`. The harness build is documented
in [HARNESS.md](HARNESS.md).

Cloud Chrome may reject `file://` URLs or may not expose
`showDirectoryPicker`. Those are environment limitations, not evidence that
browser testing is unavailable.

Reuse an applicable preview and browser session. For initial setup, use the
provided `sites-preview` runner from this checkout:

1. Keep the checkout beneath `/workspace`.
2. Use this checkout's `package.json` `dev` script, which runs
   `test/preview_server.py`; do not start with a separate static-preview
   project.
3. Run `sites-preview start "$PWD"` and open the returned
   `http://terminal.local:...` URL.
4. Exercise the visible UI through CUA.

For native file I/O, select an explicit test adapter before startup (for
example, with a query parameter). The page evaluator is read-only and cannot
install a shim after the application starts.

Do not assume a test adapter from the older `new.html` application works in the
LP5 rewrite. When testing the rewrite, serve the generated output and inspect
that output's startup path for an adapter before choosing a test URL. A check of
`new.html?test=1` does not verify the generated program.

In particular, `test/PROJECT_IO_PREVIEW.md` and `test/ARTICLE_DETAILS.md`
describe the older `new.html?test=1` application. Use those scenarios only when
testing that application. They do not establish coverage for the generated LP5
rewrite; test the actual generated output and its own adapter and behavior.

`test/STORAGE.md` covers the rewrite's local and HTTP storage backends through
`/test/storage.html`. HTTP stores use real disposable server-side files at
`/test/storage-project/`; they do not use the legacy in-memory adapter. This
tests the storage unit separately from model and project-dialog integration.

`test/STARTUP_ERRORS.md` covers uncaught errors and unhandled rejections in
the complete generated application, including the permanent fatal-error modal.

If preview setup fails, check `command -v sites-preview`, the checkout path,
the startup configuration, and the exact runner error. Failure of a separate
static preview (including a `bwrap` `/proc` mount error) does not establish that
the repository preview is broken; test the existing `dev` script from the
checkout. Do not manually launch the preview daemon or retry denied escalation.

The server allowlists paths. To preview a new tangled HTML file, temporarily
add its route and restart the runner, then remove that temporary change after
capturing the result. Use the returned preview URL, not `file://` or the
execution container's loopback address. Native picker behavior, actual disk
permissions, and IndexedDB persistence remain separate tests.
