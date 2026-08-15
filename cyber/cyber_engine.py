import os
import json
import subprocess
import datetime
import ipaddress


class CyberEngine:

    def __init__(self):

        base_dir = os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )

        self.base_dir = base_dir

        self.report_dir = os.path.join(
            base_dir,
            "cyber",
            "reports"
        )

        os.makedirs(
            self.report_dir,
            exist_ok=True
        )

        self.scope = []

    def add_target(self, target):

        target = target.strip()

        if not target:
            return False

        try:

            ipaddress.ip_address(target)

            if target not in self.scope:
                self.scope.append(target)

            return True

        except ValueError:

            return False

    def clear_scope(self):

        self.scope = []

    def get_scope(self):

        return list(self.scope)

    def scan_target(self, target):

        if target not in self.scope:

            return {
                "success": False,
                "error": "Target is outside the authorized scope."
            }

        timestamp = datetime.datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        safe_target = target.replace(
            ".",
            "_"
        )

        filename = (
            "scan_"
            + safe_target
            + "_"
            + timestamp
            + ".txt"
        )

        report_path = os.path.join(
            self.report_dir,
            filename
        )

        command = [
            "nmap",
            "-sV",
            target
        ]

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300
            )

            output = result.stdout

            if result.stderr:

                output += (
                    "\n\nNMAP ERRORS:\n"
                    + result.stderr
                )

            with open(
                report_path,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(output)

            return {
                "success": True,
                "target": target,
                "report": report_path,
                "output": output
            }

        except FileNotFoundError:

            return {
                "success": False,
                "error": "Nmap was not found in PATH."
            }

        except subprocess.TimeoutExpired:

            return {
                "success": False,
                "error": "The scan timed out."
            }

        except Exception as error:

            return {
                "success": False,
                "error": str(error)
            }

    def analyze_result(self, scan_result):

        if not scan_result.get("success"):

            return {
                "success": False,
                "error": scan_result.get(
                    "error",
                    "Unknown error"
                )
            }

        output = scan_result.get(
            "output",
            ""
        )

        findings = []

        interesting_ports = [
            "21",
            "22",
            "23",
            "25",
            "53",
            "80",
            "110",
            "135",
            "139",
            "143",
            "443",
            "445",
            "3306",
            "3389",
            "5432",
            "5900",
            "8080"
        ]

        for line in output.splitlines():

            line = line.strip()

            if not line:
                continue

            for port in interesting_ports:

                if line.startswith(
                    port + "/"
                ):

                    findings.append(line)
                    break

        return {
            "success": True,
            "target": scan_result.get(
                "target"
            ),
            "findings": findings,
            "report": scan_result.get(
                "report"
            )
        }

    def save_evidence(self, data):

        timestamp = datetime.datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = (
            "evidence_"
            + timestamp
            + ".json"
        )

        path = os.path.join(
            self.report_dir,
            filename
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

        return path


def main():

    print("=" * 55)
    print("JARVIS CYBER ENGINE")
    print("=" * 55)

    print("")
    print("Use this only against systems you own")
    print("or systems you are explicitly authorized to test.")
    print("")

    engine = CyberEngine()

    target = input(
        "LAB TARGET IP: "
    ).strip()

    if not engine.add_target(target):

        print("")
        print("Invalid IP address.")
        return

    print("")
    print("Authorized scope:")
    print(engine.get_scope())

    print("")
    print("Starting Nmap service scan...")
    print("")

    result = engine.scan_target(target)

    if not result.get("success"):

        print(
            "ERROR:",
            result.get("error")
        )

        return

    print("Scan completed.")

    print("")
    print("Analyzing result...")

    analysis = engine.analyze_result(
        result
    )

    print("")
    print("Detected services:")

    findings = analysis.get(
        "findings",
        []
    )

    if findings:

        for finding in findings:

            print(
                " -",
                finding
            )

    else:

        print(
            "No services matched the basic analysis."
        )

    evidence = engine.save_evidence(
        analysis
    )

    print("")
    print("Raw report:")
    print(
        result.get("report")
    )

    print("")
    print("Evidence:")
    print(evidence)

    print("")
    print("Cyber Engine finished.")


if __name__ == "__main__":

    main()