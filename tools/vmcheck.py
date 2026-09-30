"""Static checks for a scenario VM script against the game's own rules, so a
compile error does not have to be found by loading the game.

    python tools/vmcheck.py <script.txt> [...]

Checks, each taken from the VM compiler's error strings in SOVIET64.exe or from
what vanilla scripts do:
  - operators vanilla never uses (there is no >=, <=, ==, !=)
  - calls to names that are neither instructions (SOVIETInstructions.txt) nor
    functions defined in the script
  - argument count and type per call ("Invalid instruction argument type",
    "Invlid parameter count"); `void` parameters take anything
  - struct fields that do not exist ("Undefined token")
  - every function but main ending in return(x) / returnVoid()
    ("No return found at the end of function")
  - int or char variables assigned a float ("Possible loss of data")
  - else()/elseif() without a preceding if
Exit status 1 when anything is found.
"""
import glob
import re
import sys

import os  # noqa: E402
# the game folder; override with the WRSR_GAME environment variable
GAME = os.path.join(os.environ.get('WRSR_GAME', 'C:/Program Files (x86)/Steam/steamapps/common/SovietRepublic'), 'media_soviet')
INSTR = GAME + '/scripts/SOVIETInstructions.txt'


def strip_comments(src):
    src = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group().count('\n'), src, flags=re.S)
    out = []
    for line in src.split('\n'):
        res, q = '', False
        i = 0
        while i < len(line):
            c = line[i]
            if c == '"':
                q = not q
            if not q and line.startswith('//', i):
                break
            res += c
            i += 1
        out.append(res)
    return out


def split_args(s):
    args, depth, cur, q = [], 0, '', False
    for c in s:
        if c == '"':
            q = not q
        if not q:
            if c in '([':
                depth += 1
            elif c in ')]':
                depth -= 1
            elif c == ',' and depth == 0:
                args.append(cur.strip())
                cur = ''
                continue
        cur += c
    if cur.strip():
        args.append(cur.strip())
    return args


def join_open_parens(lines):
    """Merge a line whose parentheses are not closed with the lines after it (keeping the count, so
    line numbers stay right: the merged text sits on the first line, the rest become empty)."""
    out, buf, depth, first = [], '', 0, None
    for l in lines:
        q = False
        for c in l:
            if c == '"':
                q = not q
            elif not q and c == '(':
                depth += 1
            elif not q and c == ')':
                depth -= 1
        if first is None:
            first = len(out)
            buf = l
        else:
            buf += ' ' + l.strip()
        out.append('')
        if depth <= 0:
            out[first] = buf
            buf, first, depth = '', None, 0
    if first is not None:
        out[first] = buf
    return out


class Env:
    def __init__(self):
        self.instr = {}      # name -> [types]
        self.sinstr = {}     # (struct, name) -> [types]
        self.fields = {}     # struct -> {field: type}
        self.vars = {}       # global name -> type
        self.arrays = {}     # name -> element type
        self.funcs = {}      # name -> (ret, [types])
        self.load_instructions()

    def load_instructions(self):
        lines = strip_comments(open(INSTR, encoding='utf-8', errors='replace').read())
        for l in lines:
            for m in re.finditer(r'defineInstruction\((\w+)\s*,\s*\d+\s*((?:,\s*[\w\[\]]+\s*)*)\)', l):
                self.instr[m.group(1)] = [t.strip() for t in m.group(2).split(',') if t.strip()]
            for m in re.finditer(r'defineStructInstruction\((\w+)\s*,\s*(\w+)\s*,\s*\d+\s*((?:,\s*[\w\[\]]+\s*)*)\)', l):
                self.sinstr[(m.group(1), m.group(2))] = [t.strip() for t in m.group(3).split(',') if t.strip()]
            for m in re.finditer(r'defineStructVariable\((\w+)\s*,\s*(\w+)\s*,\s*(\w+)\)', l):
                self.fields.setdefault(m.group(1), {})[m.group(3)] = m.group(2)
            for m in re.finditer(r'defineStructArray\((\w+)\s*,\s*(\w+)\[\w*\]\s*,\s*(\w+)\)', l):
                self.fields.setdefault(m.group(1), {})[m.group(3)] = m.group(2) + '[]'
            for m in re.finditer(r'defineVariable\((\w+)\s*,\s*(\w+)\)', l):
                self.vars[m.group(2)] = m.group(1)
            for m in re.finditer(r'defineFunction\((\w+)\s*,\s*(\w+)((?:\s*,\s*\w+:\w+)*)\)', l):
                self.funcs[m.group(1)] = (m.group(2), [p.split(':')[0].strip() for p in m.group(3).split(',') if ':' in p])


