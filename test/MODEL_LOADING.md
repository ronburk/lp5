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

Model notifications use a private EventTarget exposed through addEventListener
and removeEventListener. Tests verify exactly one ProjectLoaded event per
successful load/reload, complete articles and indexes during notification,
notification before the load Promise resolves, subscriptions surviving reload,
once/removal behavior, and no completion events for selection, pending loads,
or failed loads. This event is separate from the controller completion command.
Its selectionId stays stable on reload and changes for a different opened
storage object, even if both projects have the same root filename.

If OPFS is available, the page creates uniquely named temporary projects,
loads an actual file, and uses two independent utility instances to add
handles concurrently. It verifies distinct projects are both retained,
equivalent directories converge on one ID, and deletion is idempotent. The
fixtures and their stored handles are removed afterward. If OPFS is unavailable,
the page reports that limitation. Run `python3 test/directory_handles.py` for
the same concurrency, deduplication, deletion, and database-reset scenarios
against a transaction-serializing IndexedDB test double and the actual utility
source. These checks do not exercise the native directory picker or
external-directory permissions.

The preview server allows only the specific test page and generated output
routes in addition to its existing legacy-app routes.
