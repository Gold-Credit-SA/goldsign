"""
Gold Credit - Assistente de Assinatura Digital ICP-Brasil

Launcher desktop com visual claro, minimalista e organizado em linha do tempo.
"""

import logging
import os
import queue
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
import tkinter as tk
from datetime import datetime
from tkinter import messagebox


if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    if hasattr(sys, "_MEIPASS"):
        sys.path.insert(0, sys._MEIPASS)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(BASE_DIR, "log.txt")
PORT = 8765
STATUS_URL = f"http://127.0.0.1:{PORT}/api/status"


BG = "#F7F5F0"
SURFACE = "#FFFFFF"
SURFACE2 = "#FCF8EE"
BORDER = "#E9E0CF"
TEXT = "#201A14"
MUTED = "#7B6D5A"
GOLD = "#E3B76E"
GOLD_SOFT = "#FFF6D9"
GOLD_STRONG = "#AA7128"
SUCCESS = "#5F9E7E"
ERROR = "#C45B5B"
WHITE = "#FFFFFF"
CONSOLE = "#FCFAF4"
CONSOLE_TEXT = "#6C7A67"

F_DISPLAY = ("Segoe UI", 22, "bold")
F_TITLE = ("Segoe UI", 11, "bold")
F_BODY = ("Segoe UI", 9)
F_SMALL = ("Segoe UI", 8)
F_LABEL = ("Segoe UI", 7, "bold")
F_MONO = ("Consolas", 8)
F_BTN = ("Segoe UI", 9, "bold")
F_BADGE = ("Segoe UI", 8, "bold")


def log(msg: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{now}] {msg}\n")
    except Exception:
        pass


