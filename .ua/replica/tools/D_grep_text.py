# -*- coding: utf-8 -*-
"""D_grep_text.py  在 References/fyqc/fyqc-client/text 下按关键词搜配置（自动把 \\uXXXX 还原成中文）。
用法: python D_grep_text.py <正则> [文件名过滤正则] [上下文字符数]
只读，不写任何文件。
"""
import io, re, os, glob, json, sys

ROOT = r'D:\GameDev\the-shuttle-badminton-glory\References\fyqc\fyqc-client\text'
SKIP = re.compile(r'^(cn|tw|common_|shenhe|protectwhite|hanzi|word2pinyin|unicodezone|NameWeight|com_enter|whitelist|'
                  r'Traditional|English|Clause|Translation|A5_dlt|a5_kbn|.*(english|japanese|korean|traditionalchinese)\.txt)')
U = re.compile(r'\\u([0-9a-fA-F]{4})')


def load(path):
    s = io.open(path, encoding='utf-8', errors='replace').read()
    if U.search(s[:200000]):
        s = U.sub(lambda m: chr(int(m.group(1), 16)), s)
    return s


def main():
    pat = re.compile(sys.argv[1])
    ffilter = re.compile(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None
    ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    for f in sorted(glob.glob(os.path.join(ROOT, '*.txt'))):
        b = os.path.basename(f)
        if SKIP.match(b):
            continue
        if ffilter and not ffilter.search(b):
            continue
        s = load(f)
        ms = list(pat.finditer(s))
        if not ms:
            continue
        print('== %s  hits=%d size=%d' % (b, len(ms), len(s)))
        if ctx > 0:
            for m in ms[:40]:
                a = max(0, m.start() - ctx)
                e = min(len(s), m.end() + ctx)
                line = s.count('\n', 0, m.start()) + 1
                print('  L%d: %s' % (line, re.sub(r'\s+', ' ', s[a:e])))


if __name__ == '__main__':
    main()
