# homebrew-tap

A Homebrew tap that installs the **signed** upstream `uv` release instead of building it from source.

## Why

Astral began shipping Developer ID signed and notarized macOS binaries in [uv 0.12.12](https://github.com/astral-sh/uv/releases/tag/0.12.12), closing [astral-sh/uv#14870](https://github.com/astral-sh/uv/issues/14870). Homebrew does not benefit from that, because homebrew-core's `uv` formula compiles from a source tarball with `cargo install`. The resulting bottle is ad-hoc signed with no Team ID, so it is rejected by Gatekeeper and, on fleets running [Santa](https://github.com/northpolesec/santa) in lockdown, can only be permitted by a path rule over the Homebrew prefix rather than by publisher.

This tap installs the official release tarball verbatim, so the executables keep their signature.

| | signature | `spctl` | Santa decision |
|---|---|---|---|
| `brew install uv` (homebrew-core) | `adhoc, linker-signed`, `TeamIdentifier=not set` | `rejected` | `Allowed (Regex)`, prefix path rule |
| `brew install r3motecontrol/tap/uv-signed` | `Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)` | `accepted, source=Notarized Developer ID` | `Allowed (TeamID)`, publisher rule |

The installed executable is byte for byte the one Astral published. Same SHA-256 before and after Homebrew touches it:

```
53cf843c2eed12d1cafdaab7a1ba95e53496f7df280fc2be4fa8f3d7c32a1496  ./uv-aarch64-apple-darwin/uv
53cf843c2eed12d1cafdaab7a1ba95e53496f7df280fc2be4fa8f3d7c32a1496  /opt/homebrew/Cellar/uv-signed/0.12.12/bin/uv
```

That holds because Homebrew only re-signs Mach-O files it actually rewrites (`Keg#fix_dynamic_linkage` re-signs just the files it modified), and `uv` has nothing to rewrite: every load command points at `/usr/lib` or a system framework, and it declares no `LC_RPATH`.

## Install

```sh
brew tap r3motecontrol/tap
brew trust r3motecontrol/tap   # Homebrew 6 will not load formulae from an untrusted third-party tap
brew uninstall uv              # conflicts: both provide uv and uvx
brew install r3motecontrol/tap/uv-signed
```

Verify:

```sh
codesign -dv --verbose=2 "$(brew --prefix)/bin/uv"
spctl -a -vvv -t install "$(brew --prefix)/bin/uv"
```

## Why this is a tap and not a contribution to Homebrew

Neither official repository can take it:

- **homebrew-core** builds everything from source by policy, which is the reason its bottle is unsigned in the first place.
- **homebrew-cask** is not an alternative. Its rules state that "open-source command-line-only software normally belongs in homebrew/core as a formula built from source", that "a duplicate cask for the same software, release and channel is not eligible", and that "a rejection from homebrew/core does not by itself make the software eligible for homebrew/cask".

So a tap is the only route to a signed `uv` through Homebrew, and a vendor-published tap would be the natural home for it.

## Maintenance

There is no build step, so there is no bottle and no macOS runner required to keep this current. A release bump is a version string and two SHA-256 values, both of which Astral publishes as `.sha256` sidecars next to each release asset.

`.github/workflows/bump.yml` does this unattended on `ubuntu-latest`. It runs daily, and when upstream is ahead it rewrites the formula, pushes a branch and opens a pull request. `.github/workflows/tests.yml` audits the formula on Linux and, on a macOS runner, asserts that the installed binary really does carry the Developer ID signature.

### Why not `brew bump`

Homebrew ships its own autobump path, and `brew tap-new` scaffolds a workflow for it, but it cannot rewrite this formula. `brew bump-formula-pr` updates a checksum through `Utils::AST#replace_stable_stanza_value`, which resolves the stanza with a flat `select` over the formula's top-level children:

```ruby
# Homebrew/brew utils/ast.rb:331
def matching_stanzas(nodes, name, type: nil)
  nodes.select { |child| call_node_match?(child, name:, type:) }
end
```

There is no recursion into block bodies. Because this formula keeps `url` and `sha256` inside `on_arm` and `on_intel` so that one formula can serve both architectures, the lookup finds nothing at the top level and `stable_stanza` raises. Confirmed against this tap:

```
$ brew bump-formula-pr --dry-run --version=0.12.11 r3motecontrol/tap/uv-signed
Error: Could not find 'url' stanza!
```

Any binary tap serving more than one architecture hits the same wall.

`.github/scripts/bump.py` replaces it. It reads the latest tag from the GitHub API, rejects anything that is not a plain dotted version, then takes each architecture's checksum from the `.sha256` sidecar upstream publishes rather than recomputing it locally, and rewrites the two `url`/`sha256` pairs with a pattern anchored on the architecture in the filename so the blocks cannot be confused for each other. It prints the new version if it changed the formula and prints nothing if there was nothing to do.

### One wrinkle

The pull request that `bump.yml` opens will not start the `tests` workflow, because per GitHub's docs "events triggered by the `GITHUB_TOKEN` will not create a new workflow run". Two ways around it:

- Run `tests` manually against the bump branch, which is why that workflow accepts `workflow_dispatch`.
- Store a fine-grained personal access token with contents and pull request write on this repository as a `BUMP_TOKEN` secret and use it in place of `secrets.GITHUB_TOKEN` in `bump.yml`. GitHub's documented workaround is to "use a GitHub App installation access token or a personal access token instead of `GITHUB_TOKEN`".

## Caveats

This is a personal tap. It is not published, endorsed, or maintained by Astral or by Homebrew. It redistributes nothing: `brew` downloads the release asset straight from GitHub and checks it against the checksum Astral published.
