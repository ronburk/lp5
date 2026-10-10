#!/usr/bin/env python3
"""Check angle-bracket code bundles are tangled as additional outputs."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def run(executable, cwd, project, *args):
    return subprocess.run([executable, project, *args], cwd=cwd,
                          capture_output=True, text=True)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())

    with tempfile.TemporaryDirectory(prefix="lp5-multiple-outputs-") as temporary:
        working = Path(temporary)
        source = working / "app.lp5"
        source.mkdir()
        for stylesheet in ("weave.xsl", "tangle.xsl"):
            (working / stylesheet).symlink_to(PROJECT_DIR / stylesheet)
        (source / "app.lp5").write_text(
            """<template>
  <section data-lp5-kind="code"><name></name><code><![CDATA[default-start\n]]><lp5- ref="shared"/></code></section>
  <children><li id="1.lp5"/><li id="2.lp5"/><li id="3.lp5"/><li id="4.lp5"/></children>
</template>
""", encoding="utf-8")
        (source / "1.lp5").write_text(
            "<template><section data-lp5-kind=\"code\"><name>&lt;app.js&gt;</name>"
            "<code><![CDATA[app-start\n]]><lp5- ref=\"shared\"/>"
            "<![CDATA[app-end\n]]></code></section></template>\n", encoding="utf-8")
        (source / "2.lp5").write_text(
            "<template><section data-lp5-kind=\"code\"><name>&lt;page.html&gt;</name>"
            "<code><![CDATA[page-start\n]]><lp5- ref=\"&lt;app.js&gt;\"/>"
            "<![CDATA[page-end\n]]></code></section></template>\n", encoding="utf-8")
        (source / "3.lp5").write_text(
            "<template><section data-lp5-kind=\"code\"><name>&lt;app.js&gt;</name>"
            "<code><![CDATA[app-child\n]]></code></section></template>\n", encoding="utf-8")
        (source / "4.lp5").write_text(
            "<template><section data-lp5-kind=\"code\"><name>shared</name>"
            "<code><![CDATA[shared-code\n]]></code></section></template>\n", encoding="utf-8")

        result = run(executable, working, "app", "tangle")
        assert result.returncode == 0, result.stderr
        default_text = (source / "app.out").read_text(encoding="utf-8")
        assert default_text == "default-start\nshared-code\n\n", repr(default_text)
        assert (source / "app.js").read_text(encoding="utf-8") == \
            "app-start\nshared-code\napp-end\napp-child\n\n"
        assert (source / "page.html").read_text(encoding="utf-8") == \
            "page-start\napp-start\nshared-code\napp-end\napp-child\npage-end\n\n"
        assert json.loads((source / "app.map").read_text())['file'] == \
            "app.lp5/app.out"
        assert json.loads((source / "app.js.map").read_text())['file'] == \
            "app.lp5/app.js"
        assert json.loads((source / "page.html.map").read_text())['file'] == \
            "app.lp5/page.html"

        default_before = (source / "app.out").read_bytes()
        (source / "orphan.lp5").write_text(
            "<template><section data-lp5-kind=\"code\"><name>&lt;orphan.js&gt;</name>"
            "<code><![CDATA[orphan\n]]></code></section></template>\n",
            encoding="utf-8")
        orphan = run(executable, working, "app", "tangle")
        assert orphan.returncode != 0
        assert "no definition reachable from the root article" in orphan.stderr
        assert (source / "app.out").read_bytes() == default_before
        (source / "orphan.lp5").unlink()

        # A named output cannot overwrite the fixed unnamed output or escape
        # the project directory.
        page = source / "2.lp5"
        text = page.read_text(encoding="utf-8")
        page.write_text(text.replace("&lt;page.html&gt;", "&lt;app.out&gt;"),
                        encoding="utf-8")
        collision = run(executable, working, "app", "tangle")
        assert collision.returncode != 0
        assert "collision" in collision.stderr
        page.write_text(text.replace("&lt;page.html&gt;", "&lt;../escape&gt;"),
                        encoding="utf-8")
        unsafe = run(executable, working, "app", "tangle")
        assert unsafe.returncode != 0
        assert "invalid tangle output filename" in unsafe.stderr
        assert not (working / "escape").exists()

    print("multiple-output tangle checks passed")


if __name__ == "__main__":
    main()
