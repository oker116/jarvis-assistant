"""
system_control.py
------------------
طبقة تنفيذ أوامر آمنة لجارفيس.
أي أمر بيوصل هنا يتفحص أولاً ضد قائمة أنماط خطيرة معروفة
(فورمات، مسح جذري، أوامر تدمير القرص، إلخ) وتُرفض تلقائياً
قبل التنفيذ، بغض النظر عن مصدر الطلب.
"""

import os
import re
import time
import logging
import subprocess

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "system_control.log")

logger = logging.getLogger("jarvis.system_control")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/\s*($|[^a-zA-Z0-9_./])",
    r"rm\s+-rf\s+/\*",
    r"rm\s+-rf\s+~\s*($|/)",
    r"mkfs(\.\w+)?\s+/dev/",
    r"dd\s+.*of=/dev/(sd|nvme|hd|vd)",
    r">\s*/dev/(sd|nvme|hd|vd)\w*",
    r"fdisk\s+/dev/",
    r"parted\s+/dev/",
    r"wipefs",
    r"shred\s+.*\s+/dev/",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",
    r"chmod\s+-R\s+000\s+/",
    r"chown\s+-R\s+.*\s+/\s*$",
    r">\s*/etc/passwd",
    r">\s*/etc/shadow",
    r"userdel\s+-r\s+root",
    r"passwd\s+root",
    r"format\s+[a-zA-Z]:",
    r"diskpart",
    r"reboot\s*-f",
    r"shutdown\s+.*-h\s+now\s+.*--force",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


def is_dangerous(command: str) -> bool:
    stripped = command.strip()
    for pattern in COMPILED_PATTERNS:
        if pattern.search(stripped):
            return True
    return False


def run_command(command: str, timeout: int = 60) -> dict:
    if not command or not command.strip():
        return {"ok": False, "blocked": False, "output": "أمر فارغ."}

    if is_dangerous(command):
        logger.warning("[BLOCKED] Dangerous command rejected: %s", command)
        return {
            "ok": False,
            "blocked": True,
            "output": (
                "تم رفض هذا الأمر لأنه قد يسبب ضرراً دائماً "
                "(فورمات / مسح جذري / كتابة مباشرة على القرص)."
            )
        }

    logger.info("[EXEC] %s", command)
    start = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration = round(time.time() - start, 2)
        logger.info(
            "[EXEC DONE] return_code=%s duration=%ss",
            result.returncode, duration
        )
        output = (result.stdout or "") + (result.stderr or "")
        return {
            "ok": result.returncode == 0,
            "blocked": False,
            "output": output.strip(),
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        logger.error("[EXEC TIMEOUT] %s", command)
        return {
            "ok": False,
            "blocked": False,
            "output": f"انتهت مهلة التنفيذ ({timeout} ثانية)."
        }
    except Exception as error:
        logger.error("[EXEC ERROR] %s -> %s", command, error)
        return {"ok": False, "blocked": False, "output": str(error)}


if __name__ == "__main__":
    test_commands = [
        "ls -la",
        "rm -rf /",
        "mkfs.ext4 /dev/sda1",
        "echo hello world",
    ]
    for cmd in test_commands:
        print(f"\n>>> {cmd}")
        print(run_command(cmd))
