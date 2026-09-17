# PROBE.md — 环境探针（只读，1 分钟内跑完）

> **这是一次能力验证，不是真任务。**
> **严禁**执行 CLAUDE.md 里的任何实际步骤：
> 不要下载视频、不要跑 setup.sh、不要装包、不要跑转写或 OCR。
> 只做下面 8 条检查，然后把结果如实汇报。

## 请逐条执行并回答

**1. 仓库内容读到了吗**
```bash
pwd && ls -la
```
回答：目录里是否同时存在 `CLAUDE.md`、`setup.sh`、`fetch_video.sh`、`scripts/` 这四项？

**2. 能不能读 CLAUDE.md 的内容**
```bash
head -20 CLAUDE.md
```
回答：把输出原样贴出来。

**3. 算力对不对**
```bash
nproc && free -g | head -2
```
回答：CPU 几核？内存几 GB？（预期 4 核 / 8 GB）

**4. 是不是 root（关键）**
```bash
id -u
```
回答：输出 `0` 表示 root —— setup.sh 要写 `/opt/venv` 和 `/etc/profile.d`，非 root 会失败。
若不是 0，请明确说"非 root，setup.sh 会失败"。

**5. 基础工具在不在**
```bash
which ffmpeg python3 git curl; echo "---"; python3 -V
```
回答：哪些有、哪些没有、Python 版本。

**6. 能不能访问 GitHub API**
```bash
curl -sS -o /dev/null -w "http=%{http_code}\n" \
  https://api.github.com/repos/hammahrona-hue/-/releases/tags/v1
```
回答：http 码（200 = 通）。

**7. 视频附件能不能拿到、模型能不能下（两条都是关键）**
```bash
curl -sSIL https://github.com/hammahrona-hue/-/releases/download/v1/psychology-12.mov \
  | grep -i -E "^HTTP|^content-length"
curl -sS -o /dev/null -w "hf-mirror http=%{http_code}\n" \
  https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/tokens.txt
```
回答：content-length 是不是 **552772816**？hf-mirror 是不是 200？

**8. 能不能写回仓库（关键）**
```bash
echo "probe $(date -u +%FT%TZ)" > probe.txt
git add probe.txt && git commit -m "probe: 环境验证" && git push
echo "PUSH_EXIT=$?"
```
回答：push 成功还是失败？失败的话把报错原文贴出来。

---

## 最后用三句话总结（必须回答）

1. **我能读 GitHub 仓库内容吗？**（能 / 不能）
2. **我能在沙箱里执行 bash 命令吗？**（能 / 不能）
3. **我能 commit 并 push 回仓库吗？**（能 / 不能 / 报错是什么）

不要编造结果。任何一条失败，就如实说失败并贴出原始报错。
