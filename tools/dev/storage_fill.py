"""Test helper: put goods into storage buildings of the running SOVIET64.
Storages: building+0x970 vector of 0xE0-byte records; each record's slot vector at +0 holds
16-byte slots { Resource*, float content, float limit } (resource name at +0).

    python tools/dev/storage_fill.py list                       # storage buildings, their idents and contents
    python tools/dev/storage_fill.py fill <ident part> <n> <good> <tonnes>   # the n-th (0-based) building whose ident contains <ident part>
"""
import ctypes
import struct
import sys

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import memprobe as m

pid = m.pid_of()
p = m.Proc(pid)
ctx = p.base + m.CTX_RVA


def name_at(a):
    s = p.read(a, 32) if a else None
    return s.split(b'\0')[0].decode('latin-1') if s else '?'


def slots(b):
    out = []
    sb, se = p.q(b + 0x970), p.q(b + 0x978)
    if not sb or se < sb or se - sb > 32 * 0xE0:
        return out
    for r in range((se - sb) // 0xE0):
        rec = sb + r * 0xE0
        a, e = p.q(rec), p.q(rec + 8)
        if not a or e < a or e - a > 0x800:
            continue
        for j in range((e - a) // 16):
            rp, c, lim = struct.unpack('<Qff', p.read(a + j * 16, 16))
            out.append((a + j * 16, name_at(rp), c, lim))
    return out


blds = p.vec(ctx + 0x11B08)
if sys.argv[1] == 'list':
    for b in blds:
        s = slots(b)
        if s:
            print(p.ident(b)[:40], {n: '%.1f/%.0f' % (c, l) for _, n, c, l in s if c > 0 or n in ('lox', 'fuel', 'spacecraft', 'food', 'hypergolic')})
else:
    part, nth, good, t = sys.argv[2], int(sys.argv[3]), sys.argv[4], float(sys.argv[5])
    hits = [b for b in blds if part in p.ident(b) and slots(b)]
    b = hits[nth]
    h = m.k32.OpenProcess(0x0038, False, pid)
    m.k32.WriteProcessMemory.argtypes = [m.w.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    for addr, n, c, lim in slots(b):
        if n == good:
            v = min(t, lim) if lim > 0 else t
            w = ctypes.c_size_t()
            m.k32.WriteProcessMemory(h, ctypes.c_void_p(addr + 8), struct.pack('<f', v), 4, ctypes.byref(w))
            print('%s #%d: %s %.1f -> %.1f (limit %.0f)' % (p.ident(b), nth, good, c, v, lim))
            break
    else:
        print('no %s slot in %s' % (good, p.ident(b)))
