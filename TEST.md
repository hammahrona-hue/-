# TEST.md — 读取能力测试（只读，5 分钟内跑完）

> **这是测试，不是干活。**
> **严禁**：跑 `setup.sh`、下载原视频、转写、OCR、装任何包。
> 只做读取和核对，然后如实汇报。**不要编造结果**，读不到就说读不到。

---

## A. 读仓库里的文本文件

先 `git clone` 或直接读工作区。对下面每个文件，贴出**前 200 个字符** + **总字节数**：

```bash
for f in out/transcript.txt out/slides_unique.txt out/ocr_all.jsonl \
         out/slides_index.md out/slides_index.json out/slides/manifest.md \
         CLAUDE.md BRIEF.md scripts/SKILL.md; do
  echo "===== $f  ($(wc -c < "$f") bytes) ====="
  head -c 200 "$f"; echo; echo
done
```

**特别确认这两个**（它们是 JSON，容易读坏）：
```bash
python3 -c "import json;[json.loads(l) for l in open('out/ocr_all.jsonl',encoding='utf-8') if l.strip()];print('ocr_all.jsonl 解析 OK')"
python3 -c "import json;d=json.load(open('out/slides_index.json',encoding='utf-8'));print('slides_index.json 解析 OK, 条数=',len(d))"
```

## B. 读 Release 上的四个大附件（只探测，不要全下载）

```bash
B=https://github.com/hammahrona-hue/-/releases/download/v1
for f in psychology-12.mov frames_all_9737.zip frames_unique_691.zip slides_102.zip; do
  curl -sIL "$B/$f" | grep -i -E "^HTTP|^content-length" | tail -2 | tr '\n' ' '
  echo "  <- $f"
done
```

**预期**：`psychology-12.mov` = 552772816、`frames_all_9737.zip` ≈ 728,600,000、
`frames_unique_691.zip` ≈ 75,700,000、`slides_102.zip` ≈ 10,500,000。

## C. ★ 真正下载 + 用视觉读图（最关键的一步）

```bash
curl -fL -o /tmp/slides.zip "$B/slides_102.zip"
python3 -m zipfile -e /tmp/slides.zip /tmp/slides/ 2>/dev/null || unzip -q /tmp/slides.zip -d /tmp/slides
ls /tmp/slides | wc -l      # 预期 103（102 张 jpg + manifest.md）
```

然后**真的打开这三张图看**，用你的视觉能力回答：

| 图片 | 要回答什么 |
|---|---|
| `/tmp/slides/S001.jpg` | ① 标题 ② 图上所有文字（尽量完整抄）③ 有没有手写批注 |
| `/tmp/slides/S005.jpg` | 同上 |
| `/tmp/slides/S050.jpg` | 同上 |

**这一节的目的是验证"你能不能看见图片里的字"**，不是验证下载成功。

---

## D. 最后用这张表汇报（必须逐行填）

| # | 内容 | 能否读取 | 证据 / 说明 |
|---|---|---|---|
| 1 | 仓库文本文件（9 个） | 能/不能 | 哪个读不了 |
| 2 | `ocr_all.jsonl` JSON 解析 | 能/不能 | 条数 |
| 3 | `slides_index.json` JSON 解析 | 能/不能 | 条数 |
| 4 | Release 四个附件可见 | 能/不能 | 各自大小 |
| 5 | 下载并解压 `slides_102.zip` | 能/不能 | 解出几个文件 |
| 6 | **看见图片里的文字** | 能/不能 | S001 抄出来的文字 |

最后用一句话总结：

> **我能读仓库文本吗？__ 我能下载 Release 附件吗？__ 我能看见幻灯片图片里的文字吗？__**
