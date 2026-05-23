#!/usr/bin/env bash
set -euo pipefail

LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

echo "→ installing Node.js via nvm"
export NVM_DIR="$HOME/.nvm"
if [[ ! -s "$NVM_DIR/nvm.sh" ]]; then
  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi
source "$NVM_DIR/nvm.sh"
if ! nvm ls 20 &>/dev/null; then
  nvm install 20
fi
nvm use 20
nvm alias default 20
NODE_BIN="$(nvm which 20 | xargs dirname)"
ln -sf "$NODE_BIN/node" "$LOCAL_BIN/node"
ln -sf "$NODE_BIN/npm"  "$LOCAL_BIN/npm"
echo "→ node version: $(node --version)"

if [[ ! -x "$LOCAL_BIN/ffmpeg" ]]; then
  echo "→ downloading static ffmpeg"
  TMP="$(mktemp -d)"
  curl -fsSL -o "$TMP/ffmpeg.tar.xz" "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
  tar -xJf "$TMP/ffmpeg.tar.xz" -C "$TMP" --strip-components=1
  mv "$TMP/ffmpeg"  "$LOCAL_BIN/ffmpeg"
  mv "$TMP/ffprobe" "$LOCAL_BIN/ffprobe"
  chmod +x "$LOCAL_BIN/ffmpeg" "$LOCAL_BIN/ffprobe"
  rm -rf "$TMP"
else
  echo "→ ffmpeg already present"
fi
echo "→ ffmpeg version: $($LOCAL_BIN/ffmpeg -version | head -1)"

pip install --upgrade pip
pip install --no-cache-dir --upgrade -r requirements.txt
echo "→ yt-dlp: $(python -m yt_dlp --version)"

python - <<'PYEOF'
import shutil, sys
node = shutil.which("node")
print(f"  node={'OK at '+node if node else 'NOT FOUND'}")
try:
    import curl_cffi
    from yt_dlp.networking.impersonate import ImpersonateTarget
    t = ImpersonateTarget.from_str("chrome")
    print(f"  curl_cffi={curl_cffi.__version__} impersonate=OK")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)
from app.services.extractor import FFMPEG_AVAILABLE, IMPERSONATE_AVAILABLE
node_ok = bool(shutil.which('node'))
print(f"  ffmpeg={FFMPEG_AVAILABLE} impersonate={IMPERSONATE_AVAILABLE} node={node_ok}")
PYEOF

echo "✓ build complete"
