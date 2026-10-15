#!/usr/bin/env python3
"""Exercise the compiler bundle with an experimental driver, not the app loop."""
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parent.parent
bundle = subprocess.check_output(
    ["./lp5", "lp5", "show-bundle", "State Machine Compiler"], cwd=repo)
code = ET.fromstring(bundle).find("section/code").text

tests = r'''
const assert = require("node:assert/strict");
const compile = new Function(CODE + "; return compileStateMachine;")();
function machine(source, log = []) {
    return new Function("log", compile(source))(log);
}
function driver(machine) {
    const stack = [machine.states[machine.initialState]()];
    return { stack, send(event) {
        while (stack.length) {
            const current = stack.at(-1);
            const result = current.next(event);
            if (result.done) stack.pop();
            else if (result.value === current) return;
            else if (result.value?.transition) {
                current.return();
                stack[stack.length - 1] = result.value.transition;
                return;
            } else stack.push(result.value);
        }
    }};
}
{
    const log = [];
    const m = machine(`
log.push("initialized");
let shared = 0;
state root
    on Start
        const local = ++shared;
        log.push(["root", state, event.name, local]);
        ->() child
        log.push(["resumed", event.name, local, shared]);
        -> done
state child
    on Start
        shared++;
        ->() grandchild
        log.push(["child resumed", event.name]);
        return;
state grandchild
    on Finish
        log.push(["grandchild", event.name]);
        return;
state done
    log.push(["done entry", event.name]);
    on Next
        log.push("next");
`, log);
    assert.equal(m.initialState, "root");
    assert.deepEqual(Object.keys(m.states), ["root", "child", "grandchild", "done"]);
    const d = driver(m);
    assert.deepEqual(log, ["initialized"], "Priming does not run a state body");
    d.send({name: "Start"});
    assert.equal(d.stack.length, 3);
    d.send({name: "Ignored"});
    assert.equal(d.stack.length, 3);
    d.send({name: "Finish"});
    assert.equal(d.stack.length, 1);
    assert.deepEqual(log, ["initialized", ["root", "root", "Start", 1],
        ["grandchild", "Finish"], ["child resumed", "Finish"], ["resumed", "Finish", 1, 2]]);
    d.send({name: "Next"});
    assert.deepEqual(log.slice(-2), [["done entry", "Next"], "next"]);
}
{
    const log = [];
    const d = driver(machine(`
state parent
    on Start
        ->() first
        log.push(["parent resumed", event.name]);
        return;
state first
    on Start
        try {
            -> second
        } finally {
            log.push("first closed");
        }
state second
    log.push(["second", event.name]);
    on Finish
        return;
`, log));
    d.send({name: "Start"});
    assert.equal(d.stack.length, 2, "Replacing a child preserves its parent");
    assert.deepEqual(log, ["first closed"]);
    d.send({name: "Finish"});
    assert.equal(d.stack.length, 0);
    assert.deepEqual(log, ["first closed", ["second", "Finish"], ["parent resumed", "Finish"]]);
}
{
    const log = [];
    const d = driver(machine(`
state a
    on Switch
        if (event.go) {
            -> b // forward target
        }
        log.push("stay");
state b
    on Switch
        -> a
`, log));
    d.send({name: "Switch", go: false});
    assert.deepEqual(log, ["stay"]);
    for (let i = 0; i < 1000; i++) d.send({name: "Switch", go: true});
    assert.equal(d.stack.length, 1, "Transitions must not accumulate stack frames");
}
{
    const log = [];
    const d = driver(machine(`
state loop
    on Go
        for (let i = 0; i < 2; i++) {
            ->() child
            log.push(i);
        }
        return;
state child
    on *
        return;
`, log));
    d.send({name: "Go"});
    assert.deepEqual(log, [0, 1], "Immediate child returns preserve loop continuation");
    assert.equal(d.stack.length, 0);
}
for (const loop of ["for (let i = 0; i < 2; i++)", "while (true)"]) {
    const log = [];
    const d = driver(machine(`
state original
    on Go
        ${loop} {
            log.push("before transition");
            -> destination
            log.push("incorrectly continued inside loop");
        }
        log.push("incorrectly continued after loop");
state destination
    on Next
        log.push("destination");
`, log));
    const old = d.stack[0];
    d.send({name: "Go"});
    assert.deepEqual(log, ["before transition"], "Transition exits the entire state inside " + loop);
    assert.equal(d.stack.length, 1);
    assert.notEqual(d.stack[0], old, "Transition replaces the old frame");
    assert.equal(old.next().done, true, "Old generator is closed");
    d.send({name: "Next"});
    assert.deepEqual(log, ["before transition", "destination"], "Destination waits for next command");
}
{
    const log = [];
    const d = driver(machine(`
state ready
    on Finish
        log.push("named");
    on *
        log.push("wildcard");
`, log));
    d.send({name: "Finish"});
    d.send({name: "Other"});
    assert.deepEqual(log, ["named", "wildcard"]);
}
{
    const log = [];
    const d = driver(machine(`
state parent
    log.push(["parent entry", event.name]);
    on Call
        ->() child
        log.push("returned");
state child
    const saved = event.value;
    log.push(["child entry", saved]);
    on Call
        log.push("initial command handled");
    on Done
        log.push(["done", saved]);
        return;
`, log));
    assert.deepEqual(log, [], "Entry waits for the initiating command, not priming");
    d.send({name: "Call", value: 1});
    d.send({name: "Ignored"});
    d.send({name: "Done"});
    d.send({name: "Call", value: 2});
    d.send({name: "Ignored"});
    d.send({name: "Done"});
    assert.deepEqual(log, [["parent entry", "Call"], ["child entry", 1],
        "initial command handled", ["done", 1], "returned", ["child entry", 2],
        "initial command handled", ["done", 2], "returned"],
        "Entry runs once per call and entry locals survive across commands");
}
{
    const log = [];
    const d = driver(machine(`
state once
    log.push(event.name);
    return;
`, log));
    d.send({name: "Start"});
    assert.deepEqual(log, ["Start"], "States without on clauses can finish in entry code");
    assert.equal(d.stack.length, 0);
}
for (const [source, expected] of [
    ["", /line 1: No states/],
    ["on Go", /line 1: on requires/],
    ["-> first", /line 1: An arrow requires/],
    ["state a\nstate a", /line 2: Duplicate/],
    ["state a\n-> missing", /line 2: Undefined/],
    ["state a\n->() missing", /line 2: Undefined/],
    ["state a\n->() *", /line 2: Malformed/],
    ["state a\n-> *", /line 2: Malformed/],
    ["state a trailing", /line 1: Malformed/],
    ["state a\non Go trailing", /line 2: Malformed/],
    ["state a\n->()", /line 2: Malformed/]
]) assert.throws(() => compile(source), expected);
assert.throws(() => compile(null), TypeError);
assert.throws(() => machine("state a\non Go\nconst = 1;"), SyntaxError);
assert.equal(machine("state fresh\r\non *\r\nreturn;").initialState, "fresh",
    "Compilations have independent parser state and support CRLF");
assert.equal(driver(machine("state __proto__\non *\nreturn;")).stack.length, 1);
console.log("PASS: per-state generators, calls/returns, transitions, wildcard handling, and diagnostics");
'''
subprocess.run(["node"], input="const CODE = " + json.dumps(code) + ";\n" + tests,
               text=True, cwd=repo, check=True)
