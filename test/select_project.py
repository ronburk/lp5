#!/usr/bin/env python3
"""Check picker outcomes using the actual async-work bundle from the harness."""
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parent.parent
bundle = subprocess.check_output(
    ["./lp5", "lp5", "show-bundle", "SelectProject async work"], cwd=repo)
code = ET.fromstring(bundle).find("section/code").text
tests = r'''
const assert = require("node:assert/strict");
const commands = [];
const window = {};
const controller = { dispatch(command) { commands.push(command); } };
const calls = [];
const model = {
    async selectProject(handle) { calls.push(["select", handle]); },
    async loadProject() { calls.push(["load"]); }
};
const run = new Function("window", "controller", "model", CODE + "; return asyncSelectProject;")(window, controller, model);

(async () => {
    for (const errorName of ["SecurityError", "NotFoundError", "TypeError"]) {
        for (const synchronous of [true, false]) {
            const error = new Error("Picker failed");
            error.name = errorName;
            window.showDirectoryPicker = synchronous
                ? () => { throw error; }
                : () => Promise.reject(error);
            await assert.rejects(run(), actual => actual === error);
            assert.equal(commands.length, 0, "Fatal error must not restore the dialog handler");
        }
    }

    const handle = { name: "example.lp5" };
    window.showDirectoryPicker = async () => handle;
    await run();
    assert.deepEqual(commands.pop(), { name: "ProjectLoaded" });
    assert.deepEqual(calls, [["select", handle], ["load"]]);
    calls.length = 0;

    for (const stage of ["selectProject", "loadProject"]) {
        for (const errorName of ["AbortError", "Error"]) {
            const error = new Error("Model failed");
            error.name = errorName;
            const original = model[stage];
            model[stage] = async () => { throw error; };
            await assert.rejects(run(), actual => actual === error);
            assert.equal(commands.length, 0, "Model errors must not produce completion commands");
            model[stage] = original;
        }
    }
    calls.length = 0;

    let finishSelection, finishLoad;
    model.selectProject = handle => new Promise(resolve => {
        calls.push(["select", handle]); finishSelection = resolve;
    });
    model.loadProject = () => new Promise(resolve => {
        calls.push(["load"]); finishLoad = resolve;
    });
    const pending = run();
    await Promise.resolve();
    assert.deepEqual(calls, [["select", handle]]);
    assert.equal(commands.length, 0);
    finishSelection();
    await Promise.resolve();
    assert.deepEqual(calls, [["select", handle], ["load"]]);
    assert.equal(commands.length, 0);
    finishLoad();
    await pending;
    assert.deepEqual(commands.pop(), { name: "ProjectLoaded" });
    calls.length = 0;

    for (const synchronous of [true, false]) {
        const error = new DOMException("Picker aborted", "AbortError");
        window.showDirectoryPicker = synchronous
            ? () => { throw error; }
            : () => Promise.reject(error);
        await run();
        assert.deepEqual(commands.pop(), { name: "ProjectPickerAborted", error });
    }
    assert.equal(commands.length, 0);
    assert.equal(calls.length, 0, "Aborts must not select or load a model");
    console.log("PASS: selection/loading order, delayed completion, aborts, and fatal picker/model errors");
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
subprocess.run(["node"], input="const CODE = " + json.dumps(code) + ";\n" + tests,
               text=True, cwd=repo, check=True)
