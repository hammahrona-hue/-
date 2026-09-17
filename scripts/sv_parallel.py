# -*- coding: utf-8 -*-
"""SenseVoice 并行全片转写：静音感知切分 + 多进程。
用法: python sv_parallel.py <wav> <out_jsonl> <workers> <threads> <chunk_sec>
"""
import sys, os, json, time, wave, math
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

WAV, OUT = sys.argv[1], sys.argv[2]
WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 4
THREADS = int(sys.argv[4]) if len(sys.argv) > 4 else 3
CHUNK = float(sys.argv[5]) if len(sys.argv) > 5 else 22.0
WORK = os.path.dirname(os.path.abspath(WAV))
SVDIR = os.environ.get("SENSEVOICE_DIR", "")

# 模型路径解析优先级：环境变量 → 工作目录/sv → 长期模型库
_CANDIDATES = [
    SVDIR,
    os.path.join(WORK, "sv"),
    os.path.expanduser(r"~\.workbuddy\models\sense-voice-zh-en-ja-ko-yue"),
]
for _c in _CANDIDATES:
    if _c and os.path.exists(os.path.join(_c, "model.int8.onnx")):
        SVDIR = _c
        break
else:
    raise SystemExit(
        "找不到 SenseVoice 模型 model.int8.onnx。\n"
        "请设置环境变量 SENSEVOICE_DIR，或下载到 ~/.workbuddy/models/sense-voice-zh-en-ja-ko-yue/：\n"
        '  B="https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main"\n'
        '  curl -sL -o model.int8.onnx "$B/model.int8.onnx"\n'
        '  curl -sL -o tokens.txt      "$B/tokens.txt"'
    )


def _decode(args):
    idx, sr, seg, off = args
    import sherpa_onnx
    global _REC
    try:
        _REC
    except NameError:
        _REC = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=os.path.join(SVDIR, "model.int8.onnx"),
            tokens=os.path.join(SVDIR, "tokens.txt"),
            num_threads=THREADS, use_itn=True, language="zh", debug=False)
    s = _REC.create_stream()
    s.accept_waveform(sr, seg)
    _REC.decode_stream(s)
    return idx, off, s.result.text.strip()


def main():
    with wave.open(WAV, "rb") as w:
        sr, n = w.getframerate(), w.getnframes()
        audio = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    dur = len(audio) / sr
    step = int(CHUNK * sr)
    print(f"audio {dur:.0f}s, chunk {CHUNK}s", flush=True)

    # 静音感知切分：在目标点 ±2s 内找能量最低处下刀，避免切断词
    cuts, pos = [0], step
    win = int(2.0 * sr)
    while pos < len(audio) - sr:
        lo, hi = max(0, pos - win), min(len(audio), pos + win)
        seg = audio[lo:hi]
        hop = int(0.02 * sr)
        e = np.array([np.sum(seg[i:i + hop] ** 2) for i in range(0, len(seg) - hop, hop)])
        best = lo + int(np.argmin(e)) * hop if len(e) else pos
        cuts.append(best)
        pos = best + step
    cuts.append(len(audio))
    jobs = [(i, sr, audio[cuts[i]:cuts[i + 1]], round(cuts[i] / sr, 2))
            for i in range(len(cuts) - 1) if cuts[i + 1] - cuts[i] > sr * 0.4]
    print(f"chunks: {len(jobs)}", flush=True)

    t0 = time.time()
    rows, done = [], 0
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for fu in as_completed([ex.submit(_decode, j) for j in jobs]):
            try:
                idx, off, text = fu.result()
                if text:
                    rows.append({"start": off, "end": off, "text": text})
            except Exception as e:
                print("FAIL", repr(e)[:120], flush=True)
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(jobs)} elapsed={time.time()-t0:.0f}s", flush=True)
    rows.sort(key=lambda r: r["start"])
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    el = time.time() - t0
    print(f"MERGED {len(rows)} segs in {el:.0f}s => {dur/el:.1f}x 实时  -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
