# -*- coding: utf-8 -*-
"""心理学1 深度审计：把幻灯片每条实质内容抽出，逐条核对两份交付物。"""
import os, re, json

B = r"C:\Users\Jason\WorkBuddy\2026-09-15-05-03-21\psych1"
manual_raw = open(os.path.join(B, "out", "心理学1_精讲全解.html"), encoding="utf-8").read()
app_raw = open(os.path.join(B, "out", "心理学1_闯关记忆手册.html"), encoding="utf-8").read()
slides_raw = open(os.path.join(B, "work", "slides_unique.txt"), encoding="utf-8").read()
ts_raw = open(os.path.join(B, "work", "transcript_sensevoice.txt"), encoding="utf-8").read()

def N(s):
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"[\s\u3000·．.、，,；;：:！!？?（）()\[\]【】「」《》<>/\\\"'“”‘’—\-…|]+", "", s)

manual, app, slides, ts = N(manual_raw), N(app_raw), N(slides_raw), N(ts_raw)

# 分页
blocks = re.split(r"===\s*S(\d+)\s*\[(\d+):(\d+)\]\s*===", slides_raw)
pages = []
for i in range(1, len(blocks), 4):
    pages.append([int(blocks[i]), f"{blocks[i+1]}:{blocks[i+2]}", blocks[i+3]])

GENERIC = re.compile(r"^(G超|超格|B\d+$|3\d{6,}|上课|课前回顾|学习进度条|今日进度|分值变化趋势|"
                     r"小红书|上岸|心理学专业硕士|考情数据化|授课风格|长年授课|"
                     r"eg\b|eq\b|口诀|【?考例|【?考情分析|记忆梳理|考点汇总|总结梳理|解题技巧|做题|"
                     r"拓展学习|理解|补充|思考|请|要求|注意|图|如下图|左侧|右侧)")

def keys_of(line):
    """从一行里抽出可用于比对的实词块（2-6 字的连续中文片段）。"""
    line = re.sub(r"[A-Za-z0-9_]+", "", line)
    parts = re.findall(r"[\u4e00-\u9fa5]{2,6}", line)
    stop = {"一个", "什么", "我们", "这个", "那个", "可以", "就是", "不是", "以及", "包括", "进行",
            "例如", "属于", "下面", "上面", "之后", "发生", "表现", "分为", "具有", "通过对",
            "叫做", "称为", "指的是", "也就是", "因为", "所以", "但是", "而且", "如果", "那么"}
    return [p for p in parts if p not in stop]

# ---------- 逐页逐行审计 ----------
rows = []
for num, t, body in pages:
    for line in body.split("\n"):
        s = line.strip()
        if len(N(s)) < 5:
            continue
        if GENERIC.match(s):
            continue
        ks = keys_of(s)
        if len(ks) < 2:
            continue
        in_app = sum(1 for k in ks if k in app) / len(ks)
        in_man = sum(1 for k in ks if k in manual) / len(ks)
        rows.append((num, t, s, in_app, in_man, len(ks)))

print("=" * 78)
print(f"幻灯片实质内容行共 {len(rows)} 条，逐条核对（按关键词命中率）")
print("=" * 78)

def bucket(v):
    return "高" if v >= 0.7 else ("中" if v >= 0.4 else "低")

cnt = {}
for num, t, s, a, m, n in rows:
    cnt[(bucket(a), bucket(m))] = cnt.get((bucket(a), bucket(m)), 0) + 1
print("\n命中率分布（记忆手册, 精讲全解）:")
for k in sorted(cnt, key=lambda x: -cnt[x]):
    print(f"   {k}: {cnt[k]} 条")

print("\n" + "-" * 78)
print("【A】两份交付物命中率都低的行（= 真缺口候选）")
print("-" * 78)
both_low = [(num, t, s, a, m, n) for num, t, s, a, m, n in rows if a < 0.4 and m < 0.4]
for num, t, s, a, m, n in both_low:
    print(f"  S{num:03d}[{t}] 手册{a:.0%} 全解{m:.0%} | {s[:72]}")

print("\n" + "-" * 78)
print("【B】仅「闯关记忆手册」命中率低的行（= 手册缺口）")
print("-" * 78)
app_low = [(num, t, s, a, m, n) for num, t, s, a, m, n in rows if a < 0.4 and m >= 0.4]
for num, t, s, a, m, n in app_low:
    print(f"  S{num:03d}[{t}] 手册{a:.0%} 全解{m:.0%} | {s[:72]}")

print("\n" + "-" * 78)
print("【C】仅「精讲全解」命中率低的行（= 全解缺口）")
print("-" * 78)
man_low = [(num, t, s, a, m, n) for num, t, s, a, m, n in rows if m < 0.4 and a >= 0.4]
for num, t, s, a, m, n in man_low:
    print(f"  S{num:03d}[{t}] 手册{a:.0%} 全解{m:.0%} | {s[:72]}")

json.dump([{"page": r[0], "t": r[1], "line": r[2], "app": r[3], "manual": r[4]}
           for r in rows], open(os.path.join(B, "audit_detail.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"\n明细已存 audit_detail.json")
