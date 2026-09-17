# -*- coding: utf-8 -*-
"""长课程视频 → 学习手册素材：一键流水线。

用法:
  python run_pipeline.py <video> <workdir> [--out OUTDIR] [--minutes N]
                         [--workers-asr 4] [--workers-ocr 12] [--interval 2]
                         [--keep] [--skip-frames]

流程: 探流 → 抽音频 → SenseVoice 转写 → 抽帧 → 去重 → 幻灯片 OCR
      → 归并唯一幻灯片 → 清洗文字稿 → (默认) 清理中间文件

产物(在 OUTDIR):
  transcript.txt        带标点、术语纠正后的文字稿
  slides_unique.txt     去重归并后的幻灯片文本
  ocr_all.jsonl         每帧 OCR 原始结果
  uniq_meta.json        帧时间轴元数据
"""
import argparse, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.environ.get("FFMPEG_BIN", r"C:\Users\Jason\.local\bin\ffmpeg.exe")
PY_ASR = os.environ.get("PY_ASR", r"C:\Users\Jason\.workbuddy\binaries\python\envs\whisper\Scripts\python.exe")
PY_OCR = os.environ.get("PY_OCR", r"C:\Users\Jason\.workbuddy\binaries\python\envs\dysub2\Scripts\python.exe")


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd[:6]), "..." if len(cmd) > 6 else "", flush=True)
    return subprocess.run(cmd, check=True, **kw)


