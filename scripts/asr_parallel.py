# -*- coding: utf-8 -*-
"""并行分片转写：把长音频切块，多进程并行跑 faster-whisper，结果合并。
用法: python asr_parallel.py <wav> <out_jsonl> <model_dir> <workers> <threads> <chunk_sec>
"""
import sys, os, json, subprocess, time, math
from concurrent.futures import ProcessPoolExecutor, as_completed

FFMPEG = r"C:\Users\Jason\.local\bin\ffmpeg.exe"

WAV, OUT, MODEL_DIR = sys.argv[1], sys.argv[2], sys.argv[3]
WORKERS, THREADS, CHUNK = int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6])
WORK = os.path.dirname(os.path.abspath(WAV))

_CACHE = {}


def _get_pipe():
    if "pipe" not in _CACHE:
        from faster_whisper import WhisperModel, BatchedInferencePipeline
        m = WhisperModel(MODEL_DIR, device="cpu", compute_type="int8", cpu_threads=THREADS)
        _CACHE["pipe"] = BatchedInferencePipeline(model=m)
    return _CACHE["pipe"]


def run(job):
    p, off, o = job
    if os.path.exists(o) and os.path.getsize(o) > 0:
        return o, 0.0
    t0 = time.time()
    segs, _ = _get_pipe().transcribe(
        p, language="zh", batch_size=4, beam_size=5, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=False,
        initial_prompt="以下是一节心理学教师招聘考试精讲课程录音，涉及普通心理学与教育心理学专业内容。",
    )
    k = 0
    with open(o, "w", encoding="utf-8") as f:
        for sg in segs:
            tx = sg.text.strip()
            if tx:
                f.write(json.dumps({"start": round(sg.start + off, 2), "end": round(sg.end + off, 2),
                                    "text": tx}, ensure_ascii=False) + "\n")
                k += 1
    return o, time.time() - t0


def main():
    import wave
    parts = os.path.join(WORK, "parts")
    os.makedirs(parts, exist_ok=True)
    with wave.open(WAV, "rb") as w:
        dur = w.getnframes() / w.getframerate()
    n = math.ceil(dur / CHUNK)
    print(f"audio {dur:.0f}s -> {n} chunks of {CHUNK:.0f}s", flush=True)

    tasks = []
    for i in range(n):
        s = i * CHUNK
        t = min(CHUNK, dur - s)
        if t < 5:
            continue
        p = os.path.join(parts, f"p{i:03d}.wav")
        if not os.path.exists(p):
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", str(s), "-t", str(t),
                            "-i", WAV, "-c:a", "pcm_s16le", p], check=True)
        tasks.append((p, s, os.path.join(parts, f"p{i:03d}.jsonl")))
    print(f"prepared {len(tasks)} chunks", flush=True)

    t0 = time.time()
    results, done = [], 0
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(run, j): j for j in tasks}
        for fu in as_completed(futs):
            try:
                o, el = fu.result()
                results.append(o)
                done += 1
                print(f"  [{done}/{len(tasks)}] {os.path.basename(o)} {el:.0f}s elapsed={time.time()-t0:.0f}s", flush=True)
            except Exception as e:
                print("  FAIL", futs[fu][0], repr(e)[:150], flush=True)

    rows = []
    for o in sorted(results):
        with open(o, encoding="utf-8") as f:
            for l in f:
                rows.append(json.loads(l))
    rows.sort(key=lambda r: r["start"])
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"MERGED {len(rows)} segments -> {OUT} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
