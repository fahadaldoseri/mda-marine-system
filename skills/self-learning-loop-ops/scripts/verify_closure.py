#!/usr/bin/env python3
"""تفويض إلى بوابة الإغلاق في المشروع (فشل مغلق). لا منطق محلي يسمح بنجاح صامت."""
import subprocess, sys
BRAIN = sys.argv[1] if len(sys.argv) > 1 else '/home/ubuntu/brain-marine-news'
raise SystemExit(subprocess.run([sys.executable, f'{BRAIN}/validators/check_closure.py', '--brain', BRAIN]).returncode)
