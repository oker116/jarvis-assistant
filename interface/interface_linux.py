import os
import sys
import math
import random
import threading
import tkinter as tk
from tkinter import scrolledtext

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.brain import JarvisBrain


class JarvisGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS")
        self.root.geometry("1000x720")
        self.root.minsize(700, 550)
        self.root.configure(bg="#070b12")

        self.brain = JarvisBrain()
        self.processing = False
        self.speaking = False
        self.listening = False
        self.orb_phase = 0.0
        self.particles = []

        self.build_ui()
        self.animate_orb()

    # -------------------------------------------------
    # UI
    # -------------------------------------------------

    def build_ui(self):
        header = tk.Frame(
            self.root,
            bg="#070b12",
            height=70
        )
        header.pack(fill="x")

        tk.Label(
            header,
            text="J A R V I S",
            font=("DejaVu Sans", 20, "bold"),
            fg="#d8e7ff",
            bg="#070b12"
        ).pack(pady=(18, 0))

        tk.Label(
            header,
            text="PERSONAL AI SYSTEM",
            font=("DejaVu Sans", 8),
            fg="#64748b",
            bg="#070b12"
        ).pack()

        # Chat
        chat_frame = tk.Frame(
            self.root,
            bg="#0a101a"
        )
        chat_frame.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=(5, 10)
        )

        self.chat = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("DejaVu Sans", 11),
            bg="#0a101a",
            fg="#dbe7f5",
            insertbackground="#dbe7f5",
            relief="flat",
            bd=0,
            padx=22,
            pady=18
        )
        self.chat.pack(fill="both", expand=True)
        self.chat.config(state="disabled")

        self.chat.tag_config(
            "user",
            foreground="#8ab4ff",
            spacing3=12
        )

        self.chat.tag_config(
            "jarvis",
            foreground="#b9f6ff",
            spacing3=12
        )

        self.chat.tag_config(
            "system",
            foreground="#64748b"
        )

        self.add_message(
            "JARVIS",
            "جاهز. أنا في انتظار أوامرك.",
            "jarvis"
        )

        # Orb
        orb_area = tk.Frame(
            self.root,
            bg="#070b12",
            height=115
        )
        orb_area.pack(fill="x")

        self.canvas = tk.Canvas(
            orb_area,
            width=150,
            height=105,
            bg="#070b12",
            highlightthickness=0
        )
        self.canvas.pack()

        # Input
        bottom = tk.Frame(
            self.root,
            bg="#070b12"
        )
        bottom.pack(fill="x", padx=35, pady=(0, 25))

        self.entry = tk.Entry(
            bottom,
            font=("DejaVu Sans", 12),
            bg="#111a27",
            fg="#e6edf7",
            insertbackground="#e6edf7",
            relief="flat",
            bd=0
        )
        self.entry.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=14,
            padx=(0, 10)
        )

        self.entry.bind(
            "<Return>",
            lambda event: self.send_message()
        )

        self.send_btn = tk.Button(
            bottom,
            text="SEND",
            command=self.send_message,
            font=("DejaVu Sans", 10, "bold"),
            bg="#17283d",
            fg="#b9f6ff",
            activebackground="#203b58",
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=22,
            pady=12
        )
        self.send_btn.pack(side="right")

    # -------------------------------------------------
    # CHAT
    # -------------------------------------------------

    def add_message(self, sender, text, tag):
        self.chat.config(state="normal")

        self.chat.insert(
            "end",
            f"\n{sender}\n",
            tag
        )

        self.chat.insert(
            "end",
            f"{text}\n",
            tag
        )

        self.chat.see("end")
        self.chat.config(state="disabled")

    # -------------------------------------------------
    # BRAIN
    # -------------------------------------------------

    def send_message(self):
        if self.processing:
            return

        text = self.entry.get().strip()

        if not text:
            return

        self.entry.delete(0, "end")

        self.add_message(
            "YOU",
            text,
            "user"
        )

        self.processing = True
        self.send_btn.config(
            state="disabled",
            text="..."
        )

        self.set_listening(True)

        thread = threading.Thread(
            target=self.ask_brain,
            args=(text,),
            daemon=True
        )
        thread.start()

    def ask_brain(self, text):
        try:
            answer = self.brain.ask(text)

            if not answer:
                answer = "لم أحصل على إجابة."

        except Exception as error:
            answer = f"حدث خطأ: {error}"

        self.root.after(
            0,
            lambda: self.finish_response(answer)
        )

    def finish_response(self, answer):
        self.processing = False

        self.send_btn.config(
            state="normal",
            text="SEND"
        )

        self.add_message(
            "JARVIS",
            answer,
            "jarvis"
        )

        self.speak(answer)

    # -------------------------------------------------
    # VOICE
    # -------------------------------------------------

    def speak(self, text):
        self.speaking = True

        thread = threading.Thread(
            target=self.voice_thread,
            args=(text,),
            daemon=True
        )
        thread.start()

    def voice_thread(self, text):
        try:
            # espeak-ng يدعم العربية بدرجات متفاوتة حسب الأصوات المثبتة
            safe_text = text.replace('"', "'")

            os.system(
                f'espeak-ng -v ar+f3 -s 155 "{safe_text}"'
            )

        finally:
            self.root.after(
                0,
                lambda: setattr(self, "speaking", False)
            )

    # -------------------------------------------------
    # ORB
    # -------------------------------------------------

    def set_listening(self, state):
        self.listening = state

    def animate_orb(self):
        self.canvas.delete("all")

        cx = 75
        cy = 52

        if self.speaking:
            energy = 10 + math.sin(self.orb_phase * 0.18) * 7
        elif self.processing:
            energy = 7 + math.sin(self.orb_phase * 0.12) * 5
        else:
            energy = 2 + math.sin(self.orb_phase * 0.05)

        # Outer rings
        for i in range(4):
            radius = 25 + i * 8 + energy

            self.canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline="#18324a",
                width=1
            )

        # Particles
        for i in range(18):
            angle = (
                self.orb_phase * 0.01
                + i * (math.pi * 2 / 18)
            )

            radius = 34 + math.sin(
                self.orb_phase * 0.03 + i
            ) * 5

            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius

            size = 2 + energy * 0.08

            self.canvas.create_oval(
                x - size,
                y - size,
                x + size,
                y + size,
                fill="#5ce1e6",
                outline=""
            )

        # Core
        core = 18 + energy

        self.canvas.create_oval(
            cx - core,
            cy - core,
            cx + core,
            cy + core,
            fill="#102c40",
            outline="#72e8ee",
            width=2
        )

        inner = 9 + energy * 0.35

        self.canvas.create_oval(
            cx - inner,
            cy - inner,
            cx + inner,
            cy + inner,
            fill="#7ce9ef",
            outline=""
        )

        self.orb_phase += 1

        self.root.after(
            40,
            self.animate_orb
        )


def main():
    root = tk.Tk()
    JarvisGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
