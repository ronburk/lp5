# LP5 project-I/O cloud-browser test

This is a test-only preview server. It serves only `new.html` and the three
fixture articles; all other paths return 404. It is not part of the production
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
4. Use the visible test controls to edit the root article. Change its heading
   or explanation in the application's editor and save. Click **Reload project**
   and confirm the change remains in the rendered article.
5. Click **Create article**. The application model's article-creation method
   should choose the next unused integer filename, write it in memory, and add
   it to the project tree.
6. Click **Export output**. The adapter records the generated text at
   `window.LP5.testProjectIO.lastGeneratedOutput`.
7. In a fresh tab load `/new.html?test=1&fail=1.lp5` and select the fixture.
   The missing child should render the application's normal failed-load
   article, including `Controlled fixture read failure: 1.lp5`.

The adapter exposes its in-memory writes only in explicit test mode as
`window.LP5.testProjectIO.writes`, so browser checks can confirm exact filenames
and saved contents. It contains no native picker, IndexedDB, or filesystem
handle calls.

## Validation boundaries

These checks exercise application behavior through the test adapter. They do
not test native directory selection, real filesystem permissions or disk
writes, or IndexedDB handle persistence. A cloud-browser result should be
reported only after opening the preview URL supplied by the environment and
completing the visible checks above.
