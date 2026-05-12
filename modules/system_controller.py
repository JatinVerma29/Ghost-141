"""
modules/system_controller.py — OS-level control for Ghost-141
"""

import os
import subprocess
import platform
import datetime
import pyautogui
import psutil

pyautogui.FAILSAFE = True


class SystemController:
    def __init__(self, settings):
        self.settings = settings
        self.os = platform.system()

    # ── Screenshots ────────────────────────────────────────────────────────

    def screenshot(self, path: str = None) -> str:
        if not path:
            ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.expanduser(f"~/Desktop/ghost_{ts}.png")
        img = pyautogui.screenshot()
        img.save(path)
        print(f"[SYSTEM] Screenshot saved: {path}")
        return path

    # ── Keyboard & Mouse ───────────────────────────────────────────────────

    def type_text(self, text: str):
        """Type text using clipboard paste — preserves case, handles long text."""
        try:
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            print(f"[SYSTEM] Typed: {text[:80]}...")
        except Exception as e:
            print(f"[SYSTEM] Clipboard failed ({e}), using typewrite.")
            # Fallback: type slowly to avoid drops
            pyautogui.typewrite(text[:200], interval=0.03)
            print(f"[SYSTEM] Typed (direct): {text[:80]}...")

    def hotkey(self, *keys):
        pyautogui.hotkey(*keys)
        print(f"[SYSTEM] Hotkey: {keys}")

    def click(self, x: int = None, y: int = None, button: str = "left"):
        if x is not None and y is not None:
            pyautogui.click(x, y, button=button)
        else:
            pyautogui.click(button=button)
        print(f"[SYSTEM] Clicked ({x},{y}) [{button}]")

    def scroll(self, clicks: int, x: int = None, y: int = None):
        if x and y:
            pyautogui.scroll(clicks, x=x, y=y)
        else:
            pyautogui.scroll(clicks)

    def move_mouse(self, x: int, y: int, duration: float = 0.3):
        pyautogui.moveTo(x, y, duration=duration)

    # ── Volume & Display ───────────────────────────────────────────────────

    def set_volume(self, level: int):
        level = max(0, min(100, level))
        if self.os == "Linux":
            subprocess.run(["amixer", "-q", "sset", "Master", f"{level}%"])
        elif self.os == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
        elif self.os == "Windows":
            subprocess.run(["nircmd", "setsysvolume", str(int(level * 655.35))])
        print(f"[SYSTEM] Volume set to {level}%")

    def set_brightness(self, level: int):
        level = max(0, min(100, level))
        if self.os == "Linux":
            subprocess.run(["brightnessctl", "set", f"{level}%"])
        elif self.os == "Darwin":
            subprocess.run(["brightness", str(level / 100)])
        elif self.os == "Windows":
            subprocess.run(["powershell", "-Command",
                            f"(Get-WmiObject -Namespace root/WMI -Class "
                            f"WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"])
        print(f"[SYSTEM] Brightness set to {level}%")

    # ── Lock / Power ───────────────────────────────────────────────────────

    def lock_screen(self):
        if self.os == "Linux":
            subprocess.Popen(["xdg-screensaver", "lock"])
        elif self.os == "Darwin":
            subprocess.Popen(["osascript", "-e",
                              'tell application "System Events" to keystroke "q" using {control down, command down}'])
        elif self.os == "Windows":
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
        print("[SYSTEM] Screen locked.")

    def power_action(self, action: str):
        if self.os == "Linux":
            cmd = ["shutdown", "-h", "now"] if action == "shutdown" else ["reboot"]
        elif self.os == "Darwin":
            cmd = ["osascript", "-e", f'tell app "System Events" to {"shut down" if action=="shutdown" else "restart"}']
        elif self.os == "Windows":
            cmd = ["shutdown", "/s", "/t", "0"] if action == "shutdown" else ["shutdown", "/r", "/t", "0"]
        subprocess.run(cmd)

    # ── Terminal Commands ──────────────────────────────────────────────────

    def run_command(self, cmd: str, timeout: int = 10) -> str:
        print(f"[SYSTEM] Running: {cmd}")
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=timeout
            )
            output = result.stdout or result.stderr or "(no output)"
            print(f"[SYSTEM] Output: {output[:500]}")
            return output
        except subprocess.TimeoutExpired:
            return "Command timed out."
        except Exception as e:
            return f"Error: {e}"

    # ── Notifications ──────────────────────────────────────────────────────

    def notify(self, message: str, title: str = "Ghost-141"):
        try:
            if self.os == "Linux":
                subprocess.Popen(["notify-send", title, message])
            elif self.os == "Darwin":
                subprocess.Popen(["osascript", "-e",
                                  f'display notification "{message}" with title "{title}"'])
            elif self.os == "Windows":
                try:
                    from win10toast import ToastNotifier
                    ToastNotifier().show_toast(title, message, duration=4)
                except ImportError:
                    # Fallback using PowerShell
                    subprocess.Popen([
                        "powershell", "-WindowStyle", "Hidden", "-Command",
                        f'Add-Type -AssemblyName System.Windows.Forms; '
                        f'$n = New-Object System.Windows.Forms.NotifyIcon; '
                        f'$n.Icon = [System.Drawing.SystemIcons]::Information; '
                        f'$n.Visible = $true; '
                        f'$n.ShowBalloonTip(4000, "{title}", "{message}", '
                        f'[System.Windows.Forms.ToolTipIcon]::None)'
                    ])
        except Exception as e:
            print(f"[SYSTEM] Notification failed: {e}")
        print(f"[SYSTEM] Notify: {title} — {message}")

    # ── Resource Monitoring ────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "cpu_percent":  psutil.cpu_percent(interval=1),
            "ram_percent":  psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "battery":      psutil.sensors_battery(),
        }

    def list_processes(self) -> list:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except psutil.NoSuchProcess:
                pass
        return sorted(procs, key=lambda x: x.get("cpu_percent", 0), reverse=True)[:15]