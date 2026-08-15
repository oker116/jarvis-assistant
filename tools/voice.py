import subprocess
import threading


class JarvisVoice:

    def __init__(self):

        self.speaking = False


    def speak(self, text):

        thread = threading.Thread(
            target=self._speak_thread,
            args=(text,)
        )

        thread.daemon = True
        thread.start()


    def _speak_thread(self, text):

        self.speaking = True

        safe_text = (
            str(text)
            .replace("'", "")
            .replace('"', "")
        )

        command = (
            "powershell "
            "-Command "
            "\"Add-Type -AssemblyName System.Speech; "
            "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$voice.Volume = 100; "
            "$voice.Rate = 0; "
            "$voice.Speak('"
            + safe_text
            + "')\""
        )

        try:

            subprocess.run(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        except Exception as error:

            print(
                "VOICE ERROR:",
                error
            )

        finally:

            self.speaking = False