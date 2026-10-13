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
const run = new Function("window", "controller", CODE + "; return asyncSelectProject;")(window, controller);

(async () => {
    for (const synchronous of [true, false]) {
        const error = new DOMException("Picker access is forbidden", "SecurityError");
        window.showDirectoryPicker = synchronous
            ? () => { throw error; }
            : () => Promise.reject(error);
        await assert.rejects(run(), actual => actual === error);
        assert.equal(commands.length, 0, "Fatal error must not restore the dialog handler");
    }

    const handle = { name: "example.lp5" };
    window.showDirectoryPicker = async () => handle;
    await run();
    assert.deepEqual(commands.pop(), { name: "ProjectDirectoryPicked", directoryHandle: handle });

    for (const [errorName, commandName] of [
        ["AbortError", "ProjectPickerAborted"],
        ["NotFoundError", "ProjectPickerFailed"]
    ]) {
        const error = new DOMException("Picker failed", errorName);
        window.showDirectoryPicker = async () => { throw error; };
        await run();
        assert.deepEqual(commands.pop(), { name: commandName, error });
    }
    assert.equal(commands.length, 0);
    console.log("PASS: picker success, abort, failure, and synchronous/asynchronous SecurityError");
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
subprocess.run(["node"], input="const CODE = " + json.dumps(code) + ";\n" + tests,
               text=True, cwd=repo, check=True)
