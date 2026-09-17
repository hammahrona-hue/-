# -*- coding: utf-8 -*-
"""优化版幻灯片 OCR：多进程 + 锁线程。
用法: python ocr_fast.py <workdir> <workers> [det_side]
"""
import sys, os, json, time, re
from concurrent.futures import ProcessPoolExecutor, as_completed

WORK = sys.argv[1]
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 12
DET_SIDE = int(sys.argv[3]) if len(sys.argv) > 3 else 960


def _job(item):
    import fast_ocr
    p = os.path.join(WORK, "uniq", item["file"])
    try:
        lines = fast_ocr.read(p, det_side=DET_SIDE)
    except Exception as e:
        lines = []
        item = dict(item, err=repr(e)[:150])
    return dict(item, text="\n".join(lines))


def main():
    os.environ.setdefault("RAPIDOCR_THREADS", "1")
    ocr_dir = os.path.join(WORK, "ocr_fast")
    os.makedirs(ocr_dir, exist_ok=True)
    meta = json.load(open(os.path.join(WORK, "uniq_meta.json"), encoding="utf-8"))
    todo = [m for m in meta if not os.path.exists(os.path.join(ocr_dir, m["file"] + ".json"))]
    print(f"frames={len(meta)}  todo={len(todo)}  workers={WORKERS}", flush=True)

    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for fu in as_completed([ex.submit(_job, m) for m in todo]):
            try:
                r = fu.result()
                with open(os.path.join(ocr_dir, r["file"] + ".json"), "w", encoding="utf-8") as f:
                    json.dump(r, f, ensure_ascii=False)
            except Exception as e:
                print("FAIL", repr(e)[:120], flush=True)
            done += 1
            if done % 20 == 0 or done == len(todo):
                el = time.time() - t0
                print(f"  {done}/{len(todo)} elapsed={el:.0f}s eta={el/done*(len(todo)-done):.0f}s "
                      f"({done/el:.2f} 帧/秒)", flush=True)

    rows = []
    for m in meta:
        fp = os.path.join(ocr_dir, m["file"] + ".json")
        if os.path.exists(fp):
            rows.append(json.load(open(fp, encoding="utf-8")))
    with open(os.path.join(WORK, "ocr_fast.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"DONE {len(rows)} frames in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
