# Model loading checks

Build the generated rewrite with `./lp5 lp5 tangle`, then start this checkout's
preview with `sites-preview start "$PWD"`. In CUA Chrome, open the returned host
at `/test/model_load_project.html`. The page must report `PASS`.

The test evaluates the actual generated namespace script without its startup
dialog. It exercises `model.loadProject()` using Chrome's real XML parser,
serializer, and File objects. Controlled directory handles are opened through
storage.local and passed to the model as storage objects. Model selection no
longer persists handles; the selecting operation owns persistence.

Checks cover ordered reachable-only reads, filename lookup, parent links,
bundles/referrers, detached XML and draft serialization, invalid XML/schema,
unsafe links, missing files, duplicate parents, article/bundle cycles, and
output-name errors. Undefined direct/nested references (including unused
bundles) are allowed, retain deduplicated referrers, and resolve when their
definitions are added and the project reloaded. They also verify immediate old-state
discard, no partial publication, empty state after failure, and successful retry.

If OPFS is available, the page additionally creates a uniquely named temporary
project, writes and loads an actual file, and verifies its native directory
handle can be persisted separately using the utility. The test removes that fixture and its stored
handle afterward. If OPFS is unavailable, the page reports that limitation.
These checks do not exercise the native directory picker or external-directory
permissions.

The preview server allows only the specific test page and generated output
routes in addition to its existing legacy-app routes.
