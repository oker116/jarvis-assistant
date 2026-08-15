import os
import sys
import json
import logging

ROOT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.system_control import run_command

logger = logging.getLogger("jarvis.tool_router")


class ToolRouter:
    """
    طبقة موحدة لأدوات JARVIS.

    الـ LLM يحدد الأداة والـ arguments،
    وهذه الطبقة هي التي تنفذها محلياً.

    event_callback اختياري:
    يسمح للواجهة بمعرفة ماذا يفعل JARVIS أثناء التنفيذ.
    """

    def __init__(self, root_dir, event_callback=None):
        self.root_dir = os.path.abspath(root_dir)
        self.event_callback = event_callback

    # =========================================================
    # ACTIVITY EVENTS
    # =========================================================

    def _emit(self, event):
        """
        إرسال حدث للواجهة أو أي مستمع خارجي.

        لو مفيش callback، لا يحدث شيء.
        ولو حصل خطأ في الواجهة، لا يعطل JARVIS.
        """

        if not self.event_callback:
            return

        try:
            self.event_callback(event)
        except Exception as error:
            logger.debug(
                "[TOOL EVENT ERROR] %s",
                error
            )

    # =========================================================
    # TOOL LIST
    # =========================================================

    def list_tools(self):
        return {
            "system_command": {
                "description": (
                    "Run a normal terminal command "
                    "on the local machine."
                ),
                "arguments": {
                    "command": "string"
                }
            },

            "read_file": {
                "description": (
                    "Read a UTF-8 text file "
                    "inside the JARVIS project."
                ),
                "arguments": {
                    "path": "string"
                }
            },

            "list_directory": {
                "description": (
                    "List files and directories "
                    "inside the JARVIS project."
                ),
                "arguments": {
                    "path": "string"
                }
            }
        }

    # =========================================================
    # SAFE PATH
    # =========================================================

    def _safe_path(self, path):

        path = os.path.expanduser(path)

        if not os.path.isabs(path):
            path = os.path.join(
                self.root_dir,
                path
            )

        path = os.path.abspath(path)

        if (
            path != self.root_dir
            and not path.startswith(
                self.root_dir + os.sep
            )
        ):
            raise ValueError(
                "Path is outside the JARVIS project."
            )

        return path

    # =========================================================
    # EXECUTE TOOL
    # =========================================================

    def execute(self, tool, arguments):

        arguments = arguments or {}

        logger.info(
            "[TOOL ROUTER] tool=%s arguments=%s",
            tool,
            arguments
        )

        # -----------------------------------------------------
        # Notify UI: tool started
        # -----------------------------------------------------

        self._emit({
            "type": "tool_start",
            "tool": tool,
            "arguments": arguments
        })

        # =====================================================
        # SYSTEM COMMAND
        # =====================================================

        if tool == "system_command":

            command = str(
                arguments.get(
                    "command",
                    ""
                )
            ).strip()

            if not command:

                result = {
                    "ok": False,
                    "tool": tool,
                    "error": "Missing command."
                }

                self._emit({
                    "type": "tool_result",
                    "tool": tool,
                    "result": result
                })

                return result

            # Show command to UI before execution

            self._emit({
                "type": "command",
                "tool": tool,
                "command": command
            })

            result = run_command(command)

            final_result = {
                "ok": bool(
                    result.get("ok")
                ),
                "tool": tool,
                "command": command,
                "result": result
            }

            # Notify UI: command finished

            self._emit({
                "type": "tool_result",
                "tool": tool,
                "command": command,
                "result": final_result
            })

            return final_result

        # =====================================================
        # READ FILE
        # =====================================================

        if tool == "read_file":

            try:

                path = self._safe_path(
                    str(
                        arguments.get(
                            "path",
                            ""
                        )
                    )
                )

            except ValueError as error:

                result = {
                    "ok": False,
                    "tool": tool,
                    "error": str(error)
                }

                self._emit({
                    "type": "tool_result",
                    "tool": tool,
                    "result": result
                })

                return result

            if not os.path.isfile(path):

                result = {
                    "ok": False,
                    "tool": tool,
                    "error": "File does not exist."
                }

                self._emit({
                    "type": "tool_result",
                    "tool": tool,
                    "result": result
                })

                return result

            if os.path.getsize(path) > 2 * 1024 * 1024:

                result = {
                    "ok": False,
                    "tool": tool,
                    "error": (
                        "File is larger than 2 MB."
                    )
                }

                self._emit({
                    "type": "tool_result",
                    "tool": tool,
                    "result": result
                })

                return result

            relative_path = os.path.relpath(
                path,
                self.root_dir
            )

            self._emit({
                "type": "file_read",
                "tool": tool,
                "path": relative_path
            })

            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    content = file.read()

                result = {
                    "ok": True,
                    "tool": tool,
                    "path": relative_path,
                    "content": content
                }

                self._emit({
                    "type": "tool_result",
                    "tool": tool,
                    "path": relative_path,
                    "result": result
                })

                return result

            except UnicodeDecodeError:

                result = {
                    "ok": False,
                    "tool": tool,
                    "error": (
                        "File is not UTF-8 text."
                    )
                }

                self._emit({
                    "type": "tool_result",
                    "tool": tool,
                    "result": result
                })

                return result

            except Exception as error:

                result = {
                    "ok": False,
                    "tool": tool,
                    "error": str(error)
                }

                self._emit({
                    "type": "tool_result",
                    "tool": tool,
                    "result": result
                })

                return result

        # =====================================================
        # LIST DIRECTORY
        # =====================================================

        if tool == "list_directory":

            try:

                path = self._safe_path(
                    str(
                        arguments.get(
                            "path",
                            "."
                        )
                    )
                )

            except ValueError as error:

                result = {
                    "ok": False,
                    "tool": tool,
                    "error": str(error)
                }

                self._emit({
                    "type": "tool_result",
                    "tool": tool,
                    "result": result
                })

                return result

            if not os.path.isdir(path):

                result = {
                    "ok": False,
                    "tool": tool,
                    "error": (
                        "Directory does not exist."
                    )
                }

                self._emit({
                    "type": "tool_result",
                    "tool": tool,
                    "result": result
                })

                return result

            relative_path = os.path.relpath(
                path,
                self.root_dir
            )

            self._emit({
                "type": "directory_read",
                "tool": tool,
                "path": relative_path
            })

            entries = []

            try:

                for name in sorted(
                    os.listdir(path)
                ):

                    full_path = os.path.join(
                        path,
                        name
                    )

                    entries.append({
                        "name": name,
                        "type": (
                            "directory"
                            if os.path.isdir(
                                full_path
                            )
                            else "file"
                        )
                    })

            except Exception as error:

                result = {
                    "ok": False,
                    "tool": tool,
                    "error": str(error)
                }

                self._emit({
                    "type": "tool_result",
                    "tool": tool,
                    "result": result
                })

                return result

            result = {
                "ok": True,
                "tool": tool,
                "path": relative_path,
                "entries": entries
            }

            self._emit({
                "type": "tool_result",
                "tool": tool,
                "path": relative_path,
                "result": result
            })

            return result

        # =====================================================
        # UNKNOWN TOOL
        # =====================================================

        result = {
            "ok": False,
            "tool": tool,
            "error": (
                f"Unknown tool: {tool}"
            )
        }

        self._emit({
            "type": "tool_result",
            "tool": tool,
            "result": result
        })

        return result


# =============================================================
# DIRECT TEST
# =============================================================

if __name__ == "__main__":

    ROOT = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    def show_event(event):
        print(
            "\n[ACTIVITY]"
        )

        print(
            json.dumps(
                event,
                ensure_ascii=False,
                indent=2
            )
        )

    router = ToolRouter(
        ROOT,
        event_callback=show_event
    )

    print(
        json.dumps(
            router.list_tools(),
            ensure_ascii=False,
            indent=2
        )
    )

    print(
        "\n--- TEST DIRECTORY ---"
    )

    result = router.execute(
        "list_directory",
        {
            "path": "tools"
        }
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )
