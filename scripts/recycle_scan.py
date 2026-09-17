# -*- coding: utf-8 -*-
"""解析 Windows 回收站 $I 元数据文件，列出被删文件的原始路径与大小。"""
import os, struct, datetime, sys, glob

def parse_i(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 24:
        return None
    ver = struct.unpack("<Q", data[0:8])[0]
    size = struct.unpack("<Q", data[8:16])[0]
    ft = struct.unpack("<Q", data[16:24])[0]
    try:
        dt = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=ft / 10)
        dt = dt + datetime.timedelta(hours=0)
    except Exception:
        dt = None
    if ver == 1:
        nlen = struct.unpack("<I", data[24:28])[0]
        name = data[28:28 + nlen * 2].decode("utf-16-le", "ignore").rstrip("\x00")
    else:
        nlen = struct.unpack("<I", data[24:28])[0]
        name = data[28:28 + nlen * 2].decode("utf-16-le", "ignore").rstrip("\x00")
    return {"ver": ver, "size": size, "time": dt, "orig": name}


def main():
    roots = sys.argv[1:] or ['C:\\$Recycle.Bin']
    items = []
    for root in roots:
        try:
            sids = os.listdir(root)
        except Exception as e:
            print("skip", root, e)
            continue
        for sid in sids:
            d = os.path.join(root, sid)
            if not os.path.isdir(d):
                continue
            try:
                names = os.listdir(d)
            except Exception:
                continue          # S-1-5-18 等系统账户无权限，跳过
            for fn in names:
                if fn.startswith("$I"):
                    try:
                        m = parse_i(os.path.join(d, fn))
                        if m:
                            m["sid"] = sid
                            m["root"] = root
                            items.append(m)
                    except Exception:
                        pass
    items.sort(key=lambda x: x["time"] or datetime.datetime.min, reverse=True)
    total = sum(i["size"] for i in items)
    print(f"共 {len(items)} 项，合计 {total/1024/1024:.1f} MB\n")
    for i in items:
        t = i["time"].strftime("%m-%d %H:%M") if i["time"] else "?"
        print(f"[{t}] {i['size']/1024:9.1f} KB  {i['orig']}")
    return items


if __name__ == "__main__":
    main()
