# lecture-video → 学习手册（Hoplite 沙箱作业仓库）

这个仓库**只放说明书和脚本，不放视频本体**。

- 视频本体挂在 **Release 附件**上（单文件上限 2 GB，不计入 Git LFS 配额，GitHub 不限带宽，
  且**不在 `git clone` 范围内** → 不会触发 Hoplite 每晚的 warm snapshot 重烘焙下载）。
- `scripts/` 是本机 `lecture-video-to-study-guide` skill 的**完整原样拷贝**（SKILL.md + 全部脚本，一个没删）。
- 真正干活的是 Hoplite 沙箱里的 Agent：**拉取视频 → 抽音频 → 转写 → 抽帧 → OCR → 出学习手册**，
  产物 commit 回本仓库。

## 给 Agent 的入口

先读 [`CLAUDE.md`](CLAUDE.md)，按里面的顺序执行。

## 目录

```
README.md          本文件
CLAUDE.md          Agent 作业指导书（覆盖 SKILL.md 里的 Windows 路径）
setup.sh           Linux 沙箱一键装环境（ffmpeg + Python 依赖 + SenseVoice 模型）
fetch_video.sh     从 Release 附件下载视频到 /work/video
requirements.txt   Python 依赖
scripts/           lecture-video-to-study-guide skill 全量拷贝
out/               （Agent 产出）transcript.txt / slides_unique.txt / ocr_all.jsonl / uniq_meta.json
```

## 为什么不用 Git LFS 放视频

Hoplite 的 warm snapshot **每次 base-branch push + 每晚**自动重烘焙（= 完整 clone 仓库）。
LFS 走账号级带宽额度（免费 10 GiB/月），1.4 GB 视频 × 每晚一次 × 30 天 ≈ 42 GiB/月，
不到一周就会把 LFS 打停；反过来若沙箱没装 git-lfs，clone 到的只是 100 字节的指针文件，等于白传。
所以：**视频必须走 Release 附件，绝不进 git 对象。**
