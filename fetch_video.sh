#!/usr/bin/env bash
# 从本仓库的 Release 附件下载视频。
# 直接用 API 返回的 browser_download_url —— 中文文件名不用自己拼 URL / 不用 URL 编码。
# 可用环境变量覆盖: OWNER REPO TAG ASSET DEST
set -euo pipefail

OWNER="${OWNER:-hammahrona-hue}"
REPO="${REPO:--}"
TAG="${TAG:-v1}"
ASSET="${ASSET:-}"          # 留空则取该 release 的第一个附件
DEST="${DEST:-/work/video}"

mkdir -p "$DEST"

API="https://api.github.com/repos/${OWNER}/${REPO}/releases/tags/${TAG}"

if [ -z "$ASSET" ]; then
  # 取第一个附件的 browser_download_url（GitHub 已拼好并编码过）
  URL="$(curl -sSL "$API" | grep -m1 '"browser_download_url"' \
        | sed -E 's/.*"browser_download_url": *"([^"]+)".*/\1/')"
else
  # 指定附件名时，从 url 列表里按名字匹配
  URL="$(curl -sSL "$API" \
        | tr ',' '\n' \
        | grep -m1 -F "$ASSET" \
        | sed -n 's/.*"browser_download_url": *"\([^"]*\)".*/\1/p')"
fi

[ -n "$URL" ] || { echo "没找到附件。检查 OWNER/REPO/TAG/ASSET，或该 release 是否真的有附件。"; exit 1; }

NAME="${URL##*/}"
echo "downloading: $NAME"
echo "        from: $URL"
curl -fL --retry 5 --retry-delay 3 -C - -o "$DEST/$NAME" "$URL"

echo "$DEST/$NAME" > "$DEST/VIDEO_PATH"
ls -lh "$DEST/$NAME"
echo
echo "VIDEO_PATH=$(cat "$DEST/VIDEO_PATH")"
