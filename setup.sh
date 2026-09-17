#!/usr/bin/env bash
# Hoplite 沙箱（Debian/Ubuntu, 4 vCPU, 8 GiB）一键装环境。
# 只需跑一次。跑完: source /etc/profile.d/pipeline.sh
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
MODELS_DIR="${MODELS_DIR:-/opt/models/sv}"

echo "===== [1/4] ffmpeg ====="
if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq ffmpeg
  else
    # 非 Debian 系兜底：下载静态构建
    mkdir -p /opt/ffmpeg
    curl -sL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
      | tar -xJ -C /opt/ffmpeg --strip-components=1
    ln -sf /opt/ffmpeg/ffmpeg /usr/local/bin/ffmpeg
  fi
fi
ffmpeg -version | head -1

echo "===== [2/4] Python venv ====="
python3 -m venv /opt/venv
/opt/venv/bin/pip install -q --upgrade pip
/opt/venv/bin/pip install -q -r "$(dirname "$0")/requirements.txt"

echo "===== [3/4] SenseVoice 模型 (228 MB) ====="
mkdir -p "$MODELS_DIR"
B="https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main"
[ -f "$MODELS_DIR/model.int8.onnx" ] || curl -sL -o "$MODELS_DIR/model.int8.onnx" "$B/model.int8.onnx"
[ -f "$MODELS_DIR/tokens.txt" ]      || curl -sL -o "$MODELS_DIR/tokens.txt"      "$B/tokens.txt"
ls -lh "$MODELS_DIR"

echo "===== [4/4] 环境变量 ====="
cat > /etc/profile.d/pipeline.sh <<EOF
export FFMPEG_BIN="$(command -v ffmpeg)"
export PY_ASR="/opt/venv/bin/python"
export PY_OCR="/opt/venv/bin/python"
export SENSEVOICE_DIR="$MODELS_DIR"
EOF
# shellcheck disable=SC1091
source /etc/profile.d/pipeline.sh

echo
echo "OK. 下一步:"
echo "  source /etc/profile.d/pipeline.sh"
echo "  bash fetch_video.sh"
