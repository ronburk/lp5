# Browser database

Run `./lp5 lp5 tangle`, start the repository preview as described in
`BROWSER_TESTING.md`, and open `/test/browser_db.html` in cloud Chrome.
Expect a PASS result, then reload the same tab and expect a second PASS result
for persistence and cleanup.

This page evaluates the actual generated namespace script without invoking
application startup. It exercises real IndexedDB: missing keys, replacement,
removal, enumeration and key order, stored undefined, clone isolation, Date,
Map, typed arrays and cyclic values, invalid keys, uncloneable values,
preservation after failed replacement, and concurrent independent operations.
Reload verifies a committed value survives destruction of the page context.

Fixtures use a unique key prefix and remove only their own entries. A sentinel
remains until the reload step completes. No production caller is added.
Native directory handle persistence, browser permission prompts, blocked upgrades,
and browser eviction are not exercised by this test.
