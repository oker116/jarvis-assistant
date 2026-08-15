import os
from dotenv import load_dotenv
load_dotenv()

import json
import logging
import re
import sys
import time
import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen3:1.7b"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "llama-3.1-8b"

RETRY_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 2

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from memory.memory import JarvisMemory
from knowledge.knowledge import KnowledgeEngine
from tools.system_control import run_command

LOG_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "jarvis.log")

logger = logging.getLogger("jarvis.brain")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


COMMAND_PATTERN = re.compile(r"^RUN_COMMAND:\s*(.+)$", re.MULTILINE)
MAX_OUTPUT_CHARS = 2000


class ProviderError(Exception):
    pass


class RateLimitError(Exception):
    pass


class ConnectionFailure(Exception):
    pass


class JarvisBrain:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.cerebras_api_key = os.getenv("CEREBRAS_API_KEY")
        self.api_key = os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            logger.warning("GEMINI_API_KEY missing - local Ollama fallback enabled")

        self.url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/gemini-3.5-flash:generateContent"
        )

        self.memory = JarvisMemory()
        self.knowledge = KnowledgeEngine()

        self.stats = {
            "gemini": {"success": 0, "failure": 0},
            "groq": {"success": 0, "failure": 0},
            "cerebras": {"success": 0, "failure": 0},
            "ollama": {"success": 0, "failure": 0},
        }

        self.system_prompt = (
            "You are JARVIS, a personal AI assistant running on the "
            "user's own Kali Linux machine. "
            "You are intelligent, precise, analytical and helpful. "
            "If the user speaks Arabic, answer in Arabic. "
            "If the user speaks English, answer in English. "
            "Be natural and conversational. "
            "Use the conversation memory when it is relevant. "
            "Do not claim to have performed an action unless "
            "the system actually performed it.\n\n"
            "TOOL USE - RUNNING SYSTEM COMMANDS:\n"
            "If, and only if, completing the user's request requires "
            "running a real terminal command on their machine "
            "(for example: listing files, checking system info, "
            "running a network scan tool, checking a process), "
            "output the command on its own line using EXACTLY this "
            "format, with nothing else on that line:\n"
            "RUN_COMMAND: <the exact shell command>\n\n"
            "Rules:\n"
            "- Only include ONE RUN_COMMAND line per response.\n"
            "- Only request a command when it is actually necessary "
            "to answer the user - do not run commands speculatively.\n"
            "- The command will be checked against a safety blocklist "
            "and may be rejected if it is destructive "
            "(formatting, wiping disks, etc). Never try to bypass this.\n"
            "- You may write a short explanation before the "
            "RUN_COMMAND line describing what you are about to do."
        )

    def print_stats(self):
        logger.info("===== ROUTER STATS =====")
        for provider, counters in self.stats.items():
            logger.info(
                "%s -> success: %s, failure: %s",
                provider.upper(), counters["success"], counters["failure"]
            )

    def _record(self, provider, ok):
        key = "success" if ok else "failure"
        self.stats[provider][key] += 1

    def _handle_command_directives(self, answer):
        match = COMMAND_PATTERN.search(answer)
        if not match:
            return answer

        command = match.group(1).strip()
        explanation = answer[:match.start()].strip()

        logger.info("[TOOL] Command requested by model: %s", command)
        result = run_command(command)

        if result.get("blocked"):
            summary = (
                f"⚠️ تم رفض تنفيذ الأمر التالي لأنه يعتبر خطيراً:\n"
                f"`{command}`\n\n{result.get('output')}"
            )
        else:
            output = (result.get("output") or "").strip()
            if len(output) > MAX_OUTPUT_CHARS:
                output = output[:MAX_OUTPUT_CHARS] + "\n... (تم اقتصاص الناتج)"
            status = "نجح ✅" if result.get("ok") else "فشل ❌"
            summary = (
                f"🖥️ تم تنفيذ الأمر:\n`{command}`\n\n"
                f"الحالة: {status}\n\n"
                f"الناتج:\n```\n{output if output else '(لا يوجد ناتج)'}\n```"
            )

        if explanation:
            return explanation + "\n\n" + summary
        return summary

    def build_contents(self, user_text):
        contents = []

        knowledge_context = self.knowledge.context(user_text, limit=5)
        if knowledge_context:
            contents.append({
                "role": "user",
                "parts": [{
                    "text": "JARVIS KNOWLEDGE BASE:\n\n" + knowledge_context +
                            "\n\nUse this knowledge when relevant."
                }]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": self.system_prompt}]
        })

        long_term_memory = self.memory.get_context(user_text, limit=10)
        if long_term_memory:
            contents.append({
                "role": "user",
                "parts": [{
                    "text": "JARVIS LONG-TERM MEMORY:\n\n" + long_term_memory +
                            "\n\nUse these memories when relevant. "
                            "Do not invent information that is not present."
                }]
            })

        recent = self.memory.get_recent(limit=20)
        for item in recent:
            role = item.get("role")
            text = item.get("text", "")
            if role not in ["user", "model"]:
                continue
            if not text:
                continue
            contents.append({
                "role": role,
                "parts": [{"text": text}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": user_text}]
        })

        return contents

    def extract_memory(self, user_text):
        prompt = f"""
استخرج من رسالة المستخدم المعلومات الشخصية المهمة التي تستحق الذاكرة طويلة المدى.
لا تحفظ التحيات أو الأسئلة أو الكلام المؤقت.
إذا لا توجد معلومة مهمة اكتب NO_MEMORY.

الرسالة:
{user_text}
"""
        try:
            response = requests.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=15
            )
            raw = response.json().get("response", "").strip()
            if raw and raw != "NO_MEMORY":
                self.memory._add_long_term_memory(raw, "automatic")
                self.memory.save()
                logger.info("[MEMORY SAVED] %s", raw)
        except Exception as error:
            logger.debug("[MEMORY SKIPPED] %s", error)

    def _post_with_retry(self, url, **kwargs):
        last_error = None
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = requests.post(url, **kwargs)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as error:
                last_error = error
                logger.warning(
                    "Connection issue (attempt %s/%s): %s",
                    attempt, RETRY_ATTEMPTS, error
                )
                time.sleep(RETRY_DELAY_SECONDS)
                continue

            if response.status_code == 429:
                raise RateLimitError(f"Rate limit hit: {response.text[:200]}")

            if response.status_code >= 400:
                raise ProviderError(f"HTTP {response.status_code}: {response.text[:200]}")

            return response

        raise ConnectionFailure(str(last_error))

    def ask_groq(self, user_text, context=""):
        try:
            response = self._post_with_retry(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": self.system_prompt + "\n\nJARVIS LONG-TERM MEMORY:\n" + context},
                        {"role": "user", "content": user_text}
                    ],
                    "temperature": 0.7
                },
                timeout=60
            )
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise ProviderError("Groq returned no choices")
            answer = choices[0].get("message", {}).get("content", "").strip()
            if not answer:
                raise ProviderError("Groq returned an empty answer")
            self._record("groq", True)
            return answer

        except RateLimitError as error:
            logger.info("[ROUTER] Groq rate limited: %s", error)
            self._record("groq", False)
            return None
        except (ProviderError, ConnectionFailure) as error:
            logger.warning("[ROUTER] Groq failed: %s", error)
            self._record("groq", False)
            return None
        except Exception as error:
            logger.error("[ROUTER] Groq unexpected error: %s", error)
            self._record("groq", False)
            return None

    def ask_cerebras(self, user_text, context=""):
        try:
            response = self._post_with_retry(
                CEREBRAS_API_URL,
                headers={
                    "Authorization": f"Bearer {self.cerebras_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": CEREBRAS_MODEL,
                    "messages": [
                        {"role": "system", "content": self.system_prompt + "\n\nJARVIS LONG-TERM MEMORY:\n" + context},
                        {"role": "user", "content": user_text}
                    ],
                    "temperature": 0.7
                },
                timeout=60
            )
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise ProviderError("Cerebras returned no choices")
            answer = choices[0].get("message", {}).get("content", "").strip()
            if not answer:
                raise ProviderError("Cerebras returned an empty answer")
            self._record("cerebras", True)
            return answer

        except RateLimitError as error:
            logger.info("[ROUTER] Cerebras rate limited: %s", error)
            self._record("cerebras", False)
            return None
        except (ProviderError, ConnectionFailure) as error:
            logger.warning("[ROUTER] Cerebras failed: %s", error)
            self._record("cerebras", False)
            return None
        except Exception as error:
            logger.error("[ROUTER] Cerebras unexpected error: %s", error)
            self._record("cerebras", False)
            return None

    def ask_ollama(self, user_text, context=""):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": (
                        self.system_prompt +
                        "\n\nJARVIS LONG-TERM MEMORY:\n" + context +
                        "\n\nUSER:\n" + user_text
                    ),
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("response", "").strip()
            if answer:
                self._record("ollama", True)
                return answer
            self._record("ollama", False)
            return "The local AI returned an empty response."
        except requests.exceptions.Timeout:
            logger.error("[ROUTER] Ollama timed out")
            self._record("ollama", False)
            return "The local AI timed out."
        except requests.exceptions.ConnectionError:
            logger.error("[ROUTER] Ollama is not running")
            self._record("ollama", False)
            return "The local AI is not running."
        except Exception as error:
            logger.error("[ROUTER] Ollama failed: %s", error)
            self._record("ollama", False)
            return "The local AI failed."

    def ask(self, user_text):
        user_text = user_text.strip()
        if not user_text:
            return ""

        self.memory.learn_from_text(user_text)
        self.extract_memory(user_text)

        contents = self.build_contents(user_text)
        long_term_memory = self.memory.get_long_term_context(limit=100)

        if self.api_key:
            data = {
                "contents": contents,
                "generationConfig": {"temperature": 0.75, "maxOutputTokens": 2048}
            }
            try:
                response = self._post_with_retry(
                    self.url,
                    params={"key": self.api_key},
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(data),
                    timeout=60
                )
                result = response.json()
                candidates = result.get("candidates", [])
                if candidates:
                    answer = (
                        candidates[0].get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                        .strip()
                    )
                    if answer:
                        logger.info("[ROUTER] Provider: Gemini")
                        self._record("gemini", True)
                        final_answer = self._handle_command_directives(answer)
                        self.memory.add_message("user", user_text)
                        self.memory.add_message("model", final_answer)
                        return final_answer
                raise ProviderError("Gemini returned no usable candidates")

            except RateLimitError as error:
                logger.info("[ROUTER] Gemini rate limited: %s", error)
                self._record("gemini", False)
            except (ProviderError, ConnectionFailure) as error:
                logger.warning("[ROUTER] Gemini failed: %s", error)
                self._record("gemini", False)
            except Exception as error:
                logger.error("[ROUTER] Gemini unexpected error: %s", error)
                self._record("gemini", False)

        if self.groq_api_key:
            logger.info("[ROUTER] Switching to Groq")
            answer = self.ask_groq(user_text, long_term_memory)
            if answer:
                logger.info("[ROUTER] Provider: Groq")
                final_answer = self._handle_command_directives(answer)
                self.memory.add_message("user", user_text)
                self.memory.add_message("model", final_answer)
                return final_answer

        if self.cerebras_api_key:
            logger.info("[ROUTER] Switching to Cerebras")
            answer = self.ask_cerebras(user_text, long_term_memory)
            if answer:
                logger.info("[ROUTER] Provider: Cerebras")
                final_answer = self._handle_command_directives(answer)
                self.memory.add_message("user", user_text)
                self.memory.add_message("model", final_answer)
                return final_answer

        logger.info("[ROUTER] Switching to Ollama")
        answer = self.ask_ollama(user_text, long_term_memory)
        logger.info("[ROUTER] Provider: Ollama")
        final_answer = self._handle_command_directives(answer)
        self.memory.add_message("user", user_text)
        self.memory.add_message("model", final_answer)
        return final_answer


if __name__ == "__main__":
    logger.info("JARVIS BRAIN - Persistent Memory Enabled")
    brain = JarvisBrain()
    while True:
        text = input("YOU > ").strip()
        if not text:
            continue
        if text.lower() in ["exit", "quit"]:
            brain.print_stats()
            break
        answer = brain.ask(text)
        print("")
        print("JARVIS >")
        print(answer)
        print("")
