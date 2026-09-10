# homebrew-tap

Installs the signed upstream `uv` release instead of building it from source.

## Why

Astral signs and notarizes the macOS release artifacts as of [uv 0.12.12](https://github.com/astral-sh/uv/releases/tag/0.12.12), closing [astral-sh/uv#14870](https://github.com/astral-sh/uv/issues/14870). Homebrew does not benefit, because homebrew-core compiles uv from source with `cargo install`. This formula installs the official release tarball unmodified instead.

| | signature | `spctl` | [Santa](https://github.com/northpolesec/santa) |
|---|---|---|---|
| `brew install uv` | `adhoc, linker-signed`, no Team ID | `rejected` | `Allowed (Regex)`, prefix path rule |
| `brew install r3motecontrol/tap/uv-signed` | `Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)` | `accepted, source=Notarized Developer ID` | `Allowed (TeamID)`, publisher rule |

The installed executable is byte identical to the published one. Homebrew re-signs only the Mach-O files it rewrites, and `uv` has nothing to rewrite: every load command points at `/usr/lib` or a system framework, and it declares no `LC_RPATH`.

## Install

```sh
brew tap r3motecontrol/tap
brew trust r3motecontrol/tap   # Homebrew will not load formulae from an untrusted third-party tap
brew uninstall uv              # conflicts: both provide uv and uvx
brew install r3motecontrol/tap/uv-signed
```

Verify:

```sh
codesign -dv --verbose=2 "$(brew --prefix)/bin/uv"
spctl -a -vvv -t install "$(brew --prefix)/bin/uv"
```

## Maintenance

`.github/workflows/bump.yml` checks daily and opens a pull request when upstream is ahead. There is no build step, so no macOS runner is needed for a bump; checksums come from the `.sha256` sidecars Astral publishes.

`brew bump` is not used. It resolves stanzas with a flat search over a formula's top-level children, so it never sees the `on_intel` override and silently updates Apple Silicon only, leaving Intel pinned to the old version. `.github/scripts/bump.py` rewrites both.

`.github/workflows/tests.yml` audits the formula on Linux and asserts the Developer ID signature on a macOS runner.

## Caveat

A personal tap, not published or endorsed by Astral or Homebrew. It redistributes nothing: `brew` downloads the release asset from GitHub and checks it against the checksum Astral published.
