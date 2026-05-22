#!/usr/bin/env bash
# Render build script for ClipFetch backend — v5
#
# What this does:
#   1. Downloads a static ffmpeg binary (Render's Python runtime has none).
#   2. Installs Python deps without pip cache so yt-dlp is always fresh.
#   3. Verifies curl_cffi is importable (required for TikTok/Facebook TLS).
#   4. Verifies ImpersonateTarget.from_str works — catches BUG 1 at build time.
#
# Render → Service → Settings → Build Command:
#       bash build.sh
#
# Render → Service → Settings → Start Command:
#       PATH="$HOME/.local/bin:$PATH" \
#         uvicorn app.main:app --host 0.0.0.0 --port $PORT

set -euo pipefail

FFMPEG_DIR="$HOME/.local/bin"
mkdir -p "$FFMPEG_DIR"

# ── 1. Static ffmpeg ──────────────────────────────────────────────────────────
if [[ ! -x "$FFMPEG_DIR/ffmpeg" ]]; then
  echo "→ downloading static ffmpeg"
  TMP="$(mktemp -d)"
  curl -fsSL -o "$TMP/ffmpeg.tar.xz" \
    "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
  tar -xJf "$TMP/ffmpeg.tar.xz" -C "$TMP" --strip-components=1
  mv "$TMP/ffmpeg"  "$FFMPEG_DIR/ffmpeg"
  mv "$TMP/ffprobe" "$FFMPEG_DIR/ffprobe"
  chmod +x "$FFMPEG_DIR/ffmpeg" "$FFMPEG_DIR/ffprobe"
  rm -rf "$TMP"
else
  echo "→ ffmpeg already present, skipping download"
fi

echo "→ ffmpeg version:"
"$FFMPEG_DIR/ffmpeg" -version | head -n 1

# ── 2. Python deps ────────────────────────────────────────────────────────────
echo "→ upgrading pip"
pip install --upgrade pip

echo "→ installing python deps (no cache — ensures fresh yt-dlp)"
pip install --no-cache-dir --upgrade -r requirements.txt

# ── 3. Verify yt-dlp ─────────────────────────────────────────────────────────
echo "→ yt-dlp version:"
python -m yt_dlp --version

# ── 4. Verify curl_cffi + ImpersonateTarget (catches BUG 1 at build time) ────
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

# ── 5. Smoke-test that app imports without errors ─────────────────────────────
echo "→ smoke-testing app import"
python -c "from app.services.extractor import extract_metadata, FFMPEG_AVAILABLE, IMPERSONATE_AVAILABLE; print(f'  ffmpeg={FFMPEG_AVAILABLE} impersonate={IMPERSONATE_AVAILABLE}')"

echo ""
echo "✓ build complete"