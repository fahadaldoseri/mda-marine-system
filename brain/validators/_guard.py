"""حارس الانهيار الموحّد لكل مدققات النظام — ك-133.

قرار صاحب القرار (2026-10-23): لا تُستدلّ حادثة الانهيار من نصّ المخرج، بل من رمز خروج
مخصّص. كل مدقق يمرّ عبر `run(main)`، فأي خطأ غير متوقّع — ولو بلا نص — يخرج بالرمز 70،
وبوابة التسليم تمنع عند 70. بهذا لا يتحوّل انهيار مدقق إلى «تحذير» يمرّ صامتًا.

الاستعمال في نهاية كل مدقق:
    if __name__ == "__main__":
        from _guard import run      # أو: from validators._guard import run
        run(main)

تنبيه: إن عرّف المدقق دالة باسم run في الملف نفسه، فاستورد الحارس باسم بديل
(from _guard import run as guard_run) لتفادي تعارض الاسم — وهو عطل مُسجّل ك-389.
"""
from __future__ import annotations

import sys
import traceback

CRASH_RC = 70  # رمز الانهيار المعتمد — يمنع التسليم في tools/final_gate.sh


def guard(main) -> int:
    """يشغّل main ويعيد رمز خروج معتمدًا: نتيجة المدقق أو رمز الانهيار 70."""
    try:
        rc = main()
        return 0 if rc is None else int(rc)
    except SystemExit as e:                      # مدقق أنهى نفسه صراحةً
        code = e.code
        return 0 if code is None else (code if isinstance(code, int) else 1)
    except KeyboardInterrupt:
        print(f"توقّف المدقق بطلب المستخدم (رمز {CRASH_RC})", file=sys.stderr)
        return CRASH_RC
    except BaseException as e:                   # أي انهيار آخر — بلا ابتلاع
        print(f"انهيار المدقق (رمز {CRASH_RC}): {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
        return CRASH_RC


def run(main) -> None:
    """نقطة الدخول: ينهي العملية برمز معتمد (نتيجة المدقق أو 70 عند الانهيار)."""
    sys.exit(guard(main))
