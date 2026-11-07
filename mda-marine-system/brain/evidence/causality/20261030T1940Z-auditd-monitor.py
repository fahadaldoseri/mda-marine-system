#!/usr/bin/env python3
import datetime as dt
import hashlib
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

OUTDIR = Path(sys.argv[1])
DURATION = int(sys.argv[2]) if len(sys.argv) > 2 else 2700
OUTDIR.mkdir(parents=True, exist_ok=True)
RAW = OUTDIR / "20261030T1940Z-auditd-window-ausearch.log"
CULPRIT = OUTDIR / "20261030T1940Z-culprit.md"
META = OUTDIR / "20261030T1940Z-auditd-monitor-runtime.log"
TRACKED = [
    Path('/home/ubuntu/skills/marine-news-brain/SKILL.md'),
    Path('/home/ubuntu/skills/military-arabic-editing/SKILL.md'),
    Path('/home/ubuntu/skills/military-arabic-editing/references/ambiguity-map.md'),
    Path('/home/ubuntu/skills/superpowers-method/SKILL.md'),
]
start = time.time()
seen_blocks = set()
last_full = ''
stop = False

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode, p.stdout
    except Exception as e:
        return 99, f'{type(e).__name__}: {e}\n'

def safe_read(path, binary=False, limit=4096):
    try:
        data = Path(path).read_bytes() if binary else Path(path).read_text(errors='replace').encode()
        return data[:limit]
    except Exception as e:
        return f'<unavailable: {type(e).__name__}: {e}>'.encode()

def stat_file(path):
    try:
        st = path.stat()
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        lines = len(path.read_text(errors='replace').splitlines())
        return {'exists': True, 'size': st.st_size, 'mtime': st.st_mtime_ns, 'sha256': h, 'lines': lines}
    except FileNotFoundError:
        return {'exists': False}
    except Exception as e:
        return {'error': f'{type(e).__name__}: {e}'}

def proc_chain(pid):
    rows = []
    seen = set()
    cur = int(pid) if str(pid).isdigit() else None
    while cur and cur > 1 and cur not in seen and len(rows) < 12:
        seen.add(cur)
        row = {'pid': cur}
        try:
            raw = Path(f'/proc/{cur}/stat').read_text()
            close = raw.rfind(')')
            fields = raw[close+2:].split()
            row['ppid'] = int(fields[1]) if len(fields) > 1 else None
        except Exception as e:
            row['error'] = f'{type(e).__name__}: {e}'
            rows.append(row)
            break
        try:
            row['cmdline'] = Path(f'/proc/{cur}/cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
        except Exception:
            row['cmdline'] = '<unavailable>'
        try:
            row['exe'] = os.readlink(f'/proc/{cur}/exe')
        except Exception:
            row['exe'] = '<unavailable>'
        try:
            row['cwd'] = os.readlink(f'/proc/{cur}/cwd')
        except Exception:
            row['cwd'] = '<unavailable>'
        try:
            env = Path(f'/proc/{cur}/environ').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            row['environ'] = env[:1000]
        except Exception:
            row['environ'] = '<unavailable>'
        rows.append(row)
        cur = row.get('ppid')
    return rows

def parse_blocks(text):
    return [b.strip() for b in re.split(r'(?m)^----\s*$', text) if b.strip()]

def block_relevant(block):
    return '/home/ubuntu/skills' in block

def extract(block, key):
    m = re.search(r'\b' + re.escape(key) + r'=(?:"([^"]*)"|(\S+))', block)
    return (m.group(1) if m and m.group(1) is not None else m.group(2)) if m else None

def write_culprit(block):
    pid = extract(block, 'pid')
    ppid = extract(block, 'ppid')
    comm = extract(block, 'comm')
    exe = extract(block, 'exe')
    names = re.findall(r'\bname=(?:"([^"]*)"|(\S+))', block)
    paths = [a or b for a,b in names]
    with CULPRIT.open('a', encoding='utf-8') as f:
        f.write(f'\n## حدث auditd التقط في {now()}\n\n')
        f.write(f'- PID: `{pid or "غير موجود في السجل"}`\n')
        f.write(f'- PPID: `{ppid or "غير موجود في السجل"}`\n')
        f.write(f'- comm: `{comm or "غير موجود في السجل"}`\n')
        f.write(f'- exe من سجل auditd: `{exe or "غير موجود في السجل"}`\n')
        f.write(f'- المسار/المسارات المتأثرة: `{paths}`\n\n')
        f.write('### سجل auditd الخام\n\n```text\n' + block + '\n```\n\n')
        if pid and pid.isdigit():
            rows = proc_chain(pid)
            f.write('### سلسلة العملية وقت الالتقاط\n\n')
            for row in rows:
                f.write(f"- PID {row.get('pid')} PPID {row.get('ppid')} exe `{row.get('exe')}` cwd `{row.get('cwd')}` cmdline `{row.get('cmdline')}`\n")
                f.write(f"  environ المختصر: `{row.get('environ','')}`\n")
            if rows:
                f.write(f"\n`readlink -f /proc/{pid}/exe` وقت الالتقاط: `{rows[0].get('exe')}`\n")
                f.write(f"`/proc/{pid}/cgroup` وقت الالتقاط:\n\n```text\n{safe_read(f'/proc/{pid}/cgroup').decode(errors='replace')}\n```\n")
        f.write('\n### قياسات الملفات الحاكمة عند الالتقاط\n\n')
        for path in TRACKED:
            f.write(f'- `{path}`: `{stat_file(path)}`\n')
        f.write('\n')

with META.open('w', encoding='utf-8') as m:
    m.write(f'start_utc={now()}\n')
    m.write(f'duration_seconds={DURATION}\n')
    m.write(f'monitor_pid={os.getpid()}\n')
    m.write(f'cwd={os.getcwd()}\n')
    m.write('command=' + shlex.join(sys.argv) + '\n')
    m.write('watch=/home/ubuntu/skills -p wa -k skills_write\n')
    m.write('tool=auditd/auditctl/ausearch\n')

with RAW.open('w', encoding='utf-8') as raw:
    raw.write(f'# auditd window start {now()}\n')

while not stop and time.time() - start < DURATION:
    rc, out = run(['sudo', '-n', 'ausearch', '-k', 'skills_write', '-i'], timeout=30)
    if out != last_full:
        last_full = out
        with RAW.open('a', encoding='utf-8') as raw:
            raw.write(f'\n### poll_utc={now()} ausearch_rc={rc}\n{out}\n')
        for block in parse_blocks(out):
            if block_relevant(block):
                digest = hashlib.sha256(block.encode()).hexdigest()
                if digest not in seen_blocks:
                    seen_blocks.add(digest)
                    write_culprit(block)
    time.sleep(2)

rc, out = run(['sudo', '-n', 'ausearch', '-k', 'skills_write', '-i'], timeout=60)
with RAW.open('a', encoding='utf-8') as raw:
    raw.write(f'\n### final_poll_utc={now()} ausearch_rc={rc}\n{out}\n')
with META.open('a', encoding='utf-8') as m:
    m.write(f'end_utc={now()}\n')
    m.write(f'elapsed_seconds={time.time()-start:.3f}\n')
    m.write(f'events_with_skill_path={len(seen_blocks)}\n')
    m.write(f'final_ausearch_rc={rc}\n')
