# -*- coding: utf-8 -*-
"""检查图/表/实验/式 的编号前缀是否与所在章号一致（vol4/vol5）。"""
import glob, os, re, sys

PAT = re.compile(r'(图|表|实验|式)\s*(\d{1,2})-([A-Z0-9]+)')


def main():
    vols = sys.argv[1:] or ['vol4', 'vol5']
    for vol in vols:
        print(f'== {vol} ==')
        for f in sorted(glob.glob(os.path.join('_build', 'vol', vol, '*.html'))):
            base = os.path.basename(f)
            if base.startswith('_'):
                continue
            m = re.match(r'(\d{2})_', base)
            if not m:
                continue
            ch = int(m.group(1))
            t = open(f, encoding='utf-8', errors='replace').read()
            bad = {}
            for kind, num, rest in PAT.findall(t):
                if int(num) != ch:
                    key = f'{kind}{num}-{rest}'
                    bad[key] = bad.get(key, 0) + 1
            if bad:
                top = sorted(bad.items(), key=lambda kv: -kv[1])[:6]
                print(f'  {base:40s} 不一致 {sum(bad.values()):3d} 处: ' +
                      ', '.join(f'{k}×{v}' for k, v in top))
            else:
                print(f'  {base:40s} OK')


if __name__ == '__main__':
    main()
