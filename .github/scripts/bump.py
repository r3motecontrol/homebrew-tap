#!/usr/bin/env python3
"""Update Formula/uv-signed.rb to the latest upstream uv release.

Homebrew's own `brew bump` cannot be used here. It rewrites a formula through
`Utils::AST#replace_stable_stanza_value`, which resolves a stanza with a flat
`select` over the formula's top-level children (Homebrew/brew
`utils/ast.rb:331`). This formula keeps its `url` and `sha256` inside
`on_macos`/`on_arm`/`on_intel` blocks so it can serve both architectures, so
the lookup finds nothing at the top level and fails with "Error: Could not
find 'url' stanza!". Hence this script.

It prints the new version to stdout if it rewrote the formula and prints
nothing if the formula was already current, so a workflow can branch on
whether the output is empty. Safe to run by hand.
"""

import json
import pathlib
import re
import sys
import urllib.request

REPO = "astral-sh/uv"
ARCHES = ("aarch64", "x86_64")
FORMULA = pathlib.Path(__file__).resolve().parents[2] / "Formula" / "uv-signed.rb"

# Upstream tags are plain dotted numbers. Anything else is either a
# prerelease naming scheme we have not seen or a sign that something
# upstream changed, and we would rather fail than substitute it into a URL.
VERSION_RE = re.compile(r"\A\d+(?:\.\d+){1,3}\Z")
SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "homebrew-tap-bump"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def latest_version() -> str:
    release = json.loads(fetch(f"https://api.github.com/repos/{REPO}/releases/latest"))
    version = release["tag_name"].lstrip("v")
    if not VERSION_RE.match(version):
        sys.exit(f"upstream tag {release['tag_name']!r} is not a plain version, refusing to use it")
    return version


def published_checksum(version: str, arch: str) -> str:
    """Read the .sha256 sidecar Astral publishes next to each release asset.

    Trusting the sidecar rather than hashing the tarball ourselves keeps the
    formula's checksum identical to the one upstream vouches for.
    """
    url = (
        f"https://github.com/{REPO}/releases/download/{version}/"
        f"uv-{arch}-apple-darwin.tar.gz.sha256"
    )
    checksum = fetch(url).decode().split()[0]
    if not SHA256_RE.match(checksum):
        sys.exit(f"sidecar for {arch} did not contain a sha256: {checksum!r}")
    return checksum


def current_version(formula: str) -> str:
    match = re.search(r"/releases/download/([^/]+)/uv-aarch64-apple-darwin\.tar\.gz", formula)
    if not match:
        sys.exit("could not find the aarch64 download URL in the formula")
    return match.group(1)


def rewrite(formula: str, arch: str, version: str, checksum: str) -> str:
    """Replace the version and checksum for one architecture.

    The pattern spans the `url` and `sha256` lines together and is anchored on
    the architecture in the filename, so the two blocks cannot be confused for
    each other and a formatting change fails loudly instead of silently
    matching the wrong one.
    """
    pattern = re.compile(
        r'(url "https://github\.com/astral-sh/uv/releases/download/)[^/]+'
        rf'(/uv-{re.escape(arch)}-apple-darwin\.tar\.gz"\n\s*sha256 ")[0-9a-f]{{64}}(")'
    )
    updated, count = pattern.subn(rf"\g<1>{version}\g<2>{checksum}\g<3>", formula)
    if count != 1:
        sys.exit(f"expected exactly one {arch} url/sha256 pair in the formula, found {count}")
    return updated


def main() -> None:
    formula = FORMULA.read_text()
    version = latest_version()

    if current_version(formula) == version:
        return

    for arch in ARCHES:
        formula = rewrite(formula, arch, version, published_checksum(version, arch))

    FORMULA.write_text(formula)
    print(version)


if __name__ == "__main__":
    main()
