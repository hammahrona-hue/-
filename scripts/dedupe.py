# -*- coding: utf-8 -*-
"""抽帧去重：把 frames/ 按感知哈希分组，输出 uniq/ 代表帧 + uniq_meta.json。
用法: python dedupe.py <workdir> <interval> [every_n]
      every_n=0 只取每组代表帧（末帧+中间帧）；>0 再叠加定时采样以抓渐进手写批注
"""
import os, sys, json, time
import numpy as np
from PIL import Image

WORK = sys.argv[1]
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
EVERY = int(sys.argv[3]) if len(sys.argv) > 3 else 0
HASH_T = 6          # 汉明距离阈值


def ahash(path, size=16):
    g = Image.open(path).convert("L").resize((size, size), Image.LANCZOS)
    a = np.asarray(g, dtype=np.float32)
    return (a > a.mean()).astype(np.uint8)


def main():
    frames_dir = os.path.join(WORK, "frames")
    uniq_dir = os.path.join(WORK, "uniq")
    os.makedirs(uniq_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(frames_dir) if f.lower().endswith(".jpg"))
    if not files:
        raise SystemExit(f"{frames_dir} 里没有帧，请先抽帧")
    print(f"frames: {len(files)}", flush=True)

    t0 = time.time()
    hashes = [ahash(os.path.join(frames_dir, f)) for f in files]
    print(f"hashed in {time.time()-t0:.0f}s", flush=True)

    groups, cur = [], 0
    for i in range(1, len(hashes)):
        if int(np.count_nonzero(hashes[i] != hashes[i - 1])) > HASH_T:
            groups.append((cur, i - 1))
            cur = i
    groups.append((cur, len(hashes) - 1))
    print(f"groups: {len(groups)}", flush=True)

    idx2g = {}
    for gi, (s, e) in enumerate(groups):
        for i in range(s, e + 1):
            idx2g[i] = gi

    keep = set()
    for s, e in groups:
        keep.add(e)                          # 每组末帧 = 该页最完整状态
        if e - s > 3:
            keep.add(s + (e - s) // 2)
    if EVERY > 0:
        for i in range(0, len(hashes), EVERY):
            keep.add(i)
    keep = sorted(keep)
    print(f"keep: {len(keep)}", flush=True)

    meta = []
    for k in keep:
        src = os.path.join(frames_dir, files[k])
        dst = os.path.join(uniq_dir, files[k])
        if not os.path.exists(dst):
            Image.open(src).save(dst, quality=92)
        s, e = groups[idx2g[k]]
        meta.append({"idx": k, "file": files[k],
                     "t": round((k + 1) * INTERVAL, 1),
                     "g_start": round((s + 1) * INTERVAL, 1),
                     "g_end": round((e + 1) * INTERVAL, 1)})
    with open(os.path.join(WORK, "uniq_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print(f"DONE {len(meta)} representative frames -> uniq/", flush=True)


if __name__ == "__main__":
    main()
