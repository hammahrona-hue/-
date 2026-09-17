# -*- coding: utf-8 -*-
"""优化版 RapidOCR 封装。

原始 rapidocr_onnxruntime 的两个致命伤：
1. OrtInferSession 用裸 SessionOptions()，intra_op_num_threads 默认=物理核数。
   多进程并行时 N 进程 × 3 会话 × 14 线程 → 线程爆炸，CPU 全花在上下文切换上。
2. 默认 use_angle_cls=True（每个文本框都过一次方向分类模型）+ Det limit_type=min
   会把 960x444 的图放大到 1591x736 再检测，白算 2.7 倍像素。

本模块做三件事：锁线程、关方向分类、按原分辨率检测。
"""
import os
import numpy as np

import onnxruntime as ort
import rapidocr_onnxruntime.utils as _U


def _make_session_options():
    o = ort.SessionOptions()
    o.intra_op_num_threads = int(os.environ.get("RAPIDOCR_THREADS", "1"))
    o.inter_op_num_threads = 1
    o.enable_cpu_mem_arena = False
    o.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    o.log_severity_level = 4
    return o


def patch_threads():
    """让 OrtInferSession 用我们锁了线程的 SessionOptions。"""
    _U.SessionOptions = _make_session_options


_OCR = {}


def get_ocr(det_side=960):
    """det_side: 检测网络输入的长边上限（limit_type=max）。960 与原图等宽，不放大也不缩。"""
    key = det_side
    if key not in _OCR:
        patch_threads()
        from rapidocr_onnxruntime import RapidOCR
        _OCR[key] = RapidOCR(
            use_angle_cls=False,          # 幻灯片全是横排文字，方向分类纯属浪费
            text_score=0.4,
            det_model_path=None,          # 前缀式 kwargs 要求该键存在，None 表示用默认模型
            det_limit_side_len=det_side,  # 默认 min/736 会把短边放大到 736
            det_limit_type="max",
            det_box_thresh=0.5,
            det_unclip_ratio=1.6,
            det_use_dilation=False,       # 默认 True，形态学膨胀在幻灯片上收益极小
            rec_model_path=None,
            rec_batch_num=16,
        )
    return _OCR[key]


def read(img_path, det_side=960, min_score=0.40):
    """返回按视觉顺序排好的文本行列表。"""
    ocr = get_ocr(det_side)
    res, _ = ocr(img_path)
    if not res:
        return []
    lines = []
    for box, txt, score in res:
        try:
            sc = float(score)
        except Exception:
            sc = 1.0
        if sc >= min_score:
            ys = [p[1] for p in box]
            xs = [p[0] for p in box]
            lines.append((min(ys), min(xs), txt))
    lines.sort(key=lambda x: (round(x[0] / 18), x[1]))
    seen, out = set(), []
    for _, _, t in lines:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


if __name__ == "__main__":
    import sys, time
    p = sys.argv[1]
    t0 = time.time()
    rows = read(p)
    print(f"{time.time()-t0:.2f}s  {len(rows)} lines")
    print("\n".join(rows[:40]))
