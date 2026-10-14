# State machine compiler

Run `python3 test/state_machine_compiler.py`. The test extracts the compiler
bundle through the harness, compiles examples, and executes them with an
experimental stack driver. It covers nested and immediately returning calls,
locals across calls, replacing transitions, caller preservation, generator
cleanup, repeated transitions without stack growth, ordered handlers,
wildcards, inline waits, forward targets, CRLF, repeated compilations, and
source-line diagnostics.

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/state_machine_compiler.html` at the supplied host. Expect PASS with 11
assertions. It extracts the actual generated namespace and defines a compiled
example through `util.scriptToFunction` in Chrome. Expand **Generated example**
to inspect the returned JavaScript.

Neither test modifies or replaces the production command dispatcher. The
compiler is exposed for exploration as `window.LP5.operations.compileStateMachine`;
the handwritten startup handlers remain in use. Tagged transitions are only
supported by the separate test drivers until the runtime protocol is approved.
