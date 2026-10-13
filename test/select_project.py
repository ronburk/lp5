#!/usr/bin/env python3
"""Check local/remote selection using the actual async-work bundle."""
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
const commands = [], calls = [];
const handle = {name: "example.lp5"};
const localProject = {root_filename: "example.lp5"};
const remoteProject = {root_filename: "remote.lp5"};
const window = {showDirectoryPicker: async () => handle};
const controller = {dispatch(command) { commands.push(command); }};
const model = {
    async selectProject(project) { calls.push(["select", project]); },
    async loadProject() { calls.push(["load"]); }
};
const storage = {
    local: {open(actual) { assert.equal(actual, handle); return localProject; }},
    remote: {open(url) { assert.equal(url, "https://example.com/remote.lp5/"); return remoteProject; }}
};
const util = {indexedDB: {async storeDirectoryHandle(actual) { calls.push(["persist", actual]); }}};
const run = new Function("window", "controller", "model", "storage", "util",
    CODE + "; return asyncSelectProject;")(window, controller, model, storage, util);
const local = {location: "local"};
(async () => {
    for (const errorName of ["SecurityError", "NotFoundError", "TypeError"]) {
        for (const synchronous of [true, false]) {
            const error = new Error("Picker failed"); error.name = errorName;
            window.showDirectoryPicker = synchronous ? () => { throw error; } : () => Promise.reject(error);
            await assert.rejects(run(local), actual => actual === error);
            assert.equal(commands.length, 0);
        }
    }
    window.showDirectoryPicker = async () => handle;
    await run(local);
    assert.deepEqual(commands.pop(), {name: "ProjectLoaded"});
    assert.deepEqual(calls, [["persist", handle], ["select", localProject], ["load"]]);
    calls.length = 0;
    window.showDirectoryPicker = () => { throw new Error("Must not invoke picker"); };
    await run({location: "remote", url: "https://example.com/remote.lp5/"});
    assert.deepEqual(commands.pop(), {name: "ProjectLoaded"});
    assert.deepEqual(calls, [["select", remoteProject], ["load"]]);
    calls.length = 0;
    window.showDirectoryPicker = async () => handle;
    for (const [object, stage] of [[util.indexedDB, "storeDirectoryHandle"], [model, "selectProject"], [model, "loadProject"]]) {
        for (const name of ["AbortError", "Error"]) {
            const error = new Error("Storage/model failed"); error.name = name;
            const original = object[stage];
            object[stage] = async () => { throw error; };
            await assert.rejects(run(local), actual => actual === error);
            assert.equal(commands.length, 0);
            object[stage] = original;
        }
    }
    calls.length = 0;
    let finishSelection, finishLoad;
    model.selectProject = project => new Promise(resolve => {
        calls.push(["select", project]); finishSelection = resolve;
    });
    model.loadProject = () => new Promise(resolve => {
        calls.push(["load"]); finishLoad = resolve;
    });
    const pending = run(local);
    await Promise.resolve();
    await Promise.resolve();
    assert.deepEqual(calls, [["persist", handle], ["select", localProject]]);
    assert.equal(commands.length, 0);
    finishSelection();
    await Promise.resolve();
    assert.deepEqual(calls, [["persist", handle], ["select", localProject], ["load"]]);
    assert.equal(commands.length, 0);
    finishLoad();
    await pending;
    assert.deepEqual(commands.pop(), {name: "ProjectLoaded"});
    calls.length = 0;
    for (const synchronous of [true, false]) {
        const error = new DOMException("Picker aborted", "AbortError");
        window.showDirectoryPicker = synchronous ? () => { throw error; } : () => Promise.reject(error);
        await run(local);
        assert.deepEqual(commands.pop(), {name: "ProjectPickerAborted", error});
    }
    assert.equal(calls.length, 0);
    console.log("PASS: local/remote routing, local persistence, loading order, aborts, and fatal errors");
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
subprocess.run(["node"], input="const CODE = " + json.dumps(code) + ";\n" + tests,
               text=True, cwd=repo, check=True)
