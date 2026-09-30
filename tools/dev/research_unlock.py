"""Mark research entries as completed in the running SOVIET64 (progress float at record+0xD0 = 1.0).
Research table: vector at game context + 0x11778 (records of 0xE8 bytes, name at +0), as written
out to research.bin by 0x2F7D40. Test helper for worlds with research switched off.
    python tools/dev/research_unlock.py sr_          # every entry whose name starts with sr_
    python tools/dev/research_unlock.py sr_ --dry    # list only"""
import ctypes, struct, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import memprobe as m

prefix = sys.argv[1] if len(sys.argv) > 1 else 'sr_'
dry = '--dry' in sys.argv
pid = m.pid_of()
p = m.Proc(pid)
ctx = p.base + m.CTX_RVA
beg, end = p.q(ctx + 0x11778), p.q(ctx + 0x11780)
n = (end - beg) // 0xE8
print('%d research records' % n)
h = None if dry else m.k32.OpenProcess(0x0038, False, pid)   # VM_OPERATION | VM_READ | VM_WRITE
if not dry and not h:
    sys.exit('OpenProcess for writing failed %d' % ctypes.get_last_error())
if h:
    m.k32.WriteProcessMemory.argtypes = [m.w.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
for i in range(n):
    rec = beg + i * 0xE8
    name = (p.read(rec, 64) or b'').split(b'\0')[0].decode('latin-1')
    prog = struct.unpack('<f', p.read(rec + 0xD0, 4))[0]
    if not name.startswith(prefix):
        continue
    if not dry and prog < 1.0:
        one = struct.pack('<f', 1.0)
        wrote = ctypes.c_size_t()
        ok = m.k32.WriteProcessMemory(h, ctypes.c_void_p(rec + 0xD0), one, 4, ctypes.byref(wrote))
        prog2 = struct.unpack('<f', p.read(rec + 0xD0, 4))[0]
        print('  %-24s %.2f -> %.2f %s' % (name, prog, prog2, '' if ok else 'WRITE FAILED'))
    else:
        print('  %-24s %.2f' % (name, prog))
