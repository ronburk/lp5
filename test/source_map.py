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
        directory = Path(temporary)
        root = directory / "root.lp5"
        child = directory / "child.lp5"
        ordinary = directory / "ordinary.html"
        mapped = directory / "mapped.html"
        map_file = directory / "mapped.html.map"
        trailing_option_output = directory / "trailing-option.html"
        trailing_option_map = directory / "trailing-option.html.map"

        root.write_text(
            """<template>
  <section data-lp5-kind="code"><name></name><code><![CDATA[alpha();
beta();
]]><lp5- ref="shared"/><![CDATA[
omega();
]]></code></section>
  <children><li id="child.lp5"/></children>
</template>
""",
            encoding="utf-8",
        )
        child.write_text(
            """<template>
  <section data-lp5-kind="code"><name>shared</name><code><![CDATA[gamma();
delta();
]]></code></section>
</template>
""",
            encoding="utf-8",
        )

        subprocess.run(
            [executable, "-o", str(ordinary), "tangle", str(root)],
            cwd=PROJECT_DIR,
            check=True,
        )
        subprocess.run(
            [executable, "-m", str(map_file), "-o", str(mapped), "tangle", str(root)],
            cwd=PROJECT_DIR,
            check=True,
        )
        subprocess.run(
            [executable, "tangle", str(root), "-m", str(trailing_option_map),
             "-o", str(trailing_option_output)],
            cwd=PROJECT_DIR,
            check=True,
        )

        assert ordinary.read_bytes() == mapped.read_bytes()
        assert ordinary.read_bytes() == trailing_option_output.read_bytes()
        source_map = json.loads(map_file.read_text(encoding="utf-8"))
        json.loads(trailing_option_map.read_text(encoding="utf-8"))
        assert source_map["version"] == 3
        assert source_map["file"] == str(mapped)

        output_lines = mapped.read_text(encoding="utf-8").splitlines()
        source_lines = mapped_source_by_line(source_map)
        expected = {
            "alpha();": "root.lp5",
            "beta();": "root.lp5",
            "gamma();": "child.lp5",
            "delta();": "child.lp5",
            "omega();": "root.lp5",
        }
        for line_number, text in enumerate(output_lines, start=1):
            if text in expected:
                source = source_lines[line_number - 1]
                assert Path(source).name == expected[text], (line_number, text, source)

        missing_root = directory / "missing-root.lp5"
        missing_output = directory / "missing-output.html"
        missing_root.write_text(
            """<template>
  <section data-lp5-kind="code"><name></name><code><![CDATA[start();]]><lp5- ref="not-present"/></code></section>
  <children><li id="missing-child.lp5"/></children>
</template>
""",
            encoding="utf-8",
        )
        missing_article = subprocess.run(
            [executable, "-o", str(missing_output), "tangle", str(missing_root)],
            cwd=PROJECT_DIR,
            text=True,
            capture_output=True,
        )
        assert missing_article.returncode == 0, missing_article.stderr
        assert "MISSING-CHILD.LP5" in missing_output.read_text(encoding="utf-8")
        assert "I/O warning" not in missing_article.stderr
        assert "failed to load external entity" not in missing_article.stderr

        weave_file = directory / "weave.xml"
        weave_file.write_text('<lp5-weave version="1"/>', encoding="utf-8")
        invalid_input = subprocess.run(
            [executable, "tangle", str(weave_file), "-m", str(map_file)],
            cwd=PROJECT_DIR,
            text=True,
            capture_output=True,
        )
        assert invalid_input.returncode == 1
        assert (
            f"tangle input '{weave_file}' is not an LP5 root article: "
            "found <lp5-weave>; expected <template>. Use -o to name the generated output."
        ) in invalid_input.stderr
        assert "Usage: lp5 tangle [root-article]" in invalid_input.stderr
        assert "transformation failed" not in invalid_input.stderr

    print("source-map parity and fragment-attribution test passed")


if __name__ == "__main__":
    main()
