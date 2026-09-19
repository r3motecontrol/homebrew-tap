class UvSigned < Formula
  desc "Developer ID signed upstream build of the uv Python package manager"
  homepage "https://docs.astral.sh/uv/"
  url "https://github.com/astral-sh/uv/releases/download/0.12.17/uv-aarch64-apple-darwin.tar.gz"
  sha256 "85f00cbdc6dd3e97eba4c31b4d014375a9fdfe8f570023b84e5102fc3456896b"
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
      url "https://github.com/astral-sh/uv/releases/download/0.12.17/uv-x86_64-apple-darwin.tar.gz"
      sha256 "8dcf05a8c809bb3c471d2b614788ba27a6e41298fc8c31ac84b5f4339fd468e5"
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
