# -*- coding: utf-8 -*-
"""心理学1 覆盖度审计 v3：用字符 n-gram 重合度做页级覆盖度量。"""
import os, re, json

BASE = r"C:\Users\Jason\WorkBuddy\2026-09-15-05-03-21\psych1"
manual = open(os.path.join(BASE, "out", "心理学1_精讲全解.html"), encoding="utf-8").read()
app = open(os.path.join(BASE, "out", "心理学1_闯关记忆手册.html"), encoding="utf-8").read()
slides_raw = open(os.path.join(BASE, "work", "slides_unique.txt"), encoding="utf-8").read()
ts_raw = open(os.path.join(BASE, "work", "transcript_sensevoice.txt"), encoding="utf-8").read()

NOISE = re.compile(r"[A-Za-z0-9_]+|G超|超格|B\d+(?![年月])|3\d{6,}|eg|eq|口|一|·|\.|\||\?|？|（|）|\(|\)")


def clean(s):
    s = NOISE.sub("", s)
    s = re.sub(r"[\s\u3000，。、；：！？,.;:!?\"'“”‘’\-—…《》【】\[\]（）()<>/\\]+", "", s)
    return s


def grams(s, n=3):
    s = clean(s)
    return set(s[i:i+n] for i in range(len(s) - n + 1)) if len(s) >= n else set()


def cover(src_text, target_text, n=3):
    g = grams(src_text, n)
    if not g:
        return 1.0, 0, 0
    t = grams(target_text, n)
    hit = len(g & t)
    return hit / len(g), hit, len(g)


print("=" * 72)
print("心理学1 · 页级覆盖度（3-gram 重合率）")
print("=" * 72)

blocks = re.split(r"\n===\s*S(\d+)\s*\[(\d+):(\d+)\]\s*===\n", slides_raw)
pages = []
for i in range(1, len(blocks), 4):
    pages.append((int(blocks[i]), f"{blocks[i+1]}:{blocks[i+2]}", blocks[i+3].strip()))

rows = []
for num, t, body in pages:
    ca, _, _ = cover(body, app)
    cm, _, _ = cover(body, manual)
    rows.append((num, t, ca, cm, body))

rows_sorted = sorted(rows, key=lambda r: r[2])
avg_a = sum(r[2] for r in rows) / len(rows)
avg_m = sum(r[3] for r in rows) / len(rows)
print(f"页数 {len(rows)}  平均重合率： 记忆手册 {avg_a:.1%}   精讲全解 {avg_m:.1%}")
print()
print("--- 记忆手册 覆盖最低的 12 页（可能是真缺口）---")
for num, t, ca, cm, body in rows_sorted[:12]:
    first = [l.strip() for l in body.split("\n") if l.strip()][:2]
    print(f"  S{num:03d} [{t}] 覆盖 {ca:.0%}  |  {' / '.join(first)[:64]}")

print()
print("--- 会话导学部分（前 20 分钟）单独看 ---")
early = [r for r in rows if int(r[1].split(":")[0]) < 21]
if early:
    e = sum(r[2] for r in early) / len(early)
    print(f"  导学段落共 {len(early)} 页，记忆手册平均覆盖 {e:.0%}")
    for num, t, ca, cm, body in sorted(early, key=lambda r: r[2])[:6]:
        first = [l.strip() for l in body.split("\n") if l.strip()][:2]
        print(f"    S{num:03d} [{t}] {ca:.0%}  {' / '.join(first)[:60]}")

# 讲解稿覆盖
print()
print("--- 文字稿分段覆盖（每 5 分钟为一段）---")
segs = {}
for line in ts_raw.split("\n"):
    m = re.match(r"\[(\d+):(\d+)\]\s*(.*)", line)
    if not m:
        continue
    mins = int(m.group(1))
    segs.setdefault(mins // 5 * 5, []).append(m.group(3))
low = []
for k in sorted(segs):
    txt = " ".join(segs[k])
    ca, _, _ = cover(txt, app)
    low.append((ca, k))
for ca, k in sorted(low)[:8]:
    print(f"  {k:>3}-{k+5:>3} 分钟   记忆手册覆盖 {ca:.0%}")
print(f"  —— 全程平均 {sum(c for c,_ in low)/len(low):.1%}")