def expr_type(e, env, local):
    e = e.strip()
    while e.startswith('(') and e.endswith(')') and split_args(e[1:-1]) == [e[1:-1].strip()]:
        e = e[1:-1].strip()
    if e.startswith('"'):
        return 'string'
    if re.fullmatch(r'-?\d+\.\d*', e):
        return 'float'
    if re.fullmatch(r'-?\d+', e):
        return 'int'
    m = re.fullmatch(r'(\w+)\s*\((.*)\)', e)
    if m and m.group(1) in env.funcs:
        return env.funcs[m.group(1)][0]
    m = re.fullmatch(r'(\w+)\.(\w+)', e)
    if m:
        st = local.get(m.group(1)) or env.vars.get(m.group(1))
        return env.fields.get(st, {}).get(m.group(2), '?field')
    m = re.fullmatch(r'(\w+)\[.*\]', e)
    if m:
        return env.arrays.get(m.group(1), '?')
    if re.fullmatch(r'\w+', e):
        if e in env.arrays:
            return env.arrays[e] + '[]'
        return local.get(e) or env.vars.get(e) or '?name'
    # an expression: float if any operand is float
    parts = re.split(r'\s*[-+*/]\s*', e)
    if len(parts) < 2:
        return '?expr'
    types = [expr_type(p, env, local) for p in parts if p]
    if 'float' in types:
        return 'float'
    if types and all(t in ('int', 'char') for t in types):
        return 'int'
    return '?expr'


