# Storage backend checks

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/storage.html` at the returned preview host. Expect PASS. This page runs
both backends from the actual generated namespace script, without startup UI.

The same contract checks run against controlled local directory handles and
HTTP backed by real temporary files: UTF-8 text, URL-encoded filenames,
replacement/truncation, empty files, listing, deletion, missing files, invalid
names, non-text stores, and canceled loads/listings. Additional checks cover
independent local projects, writable write/close failures and abort cleanup,
invalid remote URLs, reopening HTTP storage, malformed listings, and HTTP
errors. Native OPFS gets the contract checks too if available; otherwise its
absence is reported. Native picker, external filesystem permissions, network
interruption after a store commits, and cross-origin server configuration are
not covered.

The preview's `/test/storage-project/` endpoint uses GET/PUT/DELETE for files
and GET for its JSON file listing. It writes only into a temporary directory,
never the checkout or legacy fixtures. Stores stage complete bytes before
replacing a file; bodies are capped at 1 MiB. Data survives page reloads while
the server runs and is removed when the server stops. This endpoint is test
infrastructure; it is not a deployed remote-project service.

`storage.local` and `storage.remote` provide `open(...)` and the shared methods.
Use the object returned by open for operations; it inherits its backend's
methods and privately binds one location. Model and dialog integration is
separate work. See the Storage article for the interface and HTTP contract.
