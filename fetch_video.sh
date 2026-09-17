#!/usr/bin/env bash
# 从本仓库的 Release 附件下载视频。
# 可用环境变量覆盖: OWNER REPO TAG ASSET DEST
set -euo pipefail

OWNER="${OWNER:-hammahrona-hue}"
REPO="${REPO:--}"
TAG="${TAG:-v1}"
ASSET="${ASSET:-}"          # 留空则自动取该 release 的第一个附件
DEST="${DEST:-/work/video}"

mkdir -p "$DEST"

if [ -z "$ASSET" ]; then
  ASSET="$(curl -sSL "https://api.github.com/repos/${OWNER}/${REPO}/releases/tags/${TAG}" \
            | grep -m1 '"name"' | sed -E 's/.*"name": *"([^"]+)".*/\1/')"
fi
[ -n "$ASSET" ] || { echo "拿不到附件名，请显式设置 ASSET=xxx.mov"; exit 1; }

URL="https://github.com/${OWNER}/${REPO}/releases/download/${TAG}/${ASSET}"
echo "downloading: $URL"
curl -fL --retry 5 --retry-delay 3 -C - -o "$DEST/$ASSET" "$URL"

echo "$DEST/$ASSET" > "$DEST/VIDEO_PATH"
ls -lh "$DEST/$ASSET"
echo "VIDEO_PATH=$(cat "$DEST/VIDEO_PATH")"
