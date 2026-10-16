#!/usr/bin/env python3
"""Exercise directory-handle pool concurrency from the actual LP5 article."""
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
article = subprocess.check_output(
    ["./lp5", "lp5", "show-article", "30.lp5"], cwd=repo)
source = ET.fromstring(article).find(".//section[@data-lp5-kind='code']/code").text
with tempfile.TemporaryDirectory() as temporary:
    source_file = Path(temporary) / "directory_handles.js"
    source_file.write_text(source)
    subprocess.run(["node", "test/directory_handles.js", str(source_file)], cwd=repo, check=True)