def check(path, env):
    raw = open(path, encoding='utf-8', errors='replace').read()
    lines = join_open_parens(strip_comments(raw))
    errs, warns = [], []
    for m in re.finditer(r'defineArray\((\w+)\[\w*\]\s*,\s*(\w+)\)', '\n'.join(lines)):
        env.arrays[m.group(2)] = m.group(1)
    for m in re.finditer(r'defineVariable\((\w+)\s*,\s*(\w+)\)', '\n'.join(lines)):
        env.vars[m.group(2)] = m.group(1)
    for m in re.finditer(r'defineFunction\((\w+)\s*,\s*(\w+)((?:\s*,\s*\w+:\w+)*)\)', '\n'.join(lines)):
        env.funcs[m.group(1)] = (m.group(2), [p.split(':')[0].strip() for p in m.group(3).split(',') if ':' in p])
    # operators
    van = ''
    for f in glob.glob(GAME + '/scenarios/**/*.txt', recursive=True):
        if 'spacerace' in f or 'yearzero' in f:
            continue
        van += re.sub(r'"[^"\n]*"', '"S"', open(f, encoding='utf-8', errors='replace').read())
    ops = lambda s: set(re.findall(r'[<>=!?&|%^+\-*/]{1,2}', re.sub(r'"[^"\n]*"', '"S"', s)))
    extra = ops('\n'.join(lines)) - ops(van)
    if extra:
        errs.append('operators vanilla never uses: %s' % sorted(extra))
    # functions: bodies, endings, params
    cur, ret, depth, local, last, start = None, None, 0, {}, None, 0
    prev_closed_if = False
    for n, l in enumerate(lines, 1):
        s = l.strip()
        m = re.match(r'defineFunction\((\w+)\s*,\s*(\w+)(.*)\)', s)
        if m:
            cur, ret, start = m.group(1), m.group(2), n
            local = {p.split(':')[1].strip(): p.split(':')[0].strip() for p in m.group(3).split(',') if ':' in p}
            depth, last = 0, None
            continue
        if cur:
            depth += s.count('{') - s.count('}')
            if s and s not in ('{', '}'):
                last = s
            if depth == 0 and '}' in s:
                if cur != 'main':
                    want = 'returnVoid()' if ret == 'void' else 'return('
                    if not last or not last.startswith(want):
                        errs.append('line %d: %s (%s) does not end with %s...' % (n, cur, ret, want))
                cur = None
        # string contents masked (same length), so words and brackets inside texts are not read as code
        ms = re.sub(r'"[^"]*"', lambda q: '"' + 'S' * (len(q.group()) - 2) + '"', s)
        # calls
        for cm in re.finditer(r'(?:(\w+)\.)?(\w+)\s*\(', ms):
            obj, name = cm.group(1), cm.group(2)
            if name in ('if', 'elseif', 'else', 'for', 'while', 'return', 'returnVoid', 'defineVariable', 'defineArray',
                        'defineFunction', 'include', 'Include', 'InitConstants'):
                continue
            depth2, j = 0, cm.end() - 1
            for j in range(cm.end() - 1, len(ms)):
                if ms[j] == '(':
                    depth2 += 1
                elif ms[j] == ')':
                    depth2 -= 1
                    if depth2 == 0:
                        break
            args = split_args(s[cm.end():j])
            if obj:
                st = local.get(obj) or env.vars.get(obj)
                sig = env.sinstr.get((st, name))
                if sig is None:
                    errs.append('line %d: %s.%s: no such struct instruction on %s' % (n, obj, name, st))
                    continue
            elif name in env.instr:
                sig = env.instr[name]
            elif name in env.funcs:
                sig = env.funcs[name][1]
            else:
                errs.append('line %d: unknown function %s' % (n, name))
                continue
            if len(args) != len(sig):
                errs.append('line %d: %s takes %d argument(s), given %d' % (n, name, len(sig), len(args)))
                continue
            for a, t in zip(args, sig):
                at = expr_type(a, env, local)
                if t == 'void':
                    continue
                if at.startswith('?'):
                    errs.append('line %d: %s: cannot type argument %r' % (n, name, a))
                    continue
                if at != t and not (t == 'char[]' and at == 'string'):
                    errs.append('line %d: %s: argument %r is %s, expected %s' % (n, name, a, at, t))
        # fields
        for fm in re.finditer(r'\b(\w+)\.([A-Za-z_]\w*)\b(?!\s*\()', ms):
            st = local.get(fm.group(1)) or env.vars.get(fm.group(1))
            if st in env.fields and fm.group(2) not in env.fields[st]:
                errs.append('line %d: %s has no field %s' % (n, st, fm.group(2)))
        # assignments
        am = re.match(r'(\w+)\s*=\s*([^=].*?);?$', s)
        if am and not s.startswith(('for', 'if', 'define')):
            lt = local.get(am.group(1)) or env.vars.get(am.group(1))
            rt = expr_type(am.group(2).rstrip(';'), env, local)
            if lt in ('int', 'char') and rt == 'float':
                warns.append('line %d: %s (%s) = float (vanilla does this too; the compiler only warns): %s' % (n, am.group(1), lt, s))
        # else without if
        if re.match(r'(else|elseif)\s*\(', s) and not prev_closed_if:
            errs.append('line %d: else without a preceding if block' % n)
        if s:
            prev_closed_if = s == '}' or s.startswith('}')
    return errs, warns


if __name__ == '__main__':
    env = Env()
    bad = 0
    for p in sys.argv[1:]:
        errs, warns = check(p, env)
        for e in errs:
            print('%s: %s' % (p, e))
        for w in warns:
            print('%s: warning: %s' % (p, w))
        print('%s: %d problem(s)' % (p, len(errs)))
        bad += len(errs)
    sys.exit(1 if bad else 0)
