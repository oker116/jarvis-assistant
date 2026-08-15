import os
import sys
import math
import random
import threading
import subprocess
import time
import json
import shutil
import platform

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

try:
    import psutil
except ImportError:
    psutil = None


ROOT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.brain import JarvisBrain


class CoreView(Gtk.DrawingArea):

    def __init__(self):

        super().__init__()

        self.phase = 0.0
        self.energy = 0.12
        self.target_energy = 0.12

        self.thinking = False
        self.speaking = False

        self.set_size_request(
            300,
            260
        )

        self.connect(
            "draw",
            self.draw
        )

        rng = random.Random(42)

        self.stars = []

        for _ in range(170):

            self.stars.append(
                (
                    rng.uniform(-1.0, 1.0),
                    rng.uniform(-0.8, 0.8),
                    rng.uniform(0.25, 1.0),
                    rng.uniform(0.0, math.pi * 2)
                )
            )

        self.nodes = []

        for _ in range(100):

            theta = rng.uniform(
                0,
                math.pi * 2
            )

            phi = rng.uniform(
                -math.pi / 2,
                math.pi / 2
            )

            self.nodes.append(
                (
                    theta,
                    phi,
                    rng.uniform(
                        0.5,
                        1.0
                    )
                )
            )

        GLib.timeout_add(
            33,
            self.animate
        )

    def set_state(
        self,
        thinking=False,
        speaking=False
    ):

        self.thinking = bool(
            thinking
        )

        self.speaking = bool(
            speaking
        )

        if self.speaking:

            self.target_energy = 0.95

        elif self.thinking:

            self.target_energy = 0.65

        else:

            self.target_energy = 0.12

        self.queue_draw()

    def animate(self):

        if self.speaking:

            speed = 0.022

        elif self.thinking:

            speed = 0.016

        else:

            speed = 0.009

        self.phase += speed

        self.energy += (
            self.target_energy
            - self.energy
        ) * 0.065

        self.queue_draw()

        return True

    def draw(
        self,
        widget,
        cr
    ):

        width = max(
            1,
            widget.get_allocated_width()
        )

        height = max(
            1,
            widget.get_allocated_height()
        )

        cx = width / 2
        cy = height * 0.47

        # Background

        cr.set_source_rgb(
            0.003,
            0.008,
            0.015
        )

        cr.rectangle(
            0,
            0,
            width,
            height
        )

        cr.fill()

        # Stars

        for sx, sy, depth, seed in self.stars:

            x = (
                cx
                + sx
                * width
                * (
                    0.45
                    + depth * 0.20
                )
            )

            y = (
                cy
                + sy
                * height
                * (
                    0.65
                    + depth * 0.20
                )
            )

            twinkle = (
                0.35
                +
                0.65
                *
                abs(
                    math.sin(
                        self.phase
                        * (
                            0.5
                            + depth
                        )
                        + seed
                    )
                )
            )

            size = (
                0.4
                + depth * 1.4
            )

            alpha = (
                0.08
                +
                twinkle
                * depth
                * 0.45
            )

            cr.set_source_rgba(
                0.30,
                0.75,
                0.95,
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

        # Core breathing

        breath = (
            1.0
            +
            0.025
            *
            math.sin(
                self.phase * 1.7
            )
        )

        if self.thinking:

            breath += (
                0.03
                *
                math.sin(
                    self.phase * 3.5
                )
            )

        if self.speaking:

            breath += (
                0.06
                *
                math.sin(
                    self.phase * 7.0
                )
            )

        radius = 82 * breath

        # Glow

        for layer in range(
            8,
            0,
            -1
        ):

            rr = (
                radius
                + layer * 12
            )

            cr.set_source_rgba(
                0.02,
                0.60,
                0.85,
                0.003
                +
                self.energy
                * 0.006
            )

            cr.arc(
                cx,
                cy,
                rr,
                0,
                math.pi * 2
            )

            cr.stroke()

        # Energy shells

        for ring in range(5):

            wobble = (
                6
                *
                self.energy
                *
                math.sin(
                    self.phase * 1.6
                    + ring
                )
            )

            rx = (
                radius
                +
                ring * 25
                +
                wobble
            )

            ry = rx * 0.42

            cr.set_source_rgba(
                0.08,
                0.72,
                0.95,
                0.10
                +
                self.energy
                * 0.06
            )

            cr.save()

            cr.translate(
                cx,
                cy
            )

            cr.rotate(
                0.07
                *
                math.sin(
                    self.phase
                    + ring
                )
            )

            cr.scale(
                1.0,
                ry / max(
                    rx,
                    1
                )
            )

            cr.arc(
                0,
                0,
                rx,
                0,
                math.pi * 2
            )

            cr.restore()

            cr.stroke()

        # Network sphere

        projected = []

        rotation = (
            self.phase
            * 0.27
        )

        for theta, phi, brightness in self.nodes:

            x = (
                math.cos(phi)
                *
                math.cos(
                    theta
                    + rotation
                )
            )

            y = math.sin(phi)

            z = (
                math.cos(phi)
                *
                math.sin(
                    theta
                    + rotation
                )
            )

            if z < -0.10:
                continue

            px = (
                cx
                + x * radius
            )

            py = (
                cy
                + y * radius
            )

            projected.append(
                (
                    px,
                    py,
                    z,
                    brightness
                )
            )

        # Network connections

        for i, a in enumerate(
            projected
        ):

            for b in projected[
                i + 1:
            ]:

                distance = math.hypot(
                    a[0] - b[0],
                    a[1] - b[1]
                )

                if distance < 36:

                    alpha = (
                        0.012
                        +
                        self.energy
                        * 0.07
                    )

                    cr.set_source_rgba(
                        0.18,
                        0.72,
                        0.92,
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

        # Network points

        for x, y, z, brightness in projected:

            size = (
                0.8
                + z * 2.0
            )

            alpha = (
                0.15
                + z * 0.75
            ) * brightness

            cr.set_source_rgba(
                0.45,
                0.88,
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

        # Core glow

        cr.set_source_rgba(
            0.40,
            0.86,
            1.0,
            0.18
            +
            self.energy
            * 0.32
        )

        cr.arc(
            cx,
            cy,
            19
            +
            self.energy * 8,
            0,
            math.pi * 2
        )

        cr.fill()

        cr.set_source_rgba(
            0.95,
            0.99,
            1.0,
            0.95
        )

        cr.arc(
            cx,
            cy,
            6
            +
            self.energy * 2,
            0,
            math.pi * 2
        )

        cr.fill()

        # Speaking pulse bars

        if (
            self.speaking
            or
            self.thinking
        ):

            for i in range(7):

                amp = (
                    3
                    +
                    self.energy
                    * (
                        7
                        + i
                    )
                    *
                    abs(
                        math.sin(
                            self.phase
                            * 4
                            + i
                        )
                    )
                )

                x = (
                    cx
                    - 45
                    +
                    i * 15
                )

                cr.set_source_rgba(
                    0.25,
                    0.82,
                    1.0,
                    0.40
                    +
                    self.energy
                    * 0.35
                )

                cr.rectangle(
                    x,
                    cy
                    + radius
                    + 15
                    - amp,
                    8,
                    amp
                )

                cr.fill()

        return False


class JarvisApp(Gtk.Window):

    def __init__(self):

        super().__init__(
            title="JARVIS"
        )

        self.set_default_size(
            1000,
            718
        )

        self.set_resizable(
            True
        )


        self.processing = False
        self.speaking = False
        self._chat_count = 0

        self.current_view = "chat"

        self.brain = JarvisBrain()

        self.nav_buttons = {}

        self.load_css()
        self.build_ui()

        self.refresh_stats()

        self.add_message(
            "JARVIS",
            "System online. I am ready.",
            False
        )

        GLib.timeout_add(
            2000,
            self.update_clock
        )

    # ======================================================
    # CSS
    # ======================================================

    def load_css(self):

        css = b"""
        * {
            font-family: Sans;
        }

        window {
            background: #03070d;
            color: #dcefff;
        }

        .sidebar {
            background: #050b13;
            border-right: 1px solid #102a39;
        }

        .brand {
            color: #8eeaff;
            font-size: 20px;
            font-weight: bold;
            letter-spacing: 6px;
        }

        .tagline {
            color: #55717c;
            font-size: 9px;
            letter-spacing: 2px;
        }

        .section {
            color: #517280;
            font-size: 9px;
            font-weight: bold;
            letter-spacing: 2px;
        }

        .nav {
            background: transparent;
            color: #87a5b3;
            border: none;
            padding: 9px 12px;
            border-radius: 8px;
        }

        .nav:hover {
            background: #0a1c26;
            color: #8feeff;
        }

        .nav-active {
            background: #0b2430;
            color: #8feeff;
            border: 1px solid #174b5c;
        }

        .panel {
            background: #061019;
            border: 1px solid #102d3c;
            border-radius: 12px;
        }

        .panel-title {
            color: #83e9ff;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 2px;
        }

        .muted {
            color: #607c88;
            font-size: 9px;
        }

        .value {
            color: #dff8ff;
            font-size: 14px;
            font-weight: bold;
        }

        .good {
            color: #54e7b0;
            font-size: 9px;
            font-weight: bold;
        }

        .ready {
            color: #58dfff;
            font-size: 9px;
            font-weight: bold;
        }

        .chat-user {
            background: #092131;
            border: 1px solid #164b62;
            border-radius: 11px;
            padding: 10px;
        }

        .chat-ai {
            background: #071720;
            border: 1px solid #123746;
            border-radius: 11px;
            padding: 10px;
        }

        .sender {
            color: #61e5ff;
            font-size: 9px;
            font-weight: bold;
        }

        .message {
            color: #d5e9ee;
            font-size: 11px;
        }

        entry {
            background: #07121c;
            color: #e6faff;
            border: 1px solid #18536b;
            border-radius: 10px;
            padding: 10px;
            font-size: 11px;
        }

        entry:focus {
            border-color: #45dcff;
        }

        .action {
            background: #08202d;
            color: #73eaff;
            border: 1px solid #1a637d;
            border-radius: 9px;
            padding: 9px 12px;
        }

        .action:hover {
            background: #0d3141;
        }

        .topbar {
            background: #050b13;
            border-bottom: 1px solid #102a39;
        }

        .top-title {
            color: #d8f5ff;
            font-size: 13px;
            font-weight: bold;
            letter-spacing: 2px;
        }

        .clock {
            color: #65818c;
            font-size: 9px;
        }
        """

        provider = Gtk.CssProvider()

        provider.load_from_data(
            css
        )

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # ======================================================
    # MAIN UI
    # ======================================================

    def build_ui(self):

        root = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        self.add(root)

        self.build_sidebar(
            root
        )

        self.build_main(
            root
        )

    # ======================================================
    # SIDEBAR
    # ======================================================

    def build_sidebar(
        self,
        root
    ):

        sidebar = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=5
        )

        sidebar.set_size_request(
            210,
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
            18
        )

        tagline = Gtk.Label(
            label="ADVANCED AI SYSTEM"
        )

        tagline.get_style_context().add_class(
            "tagline"
        )

        sidebar.pack_start(
            tagline,
            False,
            False,
            5
        )

        section = Gtk.Label(
            label="MODULES"
        )

        section.set_xalign(0)
        section.set_margin_start(15)
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

        for label, name in [
            ("CHAT", "chat"),
            ("SYSTEM", "system"),
            ("MEMORY", "memory"),
            ("TOOLS", "tools"),
            ("CYBER ENGINE", "cyber"),
            ("SETTINGS", "settings")
        ]:

            button = Gtk.Button(
                label=label
            )

            button.get_style_context().add_class(
                "nav"
            )

            button.connect(
                "clicked",
                self.switch_view,
                name
            )

            sidebar.pack_start(
                button,
                False,
                False,
                1
            )

            self.nav_buttons[
                name
            ] = button

        spacer = Gtk.Box()

        sidebar.pack_start(
            spacer,
            True,
            True,
            0
        )

        status = Gtk.Label(
            label="SYSTEM"
        )

        status.set_xalign(
            0
        )

        status.set_margin_start(
            15
        )

        status.get_style_context().add_class(
            "section"
        )

        sidebar.pack_start(
            status,
            False,
            False,
            5
        )

        self.sidebar_ai = self.add_status(
            sidebar,
            "GEMINI",
            "ONLINE",
            True
        )

        self.sidebar_memory = self.add_status(
            sidebar,
            "MEMORY",
            "ACTIVE",
            True
        )

        self.sidebar_voice = self.add_status(
            sidebar,
            "VOICE",
            "CHECKING",
            False
        )

        return sidebar

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

        row.set_margin_start(
            15
        )

        row.set_margin_end(
            15
        )

        name_label = Gtk.Label(
            label=name
        )

        name_label.set_xalign(
            0
        )

        name_label.get_style_context().add_class(
            "muted"
        )

        state_label = Gtk.Label(
            label=state
        )

        state_label.set_xalign(
            1
        )

        state_label.get_style_context().add_class(
            "good"
            if good
            else "ready"
        )

        row.pack_start(
            name_label,
            True,
            True,
            0
        )

        row.pack_end(
            state_label,
            False,
            False,
            0
        )

        sidebar.pack_start(
            row,
            False,
            False,
            5
        )

        return state_label

    # ======================================================
    # MAIN AREA
    # ======================================================

    def build_main(
        self,
        root
    ):

        main = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL
        )

        root.pack_start(
            main,
            True,
            True,
            0
        )

        # Top bar

        top = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        top.get_style_context().add_class(
            "topbar"
        )

        top.set_size_request(
            -1,
            46
        )

        main.pack_start(
            top,
            False,
            False,
            0
        )

        self.top_title = Gtk.Label(
            label="CHAT"
        )

        self.top_title.get_style_context().add_class(
            "top-title"
        )

        top.pack_start(
            self.top_title,
            False,
            False,
            15
        )

        self.clock = Gtk.Label(
            label=""
        )

        self.clock.get_style_context().add_class(
            "clock"
        )

        top.pack_end(
            self.clock,
            False,
            False,
            15
        )

        self.stack = Gtk.Stack()

        self.stack.set_transition_type(
            Gtk.StackTransitionType.CROSSFADE
        )

        self.stack.set_transition_duration(
            120
        )

        main.pack_start(
            self.stack,
            True,
            True,
            0
        )

        self.chat_view = self.build_chat_view()

        self.system_view = self.build_system_view()

        self.memory_view = self.build_memory_view()

        self.tools_view = self.build_tools_view()

        self.cyber_view = self.build_cyber_view()

        self.settings_view = self.build_settings_view()

        self.stack.add_named(
            self.chat_view,
            "chat"
        )

        self.stack.add_named(
            self.system_view,
            "system"
        )

        self.stack.add_named(
            self.memory_view,
            "memory"
        )

        self.stack.add_named(
            self.tools_view,
            "tools"
        )

        self.stack.add_named(
            self.cyber_view,
            "cyber"
        )

        self.stack.add_named(
            self.settings_view,
            "settings"
        )

        self.stack.set_visible_child_name(
            "chat"
        )

    # ======================================================
    # CHAT
    # ======================================================

    def build_chat_view(
        self
    ):

        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8
        )

        body = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        body.set_border_width(
            8
        )

        outer.pack_start(
            body,
            True,
            True,
            0
        )

        # Core

        core_panel = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL
        )

        core_panel.get_style_context().add_class(
            "panel"
        )

        core_panel.set_size_request(
            390,
            -1
        )

        core_title = Gtk.Label(
            label="JARVIS CORE"
        )

        core_title.get_style_context().add_class(
            "panel-title"
        )

        core_title.set_margin_top(
            10
        )

        core_panel.pack_start(
            core_title,
            False,
            False,
            0
        )

        self.orb = CoreView()

        core_panel.pack_start(
            self.orb,
            True,
            True,
            0
        )

        body.pack_start(
            core_panel,
            False,
            False,
            0
        )

        # Chat

        chat_panel = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6
        )

        chat_panel.get_style_context().add_class(
            "panel"
        )

        chat_title = Gtk.Label(
            label="CONVERSATION"
        )

        chat_title.get_style_context().add_class(
            "panel-title"
        )

        chat_title.set_xalign(
            0
        )

        chat_title.set_margin_start(
            12
        )

        chat_title.set_margin_top(
            10
        )

        chat_panel.pack_start(
            chat_title,
            False,
            False,
            0
        )

        scroll = Gtk.ScrolledWindow()

        scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC
        )

        self.chat = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=7
        )

        scroll.add_with_viewport(
            self.chat
        )

        chat_panel.pack_start(
            scroll,
            True,
            True,
            0
        )

        body.pack_start(
            chat_panel,
            True,
            True,
            0
        )

        # Input

        input_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6
        )

        input_box.set_margin_start(
            8
        )

        input_box.set_margin_end(
            8
        )

        input_box.set_margin_bottom(
            8
        )

        self.entry = Gtk.Entry()

        self.entry.set_placeholder_text(
            "Message JARVIS..."
        )

        self.entry.connect(
            "activate",
            self.send_message
        )

        input_box.pack_start(
            self.entry,
            True,
            True,
            0
        )

        self.send_btn = Gtk.Button(
            label="SEND"
        )

        self.send_btn.get_style_context().add_class(
            "action"
        )

        self.send_btn.connect(
            "clicked",
            self.send_message
        )

        input_box.pack_end(
            self.send_btn,
            False,
            False,
            0
        )

        chat_panel.pack_end(
            input_box,
            False,
            False,
            0
        )

        return outer

    def add_message(
        self,
        sender,
        message,
        user
    ):

        bubble = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4
        )

        bubble.get_style_context().add_class(
            "chat-user"
            if user
            else "chat-ai"
        )

        bubble.set_margin_start(
            8
        )

        bubble.set_margin_end(
            8
        )

        sender_label = Gtk.Label(
            label=sender
        )

        sender_label.set_xalign(
            0
        )

        sender_label.get_style_context().add_class(
            "sender"
        )

        text = Gtk.Label(
            label=message
        )

        text.set_xalign(
            0
        )

        text.set_line_wrap(
            True
        )

        text.set_selectable(
            True
        )

        text.set_max_width_chars(
            90
        )

        text.get_style_context().add_class(
            "message"
        )

        bubble.pack_start(
            sender_label,
            False,
            False,
            0
        )

        bubble.pack_start(
            text,
            False,
            False,
            0
        )

        self.chat.pack_start(
            bubble,
            False,
            False,
            2
        )

        bubble.show_all()

        self._chat_count += 1

    def send_message(
        self,
        widget=None
    ):

        if self.processing:
            return

        text = self.entry.get_text().strip()

        if not text:
            return

        self.entry.set_text(
            ""
        )

        self.add_message(
            "YOU",
            text,
            True
        )

        self.processing = True

        self.speaking = False

        self.orb.set_state(
            thinking=True,
            speaking=False
        )

        self.send_btn.set_sensitive(
            False
        )

        thread = threading.Thread(
            target=self.ask,
            args=(text,),
            daemon=True
        )

        thread.start()

    def ask(
        self,
        text
    ):

        try:

            answer = self.brain.ask(
                text
            )

        except Exception as error:

            answer = (
                "JARVIS ERROR:\n"
                + str(error)
            )

        GLib.idle_add(
            self.receive,
            answer
        )

    def receive(
        self,
        answer
    ):

        self._last_answer = answer

        self.add_message(
            "JARVIS",
            answer,
            False
        )

        self.processing = False

        self.send_btn.set_sensitive(
            True
        )

        self.orb.set_state(
            thinking=False,
            speaking=True
        )


        return False

    # ======================================================
    # VOICE
    # ======================================================

    def speak(
        self,
        text
    ):

        thread = threading.Thread(
            target=self.say,
            args=(text,),
            daemon=True
        )

        thread.start()

    def say(
        self,
        text
    ):

        try:

            if shutil.which(
                "espeak-ng"
            ):

                subprocess.run(
                    [
                        "espeak-ng",
                        "-s",
                        "145",
                        str(text)
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            elif shutil.which(
                "espeak"
            ):

                subprocess.run(
                    [
                        "espeak",
                        "-s",
                        "145",
                        str(text)
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

        except Exception:
            pass

        GLib.idle_add(
            self.voice_finished
        )

    def voice_finished(
        self
    ):

        self.speaking = False

        self.orb.set_state(
            thinking=False,
            speaking=False
        )

        return False

    # ======================================================
    # SYSTEM
    # ======================================================

    def build_system_view(
        self
    ):

        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )

        outer.set_border_width(
            15
        )

        title = Gtk.Label(
            label="SYSTEM TELEMETRY"
        )

        title.set_xalign(
            0
        )

        title.get_style_context().add_class(
            "panel-title"
        )

        outer.pack_start(
            title,
            False,
            False,
            0
        )

        self.system_grid = Gtk.Grid()

        self.system_grid.set_row_spacing(
            8
        )

        self.system_grid.set_column_spacing(
            8
        )

        outer.pack_start(
            self.system_grid,
            False,
            False,
            0
        )

        self.system_values = {}

        metrics = [
            ("host", "HOST"),
            ("os", "OPERATING SYSTEM"),
            ("python", "PYTHON"),
            ("cpu", "CPU"),
            ("ram", "RAM"),
            ("disk", "DISK"),
            ("uptime", "UPTIME"),
            ("kernel", "KERNEL")
        ]

        for index, (
            key,
            label
        ) in enumerate(
            metrics
        ):

            frame = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=3
            )

            frame.get_style_context().add_class(
                "panel"
            )

            frame.set_border_width(
                10
            )

            value = Gtk.Label(
                label="N/A"
            )

            value.set_xalign(
                0
            )

            value.get_style_context().add_class(
                "value"
            )

            caption = Gtk.Label(
                label=label
            )

            caption.set_xalign(
                0
            )

            caption.get_style_context().add_class(
                "muted"
            )

            frame.pack_start(
                value,
                False,
                False,
                0
            )

            frame.pack_start(
                caption,
                False,
                False,
                0
            )

            self.system_grid.attach(
                frame,
                index % 4,
                index // 4,
                1,
                1
            )

            self.system_values[
                key
            ] = value

        return outer

    def refresh_stats(
        self
    ):

        if psutil is None:

            return True

        try:

            disk_path = (
                ROOT_DIR
                if os.path.exists(
                    ROOT_DIR
                )
                else "/"
            )

            self.system_values[
                "host"
            ].set_text(
                platform.node()
                or
                "N/A"
            )

            self.system_values[
                "os"
            ].set_text(
                platform.system()
                +
                " "
                +
                platform.release()
            )

            self.system_values[
                "python"
            ].set_text(
                platform.python_version()
            )

            self.system_values[
                "cpu"
            ].set_text(
                str(
                    round(
                        psutil.cpu_percent(
                            interval=None
                        ),
                        1
                    )
                )
                + "%"
            )

            self.system_values[
                "ram"
            ].set_text(
                str(
                    round(
                        psutil.virtual_memory().percent,
                        1
                    )
                )
                + "%"
            )

            self.system_values[
                "disk"
            ].set_text(
                str(
                    round(
                        psutil.disk_usage(
                            disk_path
                        ).percent,
                        1
                    )
                )
                + "%"
            )

            uptime = int(
                time.time()
                -
                psutil.boot_time()
            )

            self.system_values[
                "uptime"
            ].set_text(
                self.format_duration(
                    uptime
                )
            )

            self.system_values[
                "kernel"
            ].set_text(
                platform.release()
            )

        except Exception:
            pass

        return True

    def format_duration(
        self,
        seconds
    ):

        days = seconds // 86400

        hours = (
            seconds % 86400
        ) // 3600

        minutes = (
            seconds % 3600
        ) // 60

        return (
            str(days)
            + "d "
            + "%02d" % hours
            + "h "
            + "%02d" % minutes
            + "m"
        )

    # ======================================================
    # MEMORY
    # ======================================================

    def build_memory_view(
        self
    ):

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )

        box.set_border_width(
            15
        )

        title = Gtk.Label(
            label="LONG-TERM MEMORY"
        )

        title.set_xalign(
            0
        )

        title.get_style_context().add_class(
            "panel-title"
        )

        box.pack_start(
            title,
            False,
            False,
            0
        )

        self.memory_info = Gtk.Label(
            label="Loading..."
        )

        self.memory_info.set_xalign(
            0
        )

        self.memory_info.set_selectable(
            True
        )

        self.memory_info.get_style_context().add_class(
            "message"
        )

        box.pack_start(
            self.memory_info,
            False,
            False,
            0
        )

        button = Gtk.Button(
            label="REFRESH MEMORY"
        )

        button.get_style_context().add_class(
            "action"
        )

        button.connect(
            "clicked",
            self.refresh_memory
        )

        box.pack_start(
            button,
            False,
            False,
            0
        )

        self.refresh_memory()

        return box

    def refresh_memory(
        self,
        widget=None
    ):

        path = os.path.join(
            ROOT_DIR,
            "data",
            "memory.json"
        )

        if not os.path.exists(
            path
        ):

            self.memory_info.set_text(
                "Memory file: N/A\n"
                "No persistent memory file found."
            )

            return

        try:

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(
                    file
                )

            if isinstance(
                data,
                dict
            ):

                conversations = data.get(
                    "conversations",
                    []
                )

            else:

                conversations = []

            self.memory_info.set_text(
                "Persistent memory: ACTIVE\n"
                "Records: "
                +
                str(
                    len(
                        conversations
                    )
                )
                +
                "\n\n"
                +
                path
            )

        except Exception as error:

            self.memory_info.set_text(
                "Memory error:\n"
                + str(error)
            )

    # ======================================================
    # TOOLS
    # ======================================================

    def build_tools_view(
        self
    ):

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )

        box.set_border_width(
            15
        )

        title = Gtk.Label(
            label="LOCAL TOOLS"
        )

        title.set_xalign(
            0
        )

        title.get_style_context().add_class(
            "panel-title"
        )

        box.pack_start(
            title,
            False,
            False,
            0
        )

        tools = [
            (
                "TERMINAL",
                self.open_terminal
            ),
            (
                "FILE MANAGER",
                self.open_files
            ),
            (
                "PROJECT FOLDER",
                self.open_project
            ),
            (
                "BROWSER",
                self.open_browser
            )
        ]

        grid = Gtk.Grid()

        grid.set_row_spacing(
            8
        )

        grid.set_column_spacing(
            8
        )

        for i, (
            name,
            callback
        ) in enumerate(
            tools
        ):

            button = Gtk.Button(
                label=name
            )

            button.get_style_context().add_class(
                "action"
            )

            button.connect(
                "clicked",
                callback
            )

            grid.attach(
                button,
                i % 2,
                i // 2,
                1,
                1
            )

        box.pack_start(
            grid,
            False,
            False,
            0
        )

        return box

    def run_first(
        self,
        commands,
        args=None
    ):

        args = args or []

        for command in commands:

            if shutil.which(
                command
            ):

                subprocess.Popen(
                    [command]
                    + args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                return True

        return False

    def open_terminal(
        self,
        widget
    ):

        self.run_first(
            [
                "xfce4-terminal",
                "gnome-terminal",
                "konsole"
            ]
        )

    def open_files(
        self,
        widget
    ):

        self.run_first(
            [
                "thunar",
                "nautilus",
                "dolphin"
            ],
            [
                ROOT_DIR
            ]
        )

    def open_project(
        self,
        widget
    ):

        if shutil.which(
            "xdg-open"
        ):

            subprocess.Popen(
                [
                    "xdg-open",
                    ROOT_DIR
                ]
            )

    def open_browser(
        self,
        widget
    ):

        if shutil.which(
            "xdg-open"
        ):

            subprocess.Popen(
                [
                    "xdg-open",
                    "https://www.google.com"
                ]
            )

    # ======================================================
    # CYBER
    # ======================================================

    def build_cyber_view(
        self
    ):

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )

        box.set_border_width(
            15
        )

        title = Gtk.Label(
            label="CYBER ENGINE"
        )

        title.set_xalign(
            0
        )

        title.get_style_context().add_class(
            "panel-title"
        )

        box.pack_start(
            title,
            False,
            False,
            0
        )

        self.cyber_info = Gtk.Label(
            label="Loading..."
        )

        self.cyber_info.set_xalign(
            0
        )

        self.cyber_info.set_selectable(
            True
        )

        self.cyber_info.get_style_context().add_class(
            "message"
        )

        box.pack_start(
            self.cyber_info,
            False,
            False,
            0
        )

        refresh = Gtk.Button(
            label="REFRESH EVIDENCE"
        )

        refresh.get_style_context().add_class(
            "action"
        )

        refresh.connect(
            "clicked",
            self.refresh_cyber
        )

        box.pack_start(
            refresh,
            False,
            False,
            0
        )

        self.refresh_cyber()

        return box

    def refresh_cyber(
        self,
        widget=None
    ):

        directory = os.path.join(
            ROOT_DIR,
            "cyber",
            "reports"
        )

        if not os.path.isdir(
            directory
        ):

            self.cyber_info.set_text(
                "Cyber reports: N/A"
            )

            return

        files = sorted(
            os.listdir(
                directory
            ),
            reverse=True
        )

        scans = [
            f
            for f in files
            if f.startswith(
                "scan_"
            )
        ]

        evidence = [
            f
            for f in files
            if f.startswith(
                "evidence_"
            )
        ]

        latest = (
            files[0]
            if files
            else
            "None"
        )

        self.cyber_info.set_text(
            "Authorized cyber workspace\n\n"
            "Scan reports: "
            +
            str(
                len(scans)
            )
            +
            "\n"
            "Evidence files: "
            +
            str(
                len(evidence)
            )
            +
            "\n\n"
            "Latest file:\n"
            +
            latest
        )

    # ======================================================
    # SETTINGS
    # ======================================================

    def build_settings_view(
        self
    ):

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )

        box.set_border_width(
            15
        )

        title = Gtk.Label(
            label="SYSTEM SETTINGS"
        )

        title.set_xalign(
            0
        )

        title.get_style_context().add_class(
            "panel-title"
        )

        box.pack_start(
            title,
            False,
            False,
            0
        )

        text = (
            "Interface: GTK 3\n"
            "AI backend: core.brain.JarvisBrain\n"
            "Memory: data/memory.json\n"
            "Cyber reports: cyber/reports\n"
            "Voice: espeak-ng / espeak\n"
            "Project: "
            +
            ROOT_DIR
        )

        info = Gtk.Label(
            label=text
        )

        info.set_xalign(
            0
        )

        info.set_selectable(
            True
        )

        info.get_style_context().add_class(
            "message"
        )

        box.pack_start(
            info,
            False,
            False,
            0
        )

        return box

    # ======================================================
    # NAVIGATION
    # ======================================================

    def switch_view(
        self,
        widget,
        name
    ):

        self.current_view = name

        if name == "chat":
            view = self.chat_view

        elif name == "system":
            view = self.system_view

        elif name == "memory":
            view = self.memory_view

        elif name == "tools":
            view = self.tools_view

        elif name == "cyber":
            view = self.cyber_view

        else:
            view = self.settings_view

        self.stack.set_visible_child(
            view
        )

        self.top_title.set_text(
            name.upper()
        )

        for key, button in self.nav_buttons.items():

            context = (
                button
                .get_style_context()
            )

            if key == name:

                context.add_class(
                    "nav-active"
                )

            else:

                context.remove_class(
                    "nav-active"
                )

    # ======================================================
    # CLOCK
    # ======================================================

    def update_clock(
        self
    ):

        self.clock.set_text(
            time.strftime(
                "%Y-%m-%d  %H:%M:%S"
            )
        )

        self.refresh_stats()

        return True


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
