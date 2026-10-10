#!/usr/bin/env python3
"""Check tangle source-map output and fragment attribution."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


BASE64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
PROJECT_DIR = Path(__file__).resolve().parents[1]


def decode_vlq(segment):
    values = []
    value = shift = 0
    for character in segment:
        digit = BASE64.index(character)
        value |= (digit & 31) << shift
        if digit & 32:
            shift += 5
            continue
        values.append(-(value >> 1) if value & 1 else value >> 1)
        value = shift = 0
    return values


def mapped_source_by_line(source_map):
    source_index = original_line = original_column = 0
    result = []
    for encoded_line in source_map["mappings"].split(";"):
        source_at_column_zero = None
        for encoded_segment in filter(None, encoded_line.split(",")):
            fields = decode_vlq(encoded_segment)
            if len(fields) == 1:
                source_at_column_zero = None
            else:
                source_index += fields[1]
                original_line += fields[2]
                original_column += fields[3]
                if fields[0] == 0:
                    source_at_column_zero = source_map["sources"][source_index]
        result.append(source_at_column_zero)
    return result


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())

    with tempfile.TemporaryDirectory(prefix="lp5-source-map-") as temporary:
        working = Path(temporary)
        source_dir = working / "app.lp5"
        source_dir.mkdir()
        for stylesheet in ("tangle.xsl", "weave.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)
        root = source_dir / "app.lp5"
        child = source_dir / "child.lp5"
        root.write_text(
            """<template>
  <section data-lp5-kind="code"><name></name><code><![CDATA[alpha();
beta();
]]><lp5- ref="shared"/><![CDATA[
omega();
]]></code></section>
  <children><li id="child.lp5"/></children>
</template>
""", encoding="utf-8")
        child.write_text(
            """<template>
  <section data-lp5-kind="code"><name>shared</name><code><![CDATA[gamma();
delta();
]]></code></section>
</template>
""", encoding="utf-8")

        tangled = subprocess.run([executable, "app", "tangle"], cwd=working,
                                 capture_output=True, text=True)
        assert tangled.returncode == 0, tangled.stderr
        output = source_dir / "app.out"
        map_file = source_dir / "app.map"
        generated = output.read_text(encoding="utf-8").splitlines()
        source_map = json.loads(map_file.read_text(encoding="utf-8"))
        assert source_map["version"] == 3
        assert source_map["file"] == "app.lp5/app.out"
        source_lines = mapped_source_by_line(source_map)
        expected = {
            "alpha();": "app.lp5",
            "beta();": "app.lp5",
            "gamma();": "child.lp5",
            "delta();": "child.lp5",
            "omega();": "app.lp5",
        }
        for line_number, text in enumerate(generated, start=1):
            if text in expected:
                mapped_source = source_lines[line_number - 1]
                assert Path(mapped_source).name == expected[text], (line_number, text, mapped_source)

        extra = subprocess.run([executable, "app", "tangle", "custom.out"],
                               cwd=working, capture_output=True, text=True)
        assert extra.returncode == 1
        assert "Usage: lp5 <project-name> tangle" in extra.stderr
        assert not (working / "custom.out").exists()

    print("fixed source-map path and fragment-attribution test passed")


if __name__ == "__main__":
    main()