def step(n, total, title):
    print(f"\n{'='*6} [{n}/{total}] {title} {'='*6}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("workdir")
    ap.add_argument("--out", default=None)
    ap.add_argument("--minutes", type=float, default=0, help="只处理前 N 分钟(试跑用)")
    ap.add_argument("--workers-asr", type=int, default=4)
    ap.add_argument("--workers-ocr", type=int, default=12)
    ap.add_argument("--interval", type=float, default=2.0, help="抽帧间隔秒")
    ap.add_argument("--frame-width", type=int, default=960,
                    help="抽帧宽度。配图要 1200 就直接写 1200——"
                         "去重用的 aHash 会缩到 16x16、OCR 的 det 上限也是 960，"
                         "所以一次抽 1200 宽就能同时满足配图需求，省掉一遍全片重抽")
    ap.add_argument("--every-n", type=int, default=0, help="0=只 OCR 分组代表帧")
    ap.add_argument("--keep", action="store_true", help="保留中间文件")
    ap.add_argument("--skip-frames", action="store_true")
    a = ap.parse_args()

    video = os.path.abspath(a.video)
    work = os.path.abspath(a.workdir)
    out = os.path.abspath(a.out or os.path.join(os.path.dirname(work), "out"))
    os.makedirs(work, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    T = 6 if not a.skip_frames else 3
    t_all = time.time()

    # 1 探流
    step(1, T, "探流")
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", video], capture_output=True, text=True, errors="ignore")
    for line in (p.stderr or "").splitlines():
        if "Duration" in line or "Stream #" in line:
            print("   ", line.strip())

    # 2 抽音频
    step(2, T, "抽取音频 16kHz 单声道")
    wav = os.path.join(work, "audio16k.wav")
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", video]
    if a.minutes:
        cmd += ["-t", str(a.minutes * 60)]
    run(cmd + ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav])

    # 3 ASR
    step(3, T, "SenseVoice 并行转写")
    asr_out = os.path.join(out, "asr_raw.jsonl")
    run([PY_ASR, "-u", os.path.join(HERE, "sv_parallel.py"), wav, asr_out,
         str(a.workers_asr), "3", "22"])

    if not a.skip_frames:
        # 4 抽帧
        step(4, T, "全片抽帧")
        fdir = os.path.join(work, "frames")
        os.makedirs(fdir, exist_ok=True)
        if not os.listdir(fdir):
            cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", video]
            if a.minutes:
                cmd += ["-t", str(a.minutes * 60)]
            run(cmd + ["-vf", f"fps=1/{a.interval},scale={a.frame_width}:-2", "-q:v", "3",
                       os.path.join(fdir, "%06d.jpg")])
        print("    帧数:", len(os.listdir(fdir)))

        # 5 去重
        step(5, T, "感知哈希去重")
        run([PY_OCR, "-u", os.path.join(HERE, "dedupe.py"), work,
             str(a.interval), str(a.every_n)])

        # 6 OCR
        step(6, T, "幻灯片 OCR")
        run([PY_OCR, "-u", os.path.join(HERE, "ocr_fast.py"), work,
             str(a.workers_ocr), "960"])

    # 7 归并 + 清洗文字稿
    step(7, 7, "归并唯一幻灯片 + 清洗文字稿")
    _merge(work, out)

    if not a.keep:
        _cleanup(work)
    print(f"\n总耗时 {(time.time()-t_all)/60:.1f} 分钟  产物目录: {out}", flush=True)


def _merge(work, out):
    mp = os.path.join(work, "uniq_meta.json")
    if os.path.exists(mp):
        meta = json.load(open(mp, encoding="utf-8"))
        rows = []
        for m in meta:
            fp = os.path.join(work, "ocr_fast", m["file"] + ".json")
            if os.path.exists(fp):
                rows.append(json.load(open(fp, encoding="utf-8")))
        rows.sort(key=lambda r: r["t"])
        with open(os.path.join(out, "ocr_all.jsonl"), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        shutil.copy(mp, os.path.join(out, "uniq_meta.json"))

        # 相邻页文本归一化后相同则合并；后一条是前一条超集则只留最长（该页最终状态）
        def norm(t):
            return re.sub(r"[\s\W_]+", "", t)
        merged = []
        for r in rows:
            if len(norm(r["text"])) < 45:
                continue          # 纯品牌页/过渡帧
            if merged:
                x, y = norm(merged[-1]["text"]), norm(r["text"])
                if y.startswith(x) and len(y) > len(x):
                    merged[-1] = r
                    continue
                if x.startswith(y):
                    continue
                if len(set(x) & set(y)) / max(1, len(set(y))) > 0.92:
                    if len(y) > len(x):
                        merged[-1] = r
                    continue
            merged.append(r)
        with open(os.path.join(out, "slides_unique.txt"), "w", encoding="utf-8") as f:
            for i, r in enumerate(merged):
                mm, ss = divmod(int(r["t"]), 60)
                f.write(f"\n=== S{i+1:03d} [{mm:02d}:{ss:02d}] ===\n{r['text']}\n")
        print(f"    唯一幻灯片 {len(merged)} 张，OCR 帧 {len(rows)} 帧")

    ap_ = os.path.join(out, "asr_raw.jsonl")
    if os.path.exists(ap_):
        _transcript(ap_, os.path.join(out, "transcript.txt"))


def _transcript(src, dst):
    """剔除音乐幻觉 + 课程术语纠正。"""
    DROP = re.compile(r"(I miss the days|philosophers guess|How long|Drow it|Cared this|"
                      r"Hello, how low|Marisa|云层之上|阳光都渲染|这条路的中间|"
                      r"拉斯维加斯往返|no more So how|memories from|expiration dates|pull me out|ship is)")
    EN = re.compile(r"^[A-Za-z0-9 ,.'\"?!-]{25,}$")
    FIX = [
        # ⚠️ 2026-09-16 修正：原写法是 (感觉)?(预线|预先|…)，因为「感觉」是可选的，
        #    会把普通词「预先」也误改成「感觉阈限」（心理学4 里老师讲的是"预先的目的"，
        #    结果全被改成"感觉阈限的目的"）。必须要求「感觉」前缀。
        (r"感觉(预线|预先|欲限|阀限|阅限|阐限)", r"感觉阈限"),
        (r"(?<!感觉)(阀限|阅限|阐限|欲限)", r"阈限"),
        (r"(连绝|连觉|联绝)", "联觉"), (r"(复后像|副后像|副后项|免后像|负后项)", "负后像"),
        (r"正后相", "正后像"), (r"(横长|恒长)", "恒常"), (r"装大方神", "状大方神"),
        (r"时空洞", "时空动"), (r"马赫代", "马赫带"), (r"盲人耳税", "盲人耳聪"),
        (r"以军花目", "以耳代目"), (r"(试牙|释牙)", "视崖"), (r"痛诀", "痛觉"),
        (r"触压诀", "触压觉"), (r"听秀未夫", "视听嗅味肤"), (r"月明星星", "月明星稀"),
        (r"克美纽斯", "夸美纽斯"), (r"巴南洛夫", "巴甫洛夫"), (r"入知蓝之势", "入芝兰之室"),
        (r"入鲍鱼之势", "入鲍鱼之肆"), (r"酒而不闻", "久而不闻"), (r"(大赞戒|撰戒)", "钻戒"),
        (r"义务感", "异物感"), (r"功名时间", "工厂时间"), (r"蚊香叶", "蚊香液"),
        (r"鹤立基群", "鹤立鸡群"), (r"万绿从中", "万绿丛中"), (r"金鸡爆天门", "金鸡报天门"),
        (r"柯震恶", "柯镇恶"), (r"童彤", "僮僮"), (r"遇习", "预习"), (r"光胆", "光顾"),
        (r"6号", "溜号"), (r"透话", "内化"), (r"考评", "考频"), (r"抑制过程", "意志过程"),
    ]
    rows = [json.loads(l) for l in open(src, encoding="utf-8")]
    rows = [r for r in rows if not DROP.search(r["text"]) and not EN.match(r["text"].strip())]
    lines = []
    for r in rows:
        t = r["text"]
        for p, rep in FIX:
            t = re.sub(p, rep, t)
        mm, ss = divmod(int(r["start"]), 60)
        lines.append(f"[{mm:02d}:{ss:02d}] {t}")
    open(dst, "w", encoding="utf-8").write("\n".join(lines))
    print(f"    文字稿 {len(lines)} 段 / {sum(len(l) for l in lines)} 字 -> {dst}")


def _cleanup(work):
    """列出可删除的中间文件；实际删除交给上层（宿主的批量删除保护会拦截脚本内删除）。

    实测：脚本内 shutil.rmtree 删几千个帧时会被 host 的 safe-delete 拦下
    （SAFE_DELETE_BULK_CONFIRM_REQUIRED）。所以这里只做统计与提示，
    由 agent 在获得授权后单独执行删除命令。
    """
    targets, freed = [], 0
    for d in ["parts", "frames", "uniq", "peek"]:
        p = os.path.join(work, d)
        if os.path.isdir(p):
            sz = sum(os.path.getsize(os.path.join(r, f))
                     for r, _, fs in os.walk(p) for f in fs)
            targets.append(p)
            freed += sz
    for f in os.listdir(work):
        if f.endswith((".wav", ".log")) or f.startswith(("pb", "pl", "bench")):
            p = os.path.join(work, f)
            if os.path.isfile(p):
                targets.append(p)
                freed += os.path.getsize(p)

    if not targets:
        print("\n无需清理（中间文件已不存在）")
        return
    print(f"\n{'='*6} 待清理中间文件：{len(targets)} 项 / {freed/1024/1024:.0f} MB {'='*6}")
    for t in targets:
        print("   ", t)
    print("\n请执行（批量删除需授权）：")
    print("   rm -rf " + " ".join(f'"{t}"' for t in targets))
    print("保留：ocr*/、uniq_meta.json、各 out/ 产物")


if __name__ == "__main__":
    main()
