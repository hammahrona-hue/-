# PROBE2.md — 第二次探针（3 条命令，30 秒）

> 只跑下面 3 组命令，如实贴输出。**不要**跑 setup.sh、不要下载视频、不要跑转写。
> 目的：确认上一轮三个疑点（CPU 核数 / 模型源 / push 修复）到底是真问题还是虚惊。

## 1. 真实 CPU 配额是多少？（上一轮 nproc 报 1 核）

```bash
echo "nproc: $(nproc)"
echo "cpu.max: $(cat /sys/fs/cgroup/cpu.max 2>/dev/null || echo 'n/a')"
echo "quota:   $(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us 2>/dev/null || echo 'n/a')"
echo "period:  $(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us 2>/dev/null || echo 'n/a')"
echo "affinity: $(taskset -cp $$ 2>/dev/null || echo 'n/a')"
```

**怎么看**：`cpu.max` 形如 `400000 100000` → 配额/周期 = **4 核**；
`100000 100000` → 1 核；`max 100000` → 不限制。
把原始输出贴出来，不要自己下结论。

## 2. 模型源到底通不通？（上一轮 308 是因为漏了 -L）

```bash
B=https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main
curl -sSL -o /dev/null -w "tokens.txt  final=%{http_code}  bytes=%{size_download}\n" "$B/tokens.txt"
curl -sSL -o /dev/null -w "model       final=%{http_code}  bytes=%{size_download}\n" -r 0-1023 "$B/model.int8.onnx"
```

**怎么看**：两条都 `final=200` 且 `bytes>0` 就是通的（model 那条只取前 1KB，正常）。

## 3. push 修复验证（上一轮 exit 128）

```bash
echo "probe2 $(date -u +%FT%TZ)" >> probe.txt
git add probe.txt && git commit -m "probe2: push 修复验证"
git push -u origin HEAD; echo "PUSH_EXIT=$?"
git log --oneline -1
```

**怎么看**：`PUSH_EXIT=0` 就是修好了。非 0 就把报错原文贴出来。

---

## 最后只回答两句话

1. **真实可用核数是多少？**（贴 `cpu.max` 原始值 + 你算出来的核数）
2. **push 成功了吗？**（`PUSH_EXIT=0` 还是别的值）

不要编造，跑不出来就说跑不出来。
