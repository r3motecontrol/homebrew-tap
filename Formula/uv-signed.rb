class UvSigned < Formula
  desc "Developer ID signed upstream build of the uv Python package manager"
  homepage "https://docs.astral.sh/uv/"
  url "https://github.com/astral-sh/uv/releases/download/0.12.18/uv-aarch64-apple-darwin.tar.gz"
  sha256 "cf40e0c6a202190ccd9e0406dcfdd5b2d6668a9a5c779b17948963df32aafe5b"
  license any_of: ["Apache-2.0", "MIT"]

  livecheck do
    url :stable
    strategy :github_latest
  end

  # Astral signs only the macOS artifacts. The top-level URL is the Apple
  # Silicon build, and it also keeps the spec valid on Linux, which
  # `brew readall` simulates for any formula with `on_system` blocks.
  depends_on :macos

  # `url` and `sha256` are only allowed in an arch block at this depth.
  on_macos do
    on_intel do
      url "https://github.com/astral-sh/uv/releases/download/0.12.18/uv-x86_64-apple-darwin.tar.gz"
      sha256 "2e4108f5395397c8bc5d43bf83d3bdbb2d0e92b90d0efa607756be704905fa33"
    end
  end

  # This formula ships the same two executables as homebrew-core's `uv`, so
  # only one of the two can own the symlinks in the Homebrew prefix.
  conflicts_with "uv", because: "both install `uv` and `uvx`"

  def install
    bin.install "uv", "uvx"
  end

  test do
    assert_match "uv #{version}", shell_output("#{bin}/uv --version")

    # The whole point of this formula: the executables Homebrew links must
    # still carry Astral's Developer ID signature, not an ad-hoc one.
    signature = shell_output("codesign -dv --verbose=2 #{bin}/uv 2>&1")
    assert_match "TeamIdentifier=2DC432GLL2", signature
    refute_match "adhoc", signature
  end
end
