#!/usr/bin/env bash
# Render build script for ClipFetch backend — v6
#
# Changes from v5:
#   - Added Node.js install (required for YouTube signature/n-challenge solving)
#   - Added yt-dlp JS challenge solver script download
#
# Render → Service → Settings → Build Command:  bash build.sh
# Render → Service → Settings → Start Command:
#   PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/$(cat $HOME/.nvmrc 2>/dev/null || echo 'v20')/bin:$PATH" \
#   uvicorn app.main:app --host 0.0.0.0 --port $PORT

set -euo pipefail

LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

# ── 1. Node.js (required for YouTube signature + n-challenge solving) ─────────
# yt-dlp uses Node.js to solve YouTube's JS obfuscation challenges.
# Without it: "Signature solving failed" + "Only images are available"
echo "→ installing Node.js via nvm"
export NVM_DIR="$HOME/.nvm"

if [[ ! -s "$NVM_DIR/nvm.sh" ]]; then
  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi

# Load nvm
source "$NVM_DIR/nvm.sh"

# Install LTS Node if not present
if ! nvm ls 20 &>/dev/null; then
  nvm install 20
fi
nvm use 20
nvm alias default 20

# Symlink node/npm into LOCAL_BIN so they're on PATH at runtime
NODE_BIN="$(nvm which 20 | xargs dirname)"
ln -sf "$NODE_BIN/node" "$LOCAL_BIN/node"
ln -sf "$NODE_BIN/npm"  "$LOCAL_BIN/npm"

echo "→ node version: $(node --version)"
echo "→ npm version:  $(npm --version)"

# ── 2. Static ffmpeg ──────────────────────────────────────────────────────────
if [[ ! -x "$LOCAL_BIN/ffmpeg" ]]; then
  echo "→ downloading static ffmpeg"
  TMP="$(mktemp -d)"
  curl -fsSL -o "$TMP/ffmpeg.tar.xz" \
    "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
  tar -xJf "$TMP/ffmpeg.tar.xz" -C "$TMP" --strip-components=1
  mv "$TMP/ffmpeg"  "$LOCAL_BIN/ffmpeg"
  mv "$TMP/ffprobe" "$LOCAL_BIN/ffprobe"
  chmod +x "$LOCAL_BIN/ffmpeg" "$LOCAL_BIN/ffprobe"
  rm -rf "$TMP"
else
  echo "→ ffmpeg already present, skipping download"
fi

echo "→ ffmpeg version:"
"$LOCAL_BIN/ffmpeg" -version | head -n 1

# ── 3. Python deps ────────────────────────────────────────────────────────────
echo "→ upgrading pip"
pip install --upgrade pip

echo "→ installing python deps (no cache — ensures fresh yt-dlp)"
pip install --no-cache-dir --upgrade -r requirements.txt

# ── 4. Verify yt-dlp ─────────────────────────────────────────────────────────
echo "→ yt-dlp version:"
python -m yt_dlp --version

# ── 5. Verify Node.js is accessible to yt-dlp ────────────────────────────────
echo "→ verifying Node.js for yt-dlp JS solver"
python - <<'PYEOF'
import shutil, sys
node = shutil.which("node")
if node:
    import subprocess
    ver = subprocess.check_output([node, "--version"]).decode().strip()
    print(f"  node found at {node} ({ver}) — OK")
else:
    print("  WARNING: node not found on PATH — YouTube signature solving may fail")
PYEOF

# ── 6. Verify curl_cffi + ImpersonateTarget ───────────────────────────────────
echo "→ verifying curl_cffi and ImpersonateTarget"
python - <<'PYEOF'
import sys

try:
    import curl_cffi
    print(f"  curl_cffi {curl_cffi.__version__} — OK")
except ImportError:
    print("  ERROR: curl_cffi not importable — TikTok/Facebook will fail")
    sys.exit(1)

try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
    t = ImpersonateTarget.from_str("chrome")
    print(f"  ImpersonateTarget.from_str('chrome') = {t!r} — OK")
except Exception as exc:
    print(f"  ERROR: ImpersonateTarget setup failed: {exc}")
    sys.exit(1)
PYEOF

# ── 7. Smoke-test app import ──────────────────────────────────────────────────
echo "→ smoke-testing app import"
python -c "
from app.services.extractor import extract_metadata, FFMPEG_AVAILABLE, IMPERSONATE_AVAILABLE
import shutil
node_ok = bool(shutil.which('node'))
print(f'  ffmpeg={FFMPEG_AVAILABLE} impersonate={IMPERSONATE_AVAILABLE} node={node_ok}')
"

echo ""
echo "✓ build complete"