"""
screen_watch.py
----------------
مراقب خفيف لعنوان النافذة النشطة (الطبقة الأولى - Tier 1).
لا يأخذ أي لقطات شاشة ولا محتوى فعلي - عنوان النافذة بس.
لما يكتشف بحث أو فيديو، يخزنه في الذاكرة طويلة المدى ويظهر
نافذة اقتراح صغيرة أنيقة (مش إشعار نظام جامد) في ركن الشاشة.
"""

import os
import re
import sys
import json
import time
import subprocess
import threading
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

DATA_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(DATA_DIR, "screen_activity.json")

POLL_INTERVAL_SECONDS = 8
NUDGE_COOLDOWN_SECONDS = 90
POPUP_LIFETIME_SECONDS = 9

INTERESTING_KEYWORDS = [
    "error", "exception", "traceback", "stack overflow",
    "خطأ", "nmap", "wireshark", "burp",
]

SEARCH_PATTERNS = [
    re.compile(r"^(.+?)\s+[-–]\s+Google Search", re.IGNORECASE),
    re.compile(r"^(.+?)\s+[-–]\s+بحث Google", re.IGNORECASE),
    re.compile(r"^(.+?)\s+[-–]\s+Bing", re.IGNORECASE),
    re.compile(r"^(.+?)\s+[-–]\s+DuckDuckGo", re.IGNORECASE),
]

YOUTUBE_PATTERN = re.compile(r"^(.+?)\s+[-–]\s+YouTube", re.IGNORECASE)


def load_css():
    css = b"""
    .jarvis-popup {
        background: #060a08;
        border: 1px solid #39ff6a;
        border-radius: 10px;
        box-shadow: 0 0 14px 2px rgba(57, 255, 106, 0.35);
    }
    .popup-title {
        color: #39ff6a;
        font-family: monospace;
        font-size: 13px;
        font-weight: bold;
        text-shadow: 0 0 6px rgba(57, 255, 106, 0.6);
    }
    .popup-body {
        color: #8fe388;
        font-family: monospace;
        font-size: 12px;
    }
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def show_suggestion_popup(title, message):
    def build():
        win = Gtk.Window(type=Gtk.WindowType.POPUP)
        win.set_decorated(False)
        win.set_skip_taskbar_hint(True)
        win.set_skip_pager_hint(True)
        win.set_keep_above(True)
        win.set_default_size(340, -1)
        win.get_style_context().add_class("jarvis-popup")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(16)
        box.set_margin_end(16)

        header = Gtk.Label(label="💡  " + title)
        header.set_xalign(0)
        header.set_line_wrap(True)
        header.get_style_context().add_class("popup-title")

        body = Gtk.Label(label=message)
        body.set_xalign(0)
        body.set_line_wrap(True)
        body.set_max_width_chars(42)
        body.get_style_context().add_class("popup-body")

        box.pack_start(header, False, False, 0)
        box.pack_start(body, False, False, 0)
        win.add(box)

        win.show_all()

        screen = win.get_screen()
        width = screen.get_width()
        height = screen.get_height()
        win_width = win.get_allocated_width() or 340
        win_height = win.get_allocated_height() or 90
        win.move(width - win_width - 24, height - win_height - 60)

        def close_popup():
            win.destroy()
            return False

        GLib.timeout_add_seconds(POPUP_LIFETIME_SECONDS, close_popup)
        return False

    GLib.idle_add(build)


def get_active_window_title():
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def extract_search_query(title):
    for pattern in SEARCH_PATTERNS:
        match = pattern.match(title)
        if match:
            return match.group(1).strip()
    return None


def extract_video_title(title):
    match = YOUTUBE_PATTERN.match(title)
    if match:
        return match.group(1).strip()
    return None


class ScreenWatcher:
    def __init__(self):
        self.last_title = None
        self.last_nudge_time = 0
        self.active = True
        self.log = self._load_log()
        self.brain = None

        self.icon = Gtk.StatusIcon()
        self.icon.set_from_icon_name("view-reveal-symbolic")
        self.icon.set_tooltip_text("JARVIS - مراقبة خفيفة نشطة")
        self.icon.connect("popup-menu", self.show_menu)

        show_suggestion_popup("JARVIS", "بدأت المراقبة الخفيفة.")

        GLib.timeout_add_seconds(POLL_INTERVAL_SECONDS, self.poll)

    def _get_brain(self):
        if self.brain is None:
            from core.brain import JarvisBrain
            self.brain = JarvisBrain()
        return self.brain

    def _load_log(self):
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_log(self):
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.log[-500:], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def poll(self):
        if not self.active:
            return True

        title = get_active_window_title()
        if title and title != self.last_title:
            self.last_title = title
            self.log.append({"title": title, "timestamp": time.time()})
            self._save_log()
            self.handle_title(title)

        return True

    def handle_title(self, title):
        now = time.time()
        if now - self.last_nudge_time < NUDGE_COOLDOWN_SECONDS:
            return

        query = extract_search_query(title)
        if query and len(query) > 2:
            self.last_nudge_time = now
            self.handle_search(query)
            return

        video = extract_video_title(title)
        if video and len(video) > 2:
            self.last_nudge_time = now
            self.handle_video(video)
            return

        lowered = title.lower()
        for keyword in INTERESTING_KEYWORDS:
            if keyword.lower() in lowered:
                self.last_nudge_time = now
                show_suggestion_popup("لاحظت نشاطاً", title)
                break

    def handle_search(self, query):
        def worker():
            try:
                brain = self._get_brain()
                brain.memory._add_long_term_memory(
                    f"بحث المستخدم عن: {query}", "search_history"
                )
                suggestion = brain.suggest_resource(query)
                if suggestion:
                    show_suggestion_popup(query, suggestion)
            except Exception as error:
                print("[SCREEN_WATCH] search handling failed:", error)

        threading.Thread(target=worker, daemon=True).start()

    def handle_video(self, video_title):
        def worker():
            try:
                brain = self._get_brain()
                brain.memory._add_long_term_memory(
                    f"شاهد المستخدم فيديو بعنوان: {video_title}", "watch_history"
                )
            except Exception as error:
                print("[SCREEN_WATCH] video handling failed:", error)

        threading.Thread(target=worker, daemon=True).start()

    def show_menu(self, icon, button, activate_time):
        menu = Gtk.Menu()

        status_item = Gtk.MenuItem(
            label=("الحالة: نشط ●" if self.active else "الحالة: متوقف ○")
        )
        status_item.set_sensitive(False)
        menu.append(status_item)

        menu.append(Gtk.SeparatorMenuItem())

        toggle_item = Gtk.MenuItem(
            label=("إيقاف المراقبة" if self.active else "تشغيل المراقبة")
        )
        toggle_item.connect("activate", self.toggle)
        menu.append(toggle_item)

        quit_item = Gtk.MenuItem(label="إغلاق نهائي")
        quit_item.connect("activate", lambda w: Gtk.main_quit())
        menu.append(quit_item)

        menu.show_all()
        menu.popup(None, None, None, self.icon, button, activate_time)

    def toggle(self, widget):
        self.active = not self.active
        self.icon.set_tooltip_text(
            "JARVIS - مراقبة خفيفة نشطة" if self.active
            else "JARVIS - المراقبة متوقفة"
        )
        show_suggestion_popup(
            "JARVIS",
            "استُأنفت المراقبة." if self.active else "تم إيقاف المراقبة مؤقتاً."
        )


def main():
    load_css()
    ScreenWatcher()
    Gtk.main()


if __name__ == "__main__":
    main()
