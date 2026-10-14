# State machine compiler

Run `python3 test/state_machine_compiler.py`. The test extracts the compiler
bundle through the harness, compiles examples, and executes them with an
experimental stack driver. It covers nested and immediately returning calls,
locals across calls, replacing transitions, caller preservation, generator
cleanup, repeated transitions without stack growth, ordered handlers,
wildcards, forward targets, CRLF, repeated compilations, and
source-line diagnostics. Transitions inside both `for` and `while` loops must
exit the entire state without executing actions inside or after the loop;
the destination waits for the next command.

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/state_machine_compiler.html` at the supplied host. Expect PASS with 12
assertions. It extracts the actual generated namespace and reads the private
compiler through a test-only endpoint backed by harness `show-bundle`, then
defines a compiled example through `util.scriptToFunction` in Chrome. Expand **Generated example**
to inspect the returned JavaScript.

Neither test modifies the production command dispatcher. The compiler is
private to Operations; its startup hook installs the application's compiled
base/dialog states, which delegate the existing selection worker. Tagged
transitions are only supported by the separate test drivers until the runtime
protocol is approved. `test/unit_startup.html` verifies hook enumeration,
initialization order, and fatal reporting for compiler errors.