def porta_livre(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def servico_online(timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(STATUS_URL, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _run_flask():
    try:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        from main import app  # noqa: PLC0415

        log(f"Iniciando servico Flask em 127.0.0.1:{PORT}")
        app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
    except Exception:
        log(f"ERRO FLASK:\n{traceback.format_exc()}")
        raise


def _divider(parent, color=BORDER, height=1, pady=0):
    tk.Frame(parent, bg=color, height=height).pack(fill="x", pady=pady)


def _card(parent, padx=20, pady=18):
    outer = tk.Frame(parent, bg=BORDER)
    inner = tk.Frame(outer, bg=SURFACE)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    inner.content_padx = padx
    inner.content_pady = pady
    return outer, inner


def _label_upper(parent, text, fg=GOLD_STRONG):
    tk.Label(parent, text=text, font=F_LABEL, bg=parent.cget("bg"), fg=fg, anchor="w").pack(anchor="w", pady=(0, 8))


def _pill(parent, text, bg=GOLD_SOFT, fg=GOLD_STRONG):
    wrap = tk.Frame(parent, bg=bg)
    tk.Label(wrap, text=text, font=F_LABEL, bg=bg, fg=fg, padx=10, pady=5).pack()
    return wrap


def _btn_primary(parent, text, cmd):
    frame = tk.Frame(parent, bg=GOLD_STRONG, cursor="hand2")
    lbl = tk.Label(frame, text=text, font=F_BTN, bg=GOLD_STRONG, fg=WHITE, padx=22, pady=10, cursor="hand2")
    lbl.pack(padx=1, pady=1)

    def enter(_):
        frame.configure(bg=GOLD)
        lbl.configure(bg=GOLD)

    def leave(_):
        frame.configure(bg=GOLD_STRONG)
        lbl.configure(bg=GOLD_STRONG)

    def click(_):
        cmd()

    for widget in (frame, lbl):
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        widget.bind("<Button-1>", click)
    return frame


def _btn_ghost(parent, text, cmd):
    frame = tk.Frame(parent, bg=BORDER, cursor="hand2")
    lbl = tk.Label(frame, text=text, font=F_BTN, bg=SURFACE, fg=TEXT, padx=20, pady=9, cursor="hand2")
    lbl.pack(padx=1, pady=1)

    def enter(_):
        frame.configure(bg=GOLD)
        lbl.configure(bg=GOLD_SOFT, fg=GOLD_STRONG)

    def leave(_):
        frame.configure(bg=BORDER)
        lbl.configure(bg=SURFACE, fg=TEXT)

    def click(_):
        cmd()

    for widget in (frame, lbl):
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        widget.bind("<Button-1>", click)
    return frame


def _timeline_colors(state: str):
    if state == "active":
        return {
            "dot_outer": GOLD,
            "dot_inner": GOLD_SOFT,
            "dot_text": GOLD_STRONG,
            "line": GOLD,
            "title": TEXT,
            "desc": MUTED,
        }
    if state == "done":
        return {
            "dot_outer": GOLD_STRONG,
            "dot_inner": GOLD_STRONG,
            "dot_text": WHITE,
            "line": GOLD,
            "title": TEXT,
            "desc": MUTED,
        }
    if state == "error":
        return {
            "dot_outer": ERROR,
            "dot_inner": "#FFF1F1",
            "dot_text": ERROR,
            "line": ERROR,
            "title": TEXT,
            "desc": MUTED,
        }
    return {
        "dot_outer": BORDER,
        "dot_inner": SURFACE,
        "dot_text": MUTED,
        "line": BORDER,
        "title": TEXT,
        "desc": MUTED,
    }


def _timeline_item(parent, number, title, desc, state="pending", last=False):
    colors = _timeline_colors(state)

    row = tk.Frame(parent, bg=parent.cget("bg"))
    row.pack(fill="x", pady=(0, 18 if not last else 0))

    rail = tk.Frame(row, bg=parent.cget("bg"), width=42)
    rail.pack(side="left", fill="y")
    rail.pack_propagate(False)

    dot_outer = tk.Frame(rail, bg=colors["dot_outer"], width=32, height=32)
    dot_outer.pack(anchor="n")
    dot_outer.pack_propagate(False)

    dot_inner = tk.Frame(dot_outer, bg=colors["dot_inner"])
    dot_inner.pack(fill="both", expand=True, padx=1, pady=1)

    tk.Label(
        dot_inner,
        text=number,
        font=F_BADGE,
        bg=colors["dot_inner"],
        fg=colors["dot_text"],
    ).place(relx=0.5, rely=0.5, anchor="center")

    if not last:
        tk.Frame(rail, bg=colors["line"], width=2, height=40).pack(pady=(8, 0))

    content = tk.Frame(row, bg=parent.cget("bg"))
    content.pack(side="left", fill="x", expand=True, padx=(16, 0))
    tk.Label(content, text=title, font=("Segoe UI", 12, "bold"), bg=parent.cget("bg"), fg=colors["title"], anchor="w").pack(anchor="w")
    tk.Label(content, text=desc, font=F_BODY, bg=parent.cget("bg"), fg=colors["desc"], anchor="w", wraplength=540, justify="left").pack(anchor="w", pady=(4, 0))


class _ProgressBar:
    SEG_W = 140

    def __init__(self, parent, width=620, height=6):
        self._w = width
        self._h = height
        self._pos = 0
        self._dir = 1
        self._job = None
        self._done = False

        self.canvas = tk.Canvas(parent, width=width, height=height, bg=BORDER, highlightthickness=0, bd=0)
        self._bar = self.canvas.create_rectangle(0, 0, 0, height, fill=GOLD_STRONG, outline="")

    def pack(self, **kw):
        self.canvas.pack(**kw)

    def start(self):
        self._done = False
        self._tick()

    def _tick(self):
        if self._done:
            return
        self._pos += self._dir * 10
        if self._pos + self.SEG_W >= self._w:
            self._dir = -1
        elif self._pos <= 0:
            self._dir = 1
        self.canvas.coords(self._bar, self._pos, 0, self._pos + self.SEG_W, self._h)
        self._job = self.canvas.after(16, self._tick)

    def stop(self, success=True):
        self._done = True
        if self._job:
            self.canvas.after_cancel(self._job)
        color = SUCCESS if success else ERROR
        self.canvas.coords(self._bar, 0, 0, self._w, self._h)
        self.canvas.itemconfig(self._bar, fill=color)


class LauncherWizard:
    W, H = 720, 640

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gold Credit - Assinatura Digital")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.root.update_idletasks()
        sx = (self.root.winfo_screenwidth() - self.W) // 2
        sy = (self.root.winfo_screenheight() - self.H) // 2
        self.root.geometry(f"{self.W}x{self.H}+{sx}+{sy}")

        self.result_queue: queue.Queue = queue.Queue()
        self.server_thread = None
        self.finalizado = False
        self._status_base = ""
        self._dots = 0
        self.loading_stage = 0
        self.loading_steps_host = None

        self.container = tk.Frame(self.root, bg=BG)
        self.container.pack(fill="both", expand=True)
        self._render_welcome()

    def _clear(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def _inner(self):
        inner = tk.Frame(self.container, bg=BG)
        inner.pack(fill="both", expand=True, padx=34, pady=24)
        return inner

    def _footer(self, inner):
        _divider(inner, color=BORDER, pady=(10, 0))
        row = tk.Frame(inner, bg=BG)
        row.pack(side="bottom", fill="x", pady=(12, 0))
        return row

    def _render_timeline(self, parent, states):
        steps = [
            ("01", "Validacao do ambiente", "Checagem de porta, dependencias e preparacao para iniciar o servico local."),
            ("02", "Inicializacao do servico local", "Subida do servidor em localhost:8765 para comunicar com o navegador."),
            ("03", "Execucao em segundo plano", "O aplicativo continua disponivel na bandeja do sistema para futuras assinaturas."),
        ]
        for idx, (number, title, desc) in enumerate(steps):
            _timeline_item(parent, number, title, desc, state=states[idx], last=idx == len(steps) - 1)

    def _render_welcome(self):
        self._clear()
        inner = self._inner()

        tk.Label(inner, text="Bem-vindo", font=F_DISPLAY, bg=BG, fg=TEXT, anchor="w").pack(anchor="w")
        tk.Label(
            inner,
            text="Este assistente prepara o servico local de assinatura digital ICP-Brasil na sua maquina, de forma simples e segura.",
            font=F_BODY,
            bg=BG,
            fg=MUTED,
            anchor="w",
            wraplength=630,
            justify="left",
        ).pack(anchor="w", pady=(6, 18))

        timeline_outer, timeline = _card(inner)
        timeline_outer.pack(fill="x", pady=(10, 0))
        timeline_body = tk.Frame(timeline, bg=SURFACE)
        timeline_body.pack(fill="x", padx=28, pady=22)
        _pill(timeline_body, "Fluxo de inicializacao", bg=GOLD_SOFT, fg=GOLD_STRONG).pack(anchor="w", pady=(0, 14))
        tk.Label(
            timeline_body,
            text="O app vai iniciar em tres passos",
            font=("Segoe UI", 14, "bold"),
            bg=SURFACE,
            fg=TEXT,
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            timeline_body,
            text="Abaixo esta a linha do tempo da inicializacao. Cada etapa prepara o aplicativo para rodar localmente com seguranca e ficar disponivel em segundo plano.",
            font=F_BODY,
            bg=SURFACE,
            fg=MUTED,
            anchor="w",
            wraplength=580,
            justify="left",
        ).pack(anchor="w", pady=(6, 18))
        self._render_timeline(timeline_body, ["pending", "pending", "pending"])

        btn_row = self._footer(inner)
        _btn_ghost(btn_row, "Cancelar", self.root.destroy).pack(side="right", padx=(10, 0))
        _btn_primary(btn_row, "Next", self._render_loading).pack(side="right")

    def _render_loading(self):
        self._clear()
        inner = self._inner()
        self.loading_stage = 0

        tk.Label(inner, text="Inicializando o servico local", font=F_DISPLAY, bg=BG, fg=TEXT, anchor="w").pack(anchor="w")
        self.status_var = tk.StringVar(value="Preparando ambiente")
        tk.Label(inner, textvariable=self.status_var, font=F_BODY, bg=BG, fg=GOLD_STRONG, anchor="w").pack(anchor="w", pady=(6, 14))

        self.progress = _ProgressBar(inner, width=620, height=6)
        self.progress.pack(anchor="w", pady=(0, 18))
        self.progress.start()

        steps_outer, steps_card = _card(inner)
        steps_outer.pack(fill="x", pady=(0, 16))
        self.loading_steps_host = tk.Frame(steps_card, bg=SURFACE)
        self.loading_steps_host.pack(fill="x", padx=22, pady=18)
        self._render_loading_timeline()

        console_outer, console = _card(inner)
        console_outer.pack(fill="both", expand=True)

        ch = tk.Frame(console, bg=SURFACE2)
        ch.pack(fill="x")
        tk.Label(ch, text="  Atividade", font=F_LABEL, bg=SURFACE2, fg=MUTED).pack(side="left", pady=8)
        _pill(ch, "Inicializando", bg=GOLD_SOFT, fg=GOLD_STRONG).pack(side="right", padx=12, pady=6)

        self.details = tk.Text(
            console,
            height=10,
            width=1,
            font=F_MONO,
            bg=CONSOLE,
            fg=CONSOLE_TEXT,
            bd=0,
            relief="flat",
            padx=16,
            pady=12,
            insertbackground=GOLD_STRONG,
            selectbackground=GOLD,
            state="disabled",
        )
        self.details.pack(fill="both", expand=True)
        self._log_line("Gold Credit - Assistente iniciado.")

        self._dots = 0
        self._status_base = "Preparando ambiente"
        threading.Thread(target=self._boot_service, daemon=True).start()
        self.root.after(150, self._poll_boot)
        self.root.after(300, self._animate_dots)

    def _render_loading_timeline(self):
        if self.loading_steps_host is None:
            return
        for widget in self.loading_steps_host.winfo_children():
            widget.destroy()

        _label_upper(self.loading_steps_host, "Linha do tempo")
        states = ["pending", "pending", "pending"]
        if self.loading_stage == 0:
            states = ["active", "pending", "pending"]
        elif self.loading_stage == 1:
            states = ["done", "active", "pending"]
        elif self.loading_stage >= 2:
            states = ["done", "done", "active"]
        self._render_timeline(self.loading_steps_host, states)

    def _animate_dots(self):
        if not hasattr(self, "status_var") or self.finalizado:
            return
        self._dots = (self._dots + 1) % 4
        suffix = "." * self._dots
        self.status_var.set(self._status_base + suffix)
        self.root.after(350, self._animate_dots)

    def _log_line(self, text: str):
        self.details.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.details.insert("end", f"[{ts}]  {text}\n")
        self.details.see("end")
        self.details.configure(state="disabled")

    def _boot_service(self):
        try:
            if not porta_livre(PORT):
                raise RuntimeError(
                    f"A porta {PORT} ja esta em uso.\n"
                    "Feche a instancia anterior e tente novamente."
                )

            self.result_queue.put(("log", "Ambiente validado com sucesso."))
            self.result_queue.put(("stage", 1))
            self.result_queue.put(("status", "Iniciando servidor local"))

            self.server_thread = threading.Thread(target=_run_flask, daemon=True, name="flask-gc")
            self.server_thread.start()

            for _ in range(30):
                if servico_online():
                    self.result_queue.put(("stage", 2))
                    self.result_queue.put(("ok", "Servico iniciado com sucesso."))
                    return
                time.sleep(0.35)

            raise RuntimeError("Timeout: o servico nao respondeu a tempo.")
        except Exception as exc:
            self.result_queue.put(("err", str(exc)))

    def _poll_boot(self):
        try:
            while True:
                kind, payload = self.result_queue.get_nowait()
                if kind == "log":
                    self._log_line(payload)
                elif kind == "stage":
                    self.loading_stage = payload
                    self._render_loading_timeline()
                elif kind == "status":
                    self._status_base = payload
                    self.status_var.set(payload)
                    self._log_line(payload)
                elif kind == "ok":
                    self.progress.stop(success=True)
                    self._status_base = payload
                    self.status_var.set(payload)
                    self._log_line(payload)
                    self._render_success()
                    return
                elif kind == "err":
                    self.progress.stop(success=False)
                    self._status_base = "Falha na inicializacao"
                    self.status_var.set(self._status_base)
                    self._log_line("ERRO: " + payload)
                    messagebox.showerror("Erro ao iniciar", payload, parent=self.root)
                    self._render_welcome()
                    return
        except queue.Empty:
            pass
        self.root.after(150, self._poll_boot)

    def _render_success(self):
        self._clear()
        inner = self._inner()

        tk.Label(inner, text="Tudo pronto", font=F_DISPLAY, bg=BG, fg=TEXT, anchor="w").pack(anchor="w")
        tk.Label(
            inner,
            text="O servico local foi iniciado com sucesso e esta pronto para receber assinaturas digitais.",
            font=F_BODY,
            bg=BG,
            fg=MUTED,
            anchor="w",
            wraplength=630,
        ).pack(anchor="w", pady=(6, 18))

        status_outer, status_card = _card(inner)
        status_outer.pack(fill="x", pady=(0, 16))
        body = tk.Frame(status_card, bg=SURFACE)
        body.pack(fill="x", padx=22, pady=18)

        _pill(body, "Servico ativo", bg="#EEF8F1", fg=SUCCESS).pack(anchor="w", pady=(0, 14))
        self._render_timeline(body, ["done", "done", "done"])

        info_outer, info_card = _card(inner)
        info_outer.pack(fill="x")
        info = tk.Frame(info_card, bg=SURFACE)
        info.pack(fill="x", padx=22, pady=18)
        _label_upper(info, "Resumo")

        rows = [
            ("Endereco", f"http://127.0.0.1:{PORT}"),
            ("Protocolo", "HTTP local - somente localhost"),
            ("Seguranca", "A chave privada permanece na maquina"),
        ]
        for idx, (label, value) in enumerate(rows):
            row = tk.Frame(info, bg=SURFACE)
            row.pack(fill="x", pady=(0, 8 if idx < len(rows) - 1 else 0))
            tk.Label(row, text=label, font=F_LABEL, bg=SURFACE, fg=MUTED, width=12, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=F_BODY, bg=SURFACE, fg=TEXT, anchor="w").pack(side="left")

        tk.Label(
            info,
            text="Ao concluir, o aplicativo continua ativo na bandeja do sistema para as proximas assinaturas.",
            font=F_SMALL,
            bg=SURFACE,
            fg=MUTED,
            anchor="w",
            wraplength=590,
        ).pack(anchor="w", pady=(14, 0))

        btn_row = self._footer(inner)
        _btn_primary(btn_row, "Concluir", self._finish).pack(side="right")

    def _finish(self):
        self.finalizado = True
        self.root.destroy()

    def run(self) -> bool:
        self.root.mainloop()
        return self.finalizado


def _criar_icone_tray():
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.ellipse([2, 2, size - 3, size - 3], fill=GOLD_STRONG)

    font = None
    for fname in ("segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"):
        try:
            font = ImageFont.truetype(fname, 22)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "GC", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    draw.text((x, y), "GC", fill=WHITE, font=font)
    return img


def _rodar_tray():
    import pystray  # noqa: PLC0415

    def abrir_status(icon, item):
        webbrowser.open(STATUS_URL)

    def encerrar(icon, item):
        log("Encerrado pelo menu da bandeja.")
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Gold Credit - Assinatura Digital", lambda *_: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Ver status do servico", abrir_status),
        pystray.MenuItem("Encerrar", encerrar),
    )

    icon = pystray.Icon(
        name="GoldCreditAssDigital",
        icon=_criar_icone_tray(),
        title="Gold Credit - Assinatura Digital",
        menu=menu,
    )
    icon.run()


def main():
    log("=" * 55)
    log("Gold Credit - Assistente de Assinatura Digital iniciado.")

    wizard = LauncherWizard()
    ok = wizard.run()

    if not ok:
        log("Inicializacao cancelada pelo usuario.")
        return

    log("Wizard concluido. Executando em modo bandeja.")
    _rodar_tray()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("ERRO FATAL:\n" + traceback.format_exc())
        messagebox.showerror(
            "Erro fatal - Gold Credit",
            "Falha inesperada ao iniciar o aplicativo.\n"
            "Consulte o arquivo log.txt para detalhes.",
        )
