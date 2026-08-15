import os
import sys
import math
import random
import threading
import subprocess
import time

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango


ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.brain import JarvisBrain


class Orb(Gtk.DrawingArea):

    def __init__(self):
        super().__init__()

        self.phase = 0.0
        self.active = False

        self.set_size_request(500, 300)
        self.connect("draw", self.draw)

        self.nodes = []

        random.seed(7)

        # Network sphere
        for _ in range(110):
            theta = random.uniform(0, math.pi * 2)
            phi = random.uniform(-math.pi / 2, math.pi / 2)

            self.nodes.append(
                (
                    theta,
                    phi,
                    random.uniform(0.7, 1.0),
                    random.uniform(0.4, 1.0)
                )
            )

        GLib.timeout_add(30, self.animate)

    def animate(self):

        self.phase += 0.025
        self.queue_draw()

        return True

    def draw(self, widget, cr):

        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        cx = width / 2
        cy = height / 2 - 5

        # Background
        cr.set_source_rgb(
            0.015,
            0.035,
            0.055
        )

        cr.rectangle(
            0,
            0,
            width,
            height
        )

        cr.fill()

        # Grid floor
        for r in range(35, 250, 28):

            alpha = max(
                0.02,
                0.12 - r / 3000
            )

            cr.set_source_rgba(
                0.0,
                0.65,
                0.95,
                alpha
            )

            cr.arc(
                cx,
                cy + 105,
                r,
                0,
                math.pi * 2
            )

            cr.stroke()

        # Orb
        radius = 125

        if self.active:
            radius += math.sin(
                self.phase * 5
            ) * 7

        # Glow
        for i in range(7):

            r = radius + i * 12

            alpha = 0.045 - i * 0.005

            if alpha <= 0:
                continue

            cr.set_source_rgba(
                0.0,
                0.75,
                1.0,
                alpha
            )

            cr.arc(
                cx,
                cy,
                r,
                0,
                math.pi * 2
            )

            cr.stroke()

        projected = []

        rotation = self.phase * 0.45

        for theta, phi, scale, brightness in self.nodes:

            x = math.cos(phi) * math.cos(
                theta + rotation
            )

            y = math.sin(phi)

            z = math.cos(phi) * math.sin(
                theta + rotation
            )

            if z < -0.15:
                continue

            px = cx + x * radius
            py = cy + y * radius

            projected.append(
                (
                    px,
                    py,
                    z,
                    brightness
                )
            )

        # Connections
        for i, a in enumerate(projected):

            for b in projected[i + 1:]:

                dx = a[0] - b[0]
                dy = a[1] - b[1]

                distance = math.sqrt(
                    dx * dx + dy * dy
                )

                if distance < 42:

                    alpha = (
                        0.10
                        * max(a[2], 0)
                        * max(b[2], 0)
                    )

                    cr.set_source_rgba(
                        0.1,
                        0.75,
                        1.0,
                        alpha
                    )

                    cr.move_to(
                        a[0],
                        a[1]
                    )

                    cr.line_to(
                        b[0],
                        b[1]
                    )

                    cr.stroke()

        # Nodes
        for x, y, z, brightness in projected:

            size = 1.4 + z * 2.4

            alpha = (
                0.35
                + z * 0.65
            ) * brightness

            cr.set_source_rgba(
                0.35,
                0.9,
                1.0,
                alpha
            )

            cr.arc(
                x,
                y,
                size,
                0,
                math.pi * 2
            )

            cr.fill()

        # Core
        cr.set_source_rgba(
            0.1,
            0.75,
            1.0,
            0.8
        )

        cr.arc(
            cx,
            cy,
            3,
            0,
            math.pi * 2
        )

        cr.fill()

        # Label
        cr.set_source_rgba(
            0.35,
            0.9,
            1.0,
            0.9
        )

        cr.select_font_face(
            "Sans",
            0,
            1
        )

        cr.set_font_size(18)

        text = "J A R V I S"

        ext = cr.text_extents(text)

        cr.move_to(
            cx - ext.width / 2,
            cy - radius - 30
        )

        cr.show_text(text)

        return False


