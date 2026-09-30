"""Construction cost of building types in the running game, as the game computed it (auto costs
resolved). A type (table [RVA 0x9E6A30], stride 0xBE8) keeps its construction phases in a vector at
+0x370 (begin) / +0x378 (end) of large phase records; each phase holds a std::vector of
{Resource*, float tonnes, pad} entries (found from the coal mine's absolute $COST_RESOURCE lines
with build/costfind.py). Read-only.

    python tools/dev/costdump.py [raw] coal_mine 9000101/sr_mik ...     # totals (raw: per phase too)
    python tools/dev/costdump.py kit                                    # every 9000101/sr_* type
"""
import struct
import sys

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import memprobe as m  # noqa: E402

p = m.Proc(m.pid_of())
rb, re_ = p.q(p.base + 0x9E11C0), p.q(p.base + 0x9E11C0 + 8)
res = {a: (p.read(a, 32) or b'').split(b'\0')[0].decode() for a in range(rb, re_, 832)}
tb, te = p.q(p.base + 0x9E6A30), p.q(p.base + 0x9E6A30 + 8)
types = {}
for a in range(tb, te, 0xBE8):
    types[(p.read(a, 64) or b'').split(b'\0')[0].decode('ascii', 'replace')] = a
args = sys.argv[1:]
raw = 'raw' in args
args = [a for a in args if a != 'raw']
if args == ['kit']:
    args = sorted(k for k in types if k.startswith('9000101/'))


def cost_vectors(t):
    """[(offset in the phase array, [(name, tonnes)])] for every cost vector in the type's phases."""
    b, e = p.q(t + 0x370), p.q(t + 0x378)
    if not b or e <= b or e - b > 0x100000:
        return []
    blob = p.read(b, e - b) or b''
    out = []
    for o in range(0, len(blob) - 24, 8):
        vb, ve, vc = struct.unpack_from('<QQQ', blob, o)
        if not vb or ve <= vb or vc < ve or (ve - vb) % 16 or ve - vb > 0x400:
            continue
        ents = p.read(vb, ve - vb)
        if not ents:
            continue
        items = []
        for k in range(0, len(ents), 16):
            r, f = struct.unpack_from('<Qf', ents, k)
            if r not in res:
                items = None
                break
            items.append((res[r], f))
        if items:
            out.append((o, items))
    return out


def totals(vectors):
    tot = {}
    for _o, items in vectors:
        for n, f in items:
            tot[n] = tot.get(n, 0.0) + f
    return tot


if __name__ == '__main__':
    for want in args:
        t = types.get(want)
        if not t:
            print('no type', want)
            continue
        vs = cost_vectors(t)
        if raw:
            print('== %s: %d cost vector(s)' % (want, len(vs)))
            for o, items in vs:
                print('   +0x%05X: %s' % (o, ', '.join('%s %.1f' % x for x in items)))
        tot = totals(vs)
        order = ['workers'] + sorted(k for k in tot if k != 'workers')
        print('%-26s %s' % (want, ', '.join('%s %.0f' % (k, tot[k]) for k in order if k in tot)))
