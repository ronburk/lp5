# Model loading checks

Build the generated rewrite with `./lp5 lp5 tangle`, then start this checkout's
preview with `sites-preview start "$PWD"`. In CUA Chrome, open the returned host
at `/test/model_load_project.html`. The page must report `PASS`.

The test evaluates the actual generated namespace script without its startup
dialog. It exercises `model.loadProject()` using Chrome's real XML parser,
serializer, and File objects. File handles are controlled fixtures, and their
selection persistence is temporarily stubbed so malformed fixture projects do
not enter the browser's remembered-directory set.

Checks cover ordered reachable-only reads, filename lookup, parent links,
bundles/referrers, detached XML and draft serialization, invalid XML/schema,
unsafe links, missing files, duplicate parents, article/bundle cycles, undefined
references, and output-name errors. They also verify immediate old-state
discard, no partial publication, empty state after failure, and successful retry.

If OPFS is available, the page additionally creates a uniquely named temporary
project, writes and loads an actual file, and verifies its native directory
handle is persisted in IndexedDB. The test removes that fixture and its stored
handle afterward. If OPFS is unavailable, the page reports that limitation.
These checks do not exercise the native directory picker or external-directory
permissions.

The preview server allows only the specific test page and generated output
routes in addition to its existing legacy-app routes.
