# -*- coding: utf-8 -*-
"""R5（U46）文档修订：从 v15_full.before_R5.md 重建 v15_full.md。

所有修改都以改动前文件的行号为基准，写在 r5_ops_*.py 里：
  ("sub", 行号, 旧子串, 新子串)   行内替换，旧子串必须在该行恰好出现一次（先前的 sub 已作用于同一行时按当前内容匹配）
  ("gsub", 行号, 旧子串, 新子串)  行内全部替换，至少命中一次
  ("line", 行号, 新整行)          整行替换
  ("del", 行号)                   删除该行
  ("after", 行号, 文本)           在该行之后插入（文本可含多行）
运行：python r5_patch.py [--check]
"""
import glob
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "v15_full.before_R5.md")
DST = os.path.join(HERE, "v15_full.md")


def load_ops():
    ops = []
    for p in sorted(glob.glob(os.path.join(HERE, "r5_ops_*.py"))):
        spec = importlib.util.spec_from_file_location(os.path.basename(p)[:-3], p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        for op in m.OPS:
            ops.append((os.path.basename(p), op))
    return ops


def main():
    check = "--check" in sys.argv
    with io.open(SRC, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.split(nl)
    cur = dict((i + 1, s) for i, s in enumerate(lines))
    deleted = set()
    inserts = {}
    errors = []
    n = {"sub": 0, "gsub": 0, "line": 0, "del": 0, "after": 0}
    for fn, op in load_ops():
        kind = op[0]
        ln = op[1]
        if ln not in cur:
            errors.append("%s: 行号越界 %r" % (fn, op[:2]))
            continue
        if kind == "sub":
            old, new = op[2], op[3]
            c = cur[ln].count(old)
            if c != 1:
                errors.append("%s: L%d 旧子串出现 %d 次: %s" % (fn, ln, c, old[:40]))
                continue
            cur[ln] = cur[ln].replace(old, new)
        elif kind == "gsub":
            old, new = op[2], op[3]
            if cur[ln].count(old) < 1:
                errors.append("%s: L%d gsub 未命中: %s" % (fn, ln, old[:40]))
                continue
            cur[ln] = cur[ln].replace(old, new)
        elif kind == "line":
            cur[ln] = op[2]
        elif kind == "del":
            deleted.add(ln)
        elif kind == "after":
            inserts.setdefault(ln, []).append(op[2])
        else:
            errors.append("%s: 未知操作 %r" % (fn, kind))
            continue
        n[kind] += 1
    if errors:
        sys.stdout.write("\n".join(errors) + "\n")
        sys.stdout.write("失败：%d 处，未写文件\n" % len(errors))
        sys.exit(1)
    out = []
    for i in range(1, len(lines) + 1):
        if i not in deleted:
            out.extend(cur[i].split(chr(10)))
        for t in inserts.get(i, []):
            out.extend(t.split("\n"))
    text = nl.join(out)
    sys.stdout.write("ops %r -> %d 行\n" % (n, len(out)))
    if not check:
        with io.open(DST, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        sys.stdout.write("已写 %s\n" % DST)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
