#!/usr/bin/env python3
"""Exercise article replacement, validation failures, and deferred weave refresh."""

import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/lp5")
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="lp5-replace-article-") as temporary:
        working = Path(temporary)
        source = working / "project.lp5"
        source.mkdir()
        for stylesheet in ("replace-article.xsl", "check.xsl", "tangle.xsl",
                           "weave.xsl", "show-article.xsl"):
            shutil.copyfile(PROJECT_DIR / stylesheet, working / stylesheet)

        root = source / "lp5.lp5"
        target = source / "12.lp5"
        root.write_bytes(b"<broken")
        target.write_bytes(b"<also-broken")
        (source / "13.lp5").write_bytes(b"<template><heading>Other article</heading></template>")
        collision = working / "12.lp5"
        collision.write_bytes(b"working-directory collision")
        proposal = working / "replacement.xml"
        replacement = '''<?xml version="1.0" encoding="UTF-8"?>
<!-- document comment --><?outside kept?>
<template xmlns:meta="urn:test" meta:label="kept">
    <children><li id="missing.lp5"/></children>
    <!-- article comment --><?inside kept?>
    <heading>New <em>article</em> 雪 &amp; more</heading>
    <keywords><li> Changed Keyword </li></keywords>
    <section data-lp5-kind="explanation"><p>Keep <code>x &lt; y</code>.</p></section>
    <section data-lp5-kind="code">
        <name>Example</name>
        <code><![CDATA[  if (a < b && c > d) {
    // literal ]]]]><![CDATA[> preserved
]]><lp5- ref="helper"/><![CDATA[
  }
]]></code>
    </section>
</template>
'''.replace("\n", "\r\n").encode("utf-8")
        proposal.write_bytes(replacement)
        cache = working / "weave.xml"

        def run(*arguments, environment=None, use_source=True, **options):
            prefix = ["-s", str(source)] if use_source else []
            return subprocess.run([executable, *prefix, "replace-article", *arguments],
                                  cwd=working, env=environment, capture_output=True,
                                  **options)

        def snapshot():
            return {
                path.name: (path.read_bytes(), path.stat().st_mtime_ns)
                for path in source.iterdir() if path.is_file()
            }

        def succeeds(filename, expected, *arguments, **options):
            before = snapshot()
            result = run(*arguments, **options)
            assert result.returncode == 0 and not result.stdout, result.stderr
            assert not result.stderr, result.stderr
            assert (source / filename).read_bytes() == expected
            after = snapshot()
            assert set(after) == set(before)
            assert {key: value for key, value in after.items() if key != filename} == {
                key: value for key, value in before.items() if key != filename
            }
            assert collision.read_bytes() == b"working-directory collision"

        def fails(*arguments, diagnostic=None, **options):
            before = snapshot()
            names = set(source.iterdir())
            cache_before = ((cache.read_bytes(), cache.stat().st_mtime_ns)
                            if cache.exists() else None)
            result = run(*arguments, **options)
            assert result.returncode == 1 and not result.stdout and result.stderr, result
            if diagnostic:
                assert diagnostic in result.stderr, result.stderr
            assert snapshot() == before
            assert set(source.iterdir()) == names
            assert ((cache.read_bytes(), cache.stat().st_mtime_ns)
                    if cache.exists() else None) == cache_before

        succeeds("12.lp5", replacement, "12.lp5", str(proposal))
        assert not cache.exists()
        assert proposal.read_bytes() == replacement

        cache.write_bytes(b"deliberately invalid and stale weave")
        os.utime(cache, ns=(1, 1))
        cache_before = (cache.read_bytes(), cache.stat().st_mtime_ns)
        succeeds("12.lp5", replacement, "12.lp5", str(target))
        assert (cache.read_bytes(), cache.stat().st_mtime_ns) == cache_before

        valid_root = b'<template><children><li id="12.lp5"/></children></template>\n'
        proposal.write_bytes(valid_root)
        succeeds("lp5.lp5", valid_root, "lp5.lp5", str(proposal))

        alternate = working / "alternate-index.xml"
        alternate.write_bytes(b"preserve selected index")
        alternate_before = (alternate.read_bytes(), alternate.stat().st_mtime_ns)
        environment = dict(os.environ, LP5Source=str(source))
        proposal.write_bytes(replacement)
        succeeds("12.lp5", replacement, "-w", str(alternate), "12.lp5", str(proposal),
                 environment=environment, use_source=False)
        assert (alternate.read_bytes(), alternate.stat().st_mtime_ns) == alternate_before
        assert (cache.read_bytes(), cache.stat().st_mtime_ns) == cache_before
        environment["LP5Source"] = str(working / "missing-project")
        succeeds("12.lp5", replacement, "12.lp5", str(proposal), environment=environment)

        utf16 = '<?xml version="1.0" encoding="UTF-16"?><template><heading>雪</heading></template>'
        proposal.write_bytes(utf16.encode("utf-16"))
        succeeds("12.lp5", proposal.read_bytes(), "12.lp5", str(proposal))
        empty = b"<template/>"
        proposal.write_bytes(empty)
        succeeds("12.lp5", empty, "12.lp5", str(proposal))

        option_named_input = working / "-o"
        option_named_input.write_bytes(replacement)
        succeeds("12.lp5", replacement, "--", "12.lp5", "-o")
        named = source / "named.lp5"
        named.write_bytes(empty)
        succeeds("named.lp5", replacement, "--", "named.lp5", "-o")

        for arguments in ((), ("12.lp5",), ("12.lp5", str(proposal), "extra"),
                          ("", str(proposal)), ("12", str(proposal)),
                          ("../12.lp5", str(proposal)), (str(target), str(proposal)),
                          (r"dir\12.lp5", str(proposal)), ("missing.lp5", str(proposal)),
                          ("12.lp5", str(working / "missing.xml")),
                          ("12.lp5", str(source)), ("12.lp5", str(proposal), "-m", "map"),
                          ("-o", str(target), "12.lp5", str(proposal)),
                          ("12.lp5", str(proposal), "-o", str(proposal))):
            fails(*arguments)

        directory_target = source / "directory.lp5"
        directory_target.mkdir()
        fails("directory.lp5", str(proposal), diagnostic=b"must be a regular file")
        directory_target.rmdir()

        if os.name == "posix":
            alias = source / "alias.lp5"
            alias.symlink_to(target.name)
            fails("alias.lp5", str(proposal), diagnostic=b"must be a regular file")
            alias.unlink()
            target.chmod(0o640)
            succeeds("12.lp5", empty, "12.lp5", str(proposal))
            assert stat.S_IMODE(target.stat().st_mode) == 0o640
            target.chmod(0o644)

        for invalid in (b"", b"<broken", b"<wrong/>", b"<template/><template/>",
                        b'<template xmlns="wrong"/>',
                        b"<template><script/></template>",
                        b"<template><heading/><heading/></template>",
                        b"<template><children/><children/></template>",
                        b'<template><children><li id="13"/></children></template>',
                        b'<template><section data-lp5-kind="other"/></template>',
                        b'<template><section data-lp5-kind="code"><code/></section></template>',
                        b'<template><section data-lp5-kind="code"><name/><code><b/></code></section></template>',
                        b"<template><keywords><li><b>bad</b></li></keywords></template>"):
            proposal.write_bytes(invalid)
            fails("12.lp5", str(proposal))

        if os.name == "posix":
            import resource

            def limit_file_size(limit):
                def apply():
                    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
                    resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
                return apply

            proposal.write_bytes(b"<template><heading>" + b"x" * 100 + b"</heading></template>")
            fails("12.lp5", str(proposal), preexec_fn=limit_file_size(32),
                  diagnostic=b"cannot finish replacement")
            proposal.write_bytes(b"<template><heading>" + b"x" * 100_000 + b"</heading></template>")
            fails("12.lp5", str(proposal), preexec_fn=limit_file_size(4096),
                  diagnostic=b"cannot finish replacement")

            if sys.platform.startswith("linux"):
                # Fault injection also works in root-only user namespaces,
                # where an unprivileged test UID may not exist.
                failure_source = working / "replacement-failure.c"
                failure_source.write_text(r"""
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

int open(const char *path, int flags, ...)
{
    const char *failure = getenv("LP5_REPLACE_TEST_FAILURE");
    int (*real_open)(const char *, int, ...) = dlsym(RTLD_NEXT, "open");
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list arguments;
        va_start(arguments, flags);
        mode = va_arg(arguments, mode_t);
        va_end(arguments);
    }
    if (failure && strcmp(failure, "create") == 0 &&
            (flags & (O_CREAT | O_EXCL)) == (O_CREAT | O_EXCL)) {
        errno = EACCES;
        return -1;
    }
    return real_open(path, flags, mode);
}

int rename(const char *old_path, const char *new_path)
{
    const char *failure = getenv("LP5_REPLACE_TEST_FAILURE");
    int (*real_rename)(const char *, const char *) = dlsym(RTLD_NEXT, "rename");
    if (failure && strcmp(failure, "rename") == 0) {
        errno = EACCES;
        return -1;
    }
    return real_rename(old_path, new_path);
}
""", encoding="utf-8")
                failure_library = working / "replacement-failure.so"
                subprocess.run(["gcc", "-std=c99", "-Wall", "-Wextra", "-shared",
                                "-fPIC", str(failure_source), "-ldl", "-o",
                                str(failure_library)], check=True, capture_output=True)
                proposal.write_bytes(empty)
                for failure, diagnostic in (
                        ("create", b"cannot create replacement"),
                        ("rename", b"cannot replace article")):
                    environment = dict(os.environ, LD_PRELOAD=str(failure_library),
                                       LP5_REPLACE_TEST_FAILURE=failure)
                    fails("12.lp5", str(proposal), environment=environment,
                          diagnostic=diagnostic)

        # A subsequent read regenerates the stale cache from the changed source.
        proposal.write_bytes(replacement)
        succeeds("12.lp5", replacement, "12.lp5", str(proposal))
        assert (cache.read_bytes(), cache.stat().st_mtime_ns) == cache_before
        result = subprocess.run([executable, "-s", str(source), "show-article", "12.lp5"],
                                cwd=working, capture_output=True)
        assert result.returncode == 0, result.stderr
        assert b"Changed Keyword" in cache.read_bytes()
        assert b"Changed Keyword" in result.stdout
        assert cache.stat().st_mtime_ns != cache_before[1]

    print("replace-article acceptance checks passed")


if __name__ == "__main__":
    main()
