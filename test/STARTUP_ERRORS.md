# Startup error reporting

Build with `./lp5 lp5 tangle`, start `sites-preview start "$PWD"`, and open
`/test/startup_errors.html` at the supplied host. Run each of the three buttons:
uncaught Error, unhandled rejection with an Error, and rejection with a string.
Each scenario loads the complete generated application in a fresh iframe and
must report PASS with 11 assertions. These cover ordinary startup, first-error
message text, modal state, safe text rendering, browser reload instruction,
absence of recovery controls, retained default diagnostic reporting, prevented
cancellation, and preservation of the first message after another failure.

Click inside the error dialog and press Escape in CUA. It must remain open.
The underlying Select/Create dialog must be inaccessible while the fatal modal
is open. This is a UI block only: the first cut does not stop timers, queued
commands, or in-flight async operations, and does not catch errors before the
Startup module runs. Each fixture error/rejection deliberately emits its
normal console diagnostic; that diagnostic is expected, not a test failure.