class JarvisApp(Gtk.Window):

    def __init__(self):

        super().__init__(
            title="JARVIS CORE"
        )

        self.set_default_size(
            1100,
            700
        )

        self.set_position(
            Gtk.WindowPosition.CENTER
        )

        self.set_resizable(True)

        self.processing = False

        self.brain = JarvisBrain()

        self.load_css()
        self.build_ui()

    # =========================================================
    # CSS
    # =========================================================

    def load_css(self):

        css = b"""
        * {
            font-family: Sans;
        }

        window {
            background: #02070c;
            color: #d8f7ff;
        }

        .sidebar {
            background: #030b12;
            border-right: 1px solid #12303e;
        }

        .brand {
            color: #75eaff;
            font-size: 26px;
            font-weight: bold;
            letter-spacing: 8px;
        }

        .small {
            color: #527483;
            font-size: 10px;
            letter-spacing: 2px;
        }

        .nav {
            background: transparent;
            color: #87a9b5;
            border: none;
            padding: 13px;
            border-radius: 8px;
        }

        .nav:hover {
            background: #09202b;
            color: #72eaff;
        }

        .new-chat {
            background: #061925;
            color: #62e8ff;
            border: 1px solid #12627b;
            border-radius: 9px;
            padding: 12px;
        }

        .conversation {
            background: #06131d;
            color: #9bb9c4;
            border-radius: 8px;
            padding: 11px;
        }

        .conversation:hover {
            background: #0b2532;
            color: #7cecff;
        }

        .section {
            color: #4c7180;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 2px;
        }

        .status {
            background: #06131d;
            border: 1px solid #102d3a;
            padding: 12px;
        }

        .status-name {
            color: #a9c7d0;
            font-size: 11px;
        }

        .status-good {
            color: #00e5a0;
            font-size: 10px;
            font-weight: bold;
        }

        .status-ready {
            color: #27cfff;
            font-size: 10px;
            font-weight: bold;
        }

        .topbar {
            background: #030b12;
            border-bottom: 1px solid #12303e;
        }

        .title {
            color: #64e8ff;
            font-size: 19px;
            font-weight: bold;
            letter-spacing: 3px;
        }

        .online {
            color: #00e5a0;
            font-weight: bold;
        }

        .chat-area {
            background: #02070c;
        }

        .jarvis-bubble {
            background: #071621;
            border: 1px solid #123d4e;
            border-radius: 13px;
            padding: 14px;
        }

        .user-bubble {
            background: #0a2030;
            border: 1px solid #17516a;
            border-radius: 13px;
            padding: 14px;
        }

        .sender {
            color: #57e5ff;
            font-size: 10px;
            font-weight: bold;
        }

        .message {
            color: #d5e9ee;
            font-size: 13px;
        }

        entry {
            background: #06131d;
            color: #e5faff;
            border: 1px solid #18526a;
            border-radius: 12px;
            padding: 14px;
            font-size: 13px;
        }

        entry:focus {
            border-color: #42dcff;
        }

        .send {
            background: #073042;
            color: #70eaff;
            border: 1px solid #1e7691;
            border-radius: 11px;
            padding: 13px 20px;
        }

        .send:hover {
            background: #0b4054;
        }

        .mic {
            background: #071a25;
            color: #6deaff;
            border: 1px solid #18516a;
            border-radius: 11px;
            padding: 13px 17px;
        }
        """

        provider = Gtk.CssProvider()

        provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # =========================================================
    # UI
    # =========================================================

    def build_ui(self):

        root = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        self.add(root)

        self.build_sidebar(root)
        self.build_main(root)

    # =========================================================
    # SIDEBAR
    # =========================================================

    def build_sidebar(self, root):

        sidebar = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8
        )

        sidebar.set_size_request(
            275,
            -1
        )

        sidebar.get_style_context().add_class(
            "sidebar"
        )

        root.pack_start(
            sidebar,
            False,
            False,
            0
        )

        brand = Gtk.Label(
            label="J A R V I S"
        )

        brand.get_style_context().add_class(
            "brand"
        )

        sidebar.pack_start(
            brand,
            False,
            False,
            25
        )

        subtitle = Gtk.Label(
            label="PERSONAL AI SYSTEM"
        )

        subtitle.get_style_context().add_class(
            "small"
        )

        sidebar.pack_start(
            subtitle,
            False,
            False,
            0
        )


        section = Gtk.Label(
            label="CONVERSATIONS"
        )

        section.set_xalign(0)

        section.set_margin_start(22)
        section.set_margin_top(15)

        section.get_style_context().add_class(
            "section"
        )

        sidebar.pack_start(
            section,
            False,
            False,
            5
        )

        self.add_conversation(
            sidebar,
            "◯   New Conversation",
            "NOW"
        )

        self.add_conversation(
            sidebar,
            "◯   مشاريع جارفيس",
            "Yesterday"
        )

        self.add_conversation(
            sidebar,
            "◯   تعلم البرمجة",
            "2 days"
        )

        self.add_conversation(
            sidebar,
            "◯   تحليل النظام",
            "3 days"
        )

        sidebar.pack_start(
            Gtk.Separator(
                orientation=Gtk.Orientation.HORIZONTAL
            ),
            False,
            False,
            20
        )

        status_title = Gtk.Label(
            label="SYSTEM STATUS"
        )

        status_title.set_xalign(0)
        status_title.set_margin_start(22)

        status_title.get_style_context().add_class(
            "section"
        )

        sidebar.pack_start(
            status_title,
            False,
            False,
            5
        )

        self.add_status(
            sidebar,
            "AI ENGINE (GEMINI)",
            "ONLINE",
            True
        )

        self.add_status(
            sidebar,
            "LOCAL AI (OLLAMA)",
            "READY",
            False
        )

        self.add_status(
            sidebar,
            "MEMORY",
            "ACTIVE",
            True
        )

        self.add_status(
            sidebar,
            "VOICE SYSTEM",
            "READY",
            False
        )

        spacer = Gtk.Box()

        sidebar.pack_start(
            spacer,
            True,
            True,
            0
        )



    def add_conversation(
        self,
        sidebar,
        name,
        date
    ):

        button = Gtk.Button()

        button.get_style_context().add_class(
            "conversation"
        )

        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        left = Gtk.Label(
            label=name
        )

        left.set_xalign(0)

        date_label = Gtk.Label(
            label=date
        )

        date_label.set_xalign(1)

        box.pack_start(
            left,
            True,
            True,
            0
        )

        box.pack_end(
            date_label,
            False,
            False,
            0
        )

        button.add(box)

        button.set_margin_start(20)
        button.set_margin_end(20)

        sidebar.pack_start(
            button,
            False,
            False,
            2
        )

    def add_status(
        self,
        sidebar,
        name,
        state,
        good
    ):

        row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        row.get_style_context().add_class(
            "status"
        )

        row.set_margin_start(20)
        row.set_margin_end(20)

        label = Gtk.Label(
            label=name
        )

        label.set_xalign(0)

        label.get_style_context().add_class(
            "status-name"
        )

        value = Gtk.Label(
            label="● " + state
        )

        value.set_xalign(1)

        value.get_style_context().add_class(
            "status-good" if good
            else "status-ready"
        )

        row.pack_start(
            label,
            True,
            True,
            0
        )

        row.pack_end(
            value,
            False,
            False,
            0
        )

        sidebar.pack_start(
            row,
            False,
            False,
            1
        )

    # =========================================================
    # MAIN
    # =========================================================

    def build_main(self, root):

        main = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL
        )

        root.pack_start(
            main,
            True,
            True,
            0
        )

        topbar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        topbar.set_size_request(
            -1,
            70
        )

        topbar.get_style_context().add_class(
            "topbar"
        )

        main.pack_start(
            topbar,
            False,
            False,
            0
        )

        title = Gtk.Label(
            label="JARVIS CORE"
        )

        title.set_margin_start(30)

        title.get_style_context().add_class(
            "title"
        )

        topbar.pack_start(
            title,
            False,
            False,
            0
        )

        online = Gtk.Label(
            label="● ONLINE"
        )

        online.get_style_context().add_class(
            "online"
        )

        topbar.pack_end(
            online,
            False,
            False,
            30
        )

        # CHAT SCROLL

        self.scroll = Gtk.ScrolledWindow()

        self.scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )

        self.scroll.get_style_context().add_class(
            "chat-area"
        )

        main.pack_start(
            self.scroll,
            True,
            True,
            0
        )

        self.chat = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )

        self.chat.set_margin_start(35)
        self.chat.set_margin_end(35)
        self.chat.set_margin_top(20)
        self.chat.set_margin_bottom(15)

        self.scroll.add(
            self.chat
        )

        # ORB

        self.orb = Orb()

        self.orb.set_halign(
            Gtk.Align.CENTER
        )

        main.pack_start(
            self.orb,
            False,
            False,
            0
        )

        self.add_message(
            "JARVIS",
            "مرحباً بك. أنا جارفيس، نظام الذكاء الاصطناعي الخاص بك.",
            False
        )

        self.add_message(
            "JARVIS",
            "كيف يمكنني مساعدتك اليوم؟",
            False
        )

        # INPUT

        input_area = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        input_area.set_margin_start(30)
        input_area.set_margin_end(30)
        input_area.set_margin_bottom(25)

        main.pack_start(
            input_area,
            False,
            False,
            0
        )

        mic = Gtk.Button(
            label="🎙"
        )

        mic.get_style_context().add_class(
            "mic"
        )

        mic.connect(
            "clicked",
            self.voice_button
        )

        input_area.pack_start(
            mic,
            False,
            False,
            0
        )

        self.entry = Gtk.Entry()

        self.entry.set_placeholder_text(
            "اكتب رسالتك هنا..."
        )

        self.entry.set_direction(
            Gtk.TextDirection.RTL
        )

        self.entry.connect(
            "activate",
            self.send
        )

        input_area.pack_start(
            self.entry,
            True,
            True,
            0
        )

        send = Gtk.Button(
            label="➤"
        )

        send.get_style_context().add_class(
            "send"
        )

        send.connect(
            "clicked",
            self.send
        )

        input_area.pack_start(
            send,
            False,
            False,
            0
        )

    # =========================================================
    # CHAT
    # =========================================================

    def add_message(
        self,
        sender,
        text,
        user
    ):

        row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        row.set_halign(
            Gtk.Align.END
            if user
            else Gtk.Align.START
        )

        bubble = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL
        )

        bubble.set_size_request(
            520,
            -1
        )

        bubble.get_style_context().add_class(
            "user-bubble"
            if user
            else "jarvis-bubble"
        )

        header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        name = Gtk.Label(
            label=sender
        )

        name.set_xalign(
            0 if user else 1
        )

        name.get_style_context().add_class(
            "sender"
        )

        header.pack_start(
            name,
            True,
            True,
            0
        )

        timestamp = Gtk.Label(
            label=time.strftime("%H:%M")
        )

        timestamp.get_style_context().add_class(
            "small"
        )

        header.pack_end(
            timestamp,
            False,
            False,
            0
        )

        bubble.pack_start(
            header,
            False,
            False,
            4
        )

        message = Gtk.Label(
            label=str(text)
        )

        message.set_line_wrap(True)
        message.set_selectable(True)
        message.set_max_width_chars(70)

        message.set_justify(
            Gtk.Justification.RIGHT
        )

        message.set_direction(
            Gtk.TextDirection.RTL
        )

        message.set_xalign(1)

        message.get_style_context().add_class(
            "message"
        )

        bubble.pack_start(
            message,
            False,
            False,
            0
        )

        row.pack_start(
            bubble,
            False,
            False,
            0
        )

        self.chat.pack_start(
            row,
            False,
            False,
            0
        )

        self.chat.show_all()

        GLib.idle_add(
            self.scroll_bottom
        )

    def scroll_bottom(self):

        adjustment = (
            self.scroll
            .get_vadjustment()
        )

        adjustment.set_value(
            adjustment.get_upper()
        )

        return False

    # =========================================================
    # BRAIN
    # =========================================================

    def send(self, widget):

        if self.processing:
            return

        text = self.entry.get_text().strip()

        if not text:
            return

        self.entry.set_text("")

        self.add_message(
            "YOU",
            text,
            True
        )

        self.processing = True

        self.orb.active = True

        self.orb.queue_draw()

        thread = threading.Thread(
            target=self.ask,
            args=(text,),
            daemon=True
        )

        thread.start()

    def ask(self, text):

        try:

            answer = self.brain.ask(
                text
            )

        except Exception as error:

            answer = (
                "حدث خطأ في JARVIS:\n"
                + str(error)
            )

        GLib.idle_add(
            self.receive,
            answer
        )

    def receive(self, answer):

        self.add_message(
            "JARVIS",
            answer,
            False
        )

        self.processing = False
        self.orb.active = False
        self.orb.queue_draw()

        self.speak(answer)

        return False

    # =========================================================
    # VOICE
    # =========================================================

    def voice_button(self, widget):

        # الصوت الحالي للإخراج.
        # هنضيف speech-to-text بعدين.
        threading.Thread(
            target=self.say,
            args=("أنا أستمع إليك.",),
            daemon=True
        ).start()

    def speak(self, text):

        threading.Thread(
            target=self.say,
            args=(text,),
            daemon=True
        ).start()

    def say(self, text):

        try:

            subprocess.run(
                [
                    "espeak-ng",
                    "-v",
                    "ar",
                    "-s",
                    "145",
                    str(text)
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        except Exception:
            pass

    # =========================================================
    # NEW CHAT
    # =========================================================

    def new_chat(self, widget):

        for child in self.chat.get_children():

            self.chat.remove(child)

        self.add_message(
            "JARVIS",
            "تم إنشاء محادثة جديدة. كيف يمكنني مساعدتك؟",
            False
        )


def main():

    app = JarvisApp()

    app.connect(
        "destroy",
        Gtk.main_quit
    )

    app.show_all()

    Gtk.main()


if __name__ == "__main__":
    main()
