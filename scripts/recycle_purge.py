# -*- coding: utf-8 -*-
"""按原始路径前缀，从回收站中彻底清除指定项目（$I 元数据 + $R 数据）。
用法: python recycle_purge.py <路径前缀关键词> [<关键词2> ...]
     加 --list 只列出不删除
"""
import os, sys, struct, shutil

def parse_i(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 24:
        return None
    size = struct.unpack("<Q", data[8:16])[0]
    nlen = struct.unpack("<I", data[24:28])[0]
    name = data[28:28 + nlen * 2].decode("utf-16-le", "ignore").rstrip("\x00")
    return {"size": size, "orig": name}


def collect(roots):
    out = []
    for root in roots:
        try:
            sids = os.listdir(root)
        except Exception:
            continue
        for sid in sids:
            d = os.path.join(root, sid)
            if not os.path.isdir(d):
                continue
            try:
                names = os.listdir(d)
            except Exception:
                continue
            for fn in names:
                if fn.startswith("$I"):
                    try:
                        m = parse_i(os.path.join(d, fn))
                    except Exception:
                        continue
                    if m:
                        m["i_path"] = os.path.join(d, fn)
                        m["r_path"] = os.path.join(d, "$R" + fn[2:])
                        out.append(m)
    return out


def rmtree_force(p):
    try:
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.exists(p):
            os.remove(p)
        return not os.path.exists(p)
    except Exception:
        return False


def main():
    roots = ['C:\\$Recycle.Bin', 'D:\\$Recycle.Bin']
    keys = [a for a in sys.argv[1:] if not a.startswith("--")]
    listing_only = "--list" in sys.argv
    items = collect(roots)
    hits = [i for i in items if keys and any(k.lower() in i["orig"].lower() for k in keys)]
    print(f"匹配 {len(hits)} 项，合计 {sum(i['size'] for i in hits)/1024/1024:.1f} MB")
    for i in hits[:15]:
        print("   ", i["orig"])
    if len(hits) > 15:
        print(f"    ...以及另外 {len(hits)-15} 项")
    if listing_only:
        return
    ok = fail = 0
    freed = 0
    for i in hits:
        a = rmtree_force(i["r_path"])
        b = rmtree_force(i["i_path"])
        if a and b:
            ok += 1
            freed += i["size"]
        else:
            fail += 1
    print(f"\n清除成功 {ok} 项，失败 {fail} 项，释放 {freed/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
