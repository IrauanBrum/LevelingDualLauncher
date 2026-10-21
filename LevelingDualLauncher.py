import os
import sys
import time
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import ctypes
from ctypes import wintypes

GAME_URL = "https://levelingidle2d.com.br/jogar"
APP_NAME = "Leveling Dual Launcher"

# Win32 helpers (Windows only)
user32 = ctypes.windll.user32 if os.name == "nt" else None
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long), ("top", ctypes.c_long),
        ("right", ctypes.c_long), ("bottom", ctypes.c_long)
    ]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]

def find_opera_gx():
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera GX\opera.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera GX\launcher.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Opera GX\opera.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Opera GX\launcher.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Opera GX\opera.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Opera GX\launcher.exe"),
    ]
    # Also check common Opera GX app folders
    local = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs"))
    if local.exists():
        try:
            candidates.extend(str(p) for p in local.glob("Opera GX/**/opera.exe"))
            candidates.extend(str(p) for p in local.glob("Opera GX/**/launcher.exe"))
        except Exception:
            pass
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None

def get_monitors():
    monitors = []
    if not user32:
        return monitors
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC,
                                       ctypes.POINTER(RECT), wintypes.LPARAM)
    def callback(hmonitor, hdc, rect_ptr, data):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            r = info.rcWork
            monitors.append((r.left, r.top, r.right-r.left, r.bottom-r.top))
        return 1
    user32.EnumDisplayMonitors(0, 0, callback_type(callback), 0)
    return monitors

def list_browser_windows():
    found = []
    if not user32:
        return found
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        # The game title can vary; accept Opera windows and target URL/page titles.
        if "opera" in title.lower() or "leveling" in title.lower() or "idle" in title.lower():
            found.append((hwnd, title))
        return True
    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return found

def move_window(hwnd, x, y, w, h):
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetWindowPos(hwnd, 0, int(x), int(y), int(w), int(h), SWP_NOZORDER | SWP_SHOWWINDOW)

class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("520x530")
        self.minsize(480, 500)
        self.configure(padx=18, pady=16)
        self.opera_path = find_opera_gx()
        self.layout = tk.StringVar(value="side")
        self.profile_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LevelingDualLauncher" / "profiles"
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Leveling Dual Launcher", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(self, text="Abra duas sessões independentes no Opera GX e organize as janelas.",
                  wraplength=475).pack(anchor="w", pady=(5, 14))

        box = ttk.LabelFrame(self, text="Disposição das janelas", padding=12)
        box.pack(fill="x", pady=(0, 12))
        choices = [
            ("Lado a lado — no monitor 1", "side"),
            ("Empilhado — no monitor 1", "stack"),
            ("Lado a lado — no monitor 2", "side2"),
            ("Empilhado — no monitor 2", "stack2"),
            ("Uma janela em cada monitor (1 e 2)", "both"),
        ]
        for label, value in choices:
            ttk.Radiobutton(box, text=label, variable=self.layout, value=value).pack(anchor="w", pady=2)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(0, 10))
        ttk.Button(buttons, text="Abrir Conta 1", command=lambda: self.open_session(1)).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(buttons, text="Abrir Conta 2", command=lambda: self.open_session(2)).pack(side="left", expand=True, fill="x", padx=(5, 0))

        ttk.Button(self, text="Abrir as duas contas e organizar", command=self.open_both).pack(fill="x", ipady=5)
        ttk.Button(self, text="Organizar janelas já abertas", command=self.arrange_existing).pack(fill="x", pady=(7, 0), ipady=3)

        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(self, textvariable=self.status, wraplength=475).pack(anchor="w", pady=(12, 0))

        ttk.Separator(self).pack(fill="x", pady=12)
        note = (
            "Observações:\n"
            "• Na primeira abertura, cada perfil do Opera GX pode pedir login separadamente.\n"
            "• Os perfis ficam separados em pastas próprias deste launcher.\n"
            "• Se o Opera GX estiver instalado em uma pasta diferente, use o botão abaixo para localizar o opera.exe.\n"
            "• Este programa apenas abre e posiciona janelas; não automatiza ações dentro do jogo."
        )
        ttk.Label(self, text=note, wraplength=475, justify="left").pack(anchor="w")
        ttk.Button(self, text="Localizar opera.exe manualmente", command=self.choose_opera).pack(anchor="w", pady=(8, 0))

    def choose_opera(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(title="Selecione opera.exe do Opera GX",
                                          filetypes=[("Executáveis", "*.exe"), ("Todos os arquivos", "*.*")])
        if path:
            self.opera_path = path
            self.status.set(f"Opera GX selecionado: {path}")

    def open_session(self, number):
        if not self._check_windows_and_opera():
            return
        self.profile_root.mkdir(parents=True, exist_ok=True)
        profile = self.profile_root / f"conta{number}"
        profile.mkdir(parents=True, exist_ok=True)
        args = [
            self.opera_path,
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--new-window",
            GAME_URL,
        ]
        try:
            subprocess.Popen(args, close_fds=True)
            self.status.set(f"Janela da Conta {number} solicitada. Faça login nessa janela.")
            self.after(1800, self.arrange_existing)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Não foi possível abrir o Opera GX:\n{e}")

    def open_both(self):
        self.open_session(1)
        self.after(900, lambda: self.open_session(2))
        self.after(3500, self.arrange_existing)

    def _check_windows_and_opera(self):
        if os.name != "nt":
            messagebox.showerror(APP_NAME, "Este launcher foi feito para Windows.")
            return False
        if not self.opera_path or not os.path.isfile(self.opera_path):
            messagebox.showwarning(APP_NAME, "Não encontrei o Opera GX. Clique em 'Localizar opera.exe manualmente'.")
            return False
        return True

    def arrange_existing(self):
        if not self._check_windows_and_opera():
            return
        monitors = get_monitors()
        if not monitors:
            messagebox.showwarning(APP_NAME, "Não consegui detectar os monitores.")
            return
        windows = list_browser_windows()
        # Use the two most recently enumerated matching windows.
        if len(windows) < 2:
            self.status.set(f"Encontrei {len(windows)} janela(s) compatível(is). Abra as duas contas primeiro.")
            return
        # Usually EnumWindows returns topmost/recent windows first.
        selected = windows[:2]
        mode = self.layout.get()
        if mode in ("side2", "stack2") and len(monitors) < 2:
            messagebox.showwarning(APP_NAME, "Não detectei um segundo monitor. Conecte-o ou escolha uma opção do monitor 1.")
            return

        if mode == "both":
            if len(monitors) < 2:
                messagebox.showwarning(APP_NAME, "A opção 'uma janela em cada monitor' exige dois monitores.")
                return
            placements = [
                (monitors[0][0], monitors[0][1], monitors[0][2], monitors[0][3]),
                (monitors[1][0], monitors[1][1], monitors[1][2], monitors[1][3]),
            ]
        else:
            monitor_index = 1 if mode in ("side2", "stack2") else 0
            x, y, w, h = monitors[monitor_index]
            if mode in ("side", "side2"):
                placements = [(x, y, w // 2, h), (x + w // 2, y, w - w // 2, h)]
            else:
                placements = [(x, y, w, h // 2), (x, y + h // 2, w, h - h // 2)]

        for (hwnd, title), rect in zip(selected, placements):
            move_window(hwnd, *rect)
        self.status.set("Tentei organizar as duas janelas. Confira se são as sessões corretas.")

if __name__ == "__main__":
    app = Launcher()
    app.mainloop()
