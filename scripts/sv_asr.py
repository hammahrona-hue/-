# -*- coding: utf-8 -*-
"""SenseVoice (sherpa-onnx) 转写测试/生产脚本。
用法: python sv_asr.py <wav> <out_jsonl> <offset> [threads] [chunk_sec]
"""
import sys, os, json, time, wave
import numpy as np
import sherpa_onnx

WAV, OUT = sys.argv[1], sys.argv[2]
OFFSET = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
THREADS = int(sys.argv[4]) if len(sys.argv) > 4 else 4
CHUNK = float(sys.argv[5]) if len(sys.argv) > 5 else 22.0
MODELDIR = os.path.dirname(os.path.abspath(__file__))

t0 = time.time()
rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=os.path.join(MODELDIR, "model.int8.onnx"),
    tokens=os.path.join(MODELDIR, "tokens.txt"),
    num_threads=THREADS,
    use_itn=True,
    language="zh",
    debug=False,
)
print(f"model loaded {time.time()-t0:.1f}s", flush=True)

with wave.open(WAV, "rb") as w:
    sr = w.getframerate()
    n = w.getnframes()
    raw = w.readframes(n)
audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
dur = len(audio) / sr
print(f"audio {dur:.1f}s @ {sr}Hz", flush=True)

step = int(CHUNK * sr)
rows, t1 = [], time.time()
for i in range(0, len(audio), step):
    seg = audio[i:i + step]
    if len(seg) < sr * 0.4:
        continue
    s = rec.create_stream()
    s.accept_waveform(sr, seg)
    rec.decode_stream(s)
    text = s.result.text.strip()
    if text:
        rows.append({"start": round(OFFSET + i / sr, 2),
                     "end": round(OFFSET + min(i + step, len(audio)) / sr, 2),
                     "text": text})
el = time.time() - t1
with open(OUT, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"DONE {len(rows)} segs in {el:.0f}s  => {dur/el:.2f}x 实时", flush=True)
