"""
widgets.py - colour themes (dark / light), screen scaling and the small custom
widgets used by gui.py:  Card (rounded box, optional gradient), Pill (rounded
button), draw_icon (simple line icons) and a few helpers.
"""
import math
import sys
import types
import tkinter as tk
from tkinter import ttk

# ------------------------------------------------------------------ themes
PALETTES = {
    "dark": dict(
        bg="#0E1126", sidebar="#141833", card="#1A1F3F", inset="#252B55", border="#2E3566", entry="#11142B",
        text="#EEF0FF", muted="#8F96C4", accent="#7C6CFF", accent_hover="#9585FF", accent2="#22D3EE",
        good="#34D399", warn="#FBBF24", bad="#FB7185", warn_text="#FBBF24", bad_text="#FB7185",
        hover="#1F2550", row_bad="#3B1D36", row_warn="#3A2F1B", grad1="#6A5BFF", grad2="#1FB6E8"),
    "light": dict(
        bg="#EEF1FB", sidebar="#FFFFFF", card="#FFFFFF", inset="#EDEFFA", border="#D9DDF2", entry="#F6F7FE",
        text="#1A1D3A", muted="#6A7099", accent="#6A5BFF", accent_hover="#5546E8", accent2="#0EA5C9",
        good="#10B981", warn="#F59E0B", bad="#EF4444", warn_text="#B45309", bad_text="#DC2626",
        hover="#EEF0FD", row_bad="#FDECEE", row_warn="#FFF4DE", grad1="#6A5BFF", grad2="#22B8E8"),
}


class Theme:
    """Holds the current colours. Read them as T.bg, T.card, T.accent ..."""

    def __init__(self):
        self.use("dark")

    def use(self, name):
        self.__dict__.update(PALETTES[name])
        self.name = name


T = Theme()
FONT, BOLD, SMALL = ("Segoe UI", 10), ("Segoe UI", 10, "bold"), ("Segoe UI", 9)
H2, BIG = ("Segoe UI", 13, "bold"), ("Segoe UI", 26, "bold")

SCALE = 1.0          # 1.0 = normal screen, 1.5 = Windows display scaling of 150%


def px(number):
    """Design size -> real pixels (keeps the look sharp and the same size on every screen)."""
    return int(round(number * SCALE))


def blend(color1, color2, amount):
    """Mix two #RRGGBB colours. amount 0 = color1, 1 = color2."""
    a = [int(color1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(color2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


# ------------------------------------------------------------ window setup
def setup_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Treeview", background=T.card, fieldbackground=T.card, foreground=T.text, rowheight=px(32),
                    font=FONT, borderwidth=0, bordercolor=T.card, lightcolor=T.card, darkcolor=T.card)
    style.configure("Treeview.Heading", background=T.inset, foreground=T.muted, font=BOLD, relief="flat",
                    padding=px(7), borderwidth=0)
    style.map("Treeview.Heading", background=[("active", T.inset)])
    style.map("Treeview", background=[("selected", T.accent)], foreground=[("selected", "#FFFFFF")])
    style.layout("Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
        ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    style.configure("Vertical.TScrollbar", background=T.inset, troughcolor=T.card, bordercolor=T.card,
                    lightcolor=T.inset, darkcolor=T.inset, gripcount=0, width=px(10))
    style.map("Vertical.TScrollbar", background=[("active", T.border)])
    style.configure("TCombobox", fieldbackground=T.entry, background=T.inset, foreground=T.text, arrowcolor=T.muted,
                    bordercolor=T.border, lightcolor=T.border, darkcolor=T.border, padding=px(5))
    style.map("TCombobox", fieldbackground=[("readonly", T.entry)], foreground=[("readonly", T.text)],
              selectbackground=[("readonly", T.entry)], selectforeground=[("readonly", T.text)])
    for option, value in (("background", T.card), ("foreground", T.text),
                          ("selectBackground", T.accent), ("selectForeground", "#FFFFFF")):
        root.option_add(f"*TCombobox*Listbox.{option}", value)


def prepare_window(window, width, height):
    """Call first in every window: works out the screen scale, styles, size and position."""
    global SCALE
    if sys.platform == "win32":
        SCALE = max(1.0, window.winfo_fpixels("1i") / 96)
    setup_styles(window)
    screen_w, screen_h = window.winfo_screenwidth(), window.winfo_screenheight()
    w, h = min(px(width), screen_w - 40), min(px(height), screen_h - 90)
    window.geometry(f"{w}x{h}+{(screen_w - w) // 2}+{max(0, (screen_h - h) // 3)}")
    return w, h


# ----------------------------------------------------------------- drawing
def round_rect(canvas, x1, y1, x2, y2, r, **options):
    """Draw a rounded rectangle on a canvas."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **options)


def draw_icon(c, name, cx, cy, s, color, bg="#000000", tags="shape"):
    """Draw a small icon centred at (cx, cy); s is the half size."""
    lw = max(2, round(s / 4.5))
    line = dict(fill=color, width=lw, tags=tags, capstyle="round", joinstyle="round")
    if name == "grid":
        for dx in (-1, 1):
            for dy in (-1, 1):
                x, y = cx + dx * s * 0.52, cy + dy * s * 0.52
                round_rect(c, x - s * 0.4, y - s * 0.4, x + s * 0.4, y + s * 0.4, s * 0.12, fill=color, outline="", tags=tags)
    elif name == "pill":
        c.create_line(cx - s * 0.55, cy + s * 0.55, cx + s * 0.55, cy - s * 0.55, fill=color, width=s * 0.95, capstyle="round", tags=tags)
        c.create_line(cx - s * 0.34, cy - s * 0.34, cx + s * 0.34, cy + s * 0.34, fill=bg, width=max(1, lw - 1), tags=tags)
    elif name == "box":
        c.create_rectangle(cx - s * 0.8, cy - s * 0.3, cx + s * 0.8, cy + s * 0.85, outline=color, width=lw, tags=tags)
        c.create_rectangle(cx - s * 0.95, cy - s * 0.85, cx + s * 0.95, cy - s * 0.3, outline=color, width=lw, tags=tags)
        c.create_line(cx - s * 0.25, cy + s * 0.05, cx + s * 0.25, cy + s * 0.05, **line)
    elif name == "bag":
        c.create_arc(cx - s * 0.45, cy - s * 0.95, cx + s * 0.45, cy - s * 0.05, start=0, extent=180, style="arc", outline=color, width=lw, tags=tags)
        round_rect(c, cx - s * 0.85, cy - s * 0.3, cx + s * 0.85, cy + s * 0.9, s * 0.2, fill="", outline=color, width=lw, tags=tags)
    elif name == "chart":
        for i, height in enumerate((0.55, 1.15, 0.85)):
            x = cx + (i - 1) * s * 0.7
            round_rect(c, x - s * 0.25, cy + s * 0.85 - height * s, x + s * 0.25, cy + s * 0.85, s * 0.1, fill=color, outline="", tags=tags)
    elif name == "warn":
        c.create_polygon(cx, cy - s * 0.9, cx + s * 0.95, cy + s * 0.75, cx - s * 0.95, cy + s * 0.75, outline=color, fill="", width=lw, joinstyle="round", tags=tags)
        c.create_line(cx, cy - s * 0.25, cx, cy + s * 0.18, **line)
        c.create_oval(cx - lw / 2, cy + s * 0.42, cx + lw / 2, cy + s * 0.42 + lw, fill=color, outline="", tags=tags)
    elif name == "clock":
        c.create_oval(cx - s * 0.9, cy - s * 0.9, cx + s * 0.9, cy + s * 0.9, outline=color, width=lw, tags=tags)
        c.create_line(cx, cy, cx, cy - s * 0.5, **line)
        c.create_line(cx, cy, cx + s * 0.4, cy + s * 0.2, **line)
    elif name == "bell":
        c.create_arc(cx - s * 0.7, cy - s * 0.85, cx + s * 0.7, cy + s * 0.55, start=0, extent=180, style="arc", outline=color, width=lw, tags=tags)
        c.create_line(cx - s * 0.7, cy - s * 0.15, cx - s * 0.7, cy + s * 0.5, cx - s * 0.95, cy + s * 0.6,
                      cx + s * 0.95, cy + s * 0.6, cx + s * 0.7, cy + s * 0.5, cx + s * 0.7, cy - s * 0.15, **line)
        c.create_oval(cx - s * 0.2, cy + s * 0.78, cx + s * 0.2, cy + s, fill=color, outline="", tags=tags)
    elif name == "moon":
        c.create_oval(cx - s * 0.85, cy - s * 0.85, cx + s * 0.85, cy + s * 0.85, fill=color, outline="", tags=tags)
        c.create_oval(cx - s * 0.3, cy - s * 1.0, cx + s * 1.2, cy + s * 0.55, fill=bg, outline="", tags=tags)
    elif name == "sun":
        c.create_oval(cx - s * 0.45, cy - s * 0.45, cx + s * 0.45, cy + s * 0.45, fill=color, outline="", tags=tags)
        for k in range(8):
            a = k * math.pi / 4
            c.create_line(cx + math.cos(a) * s * 0.75, cy + math.sin(a) * s * 0.75,
                          cx + math.cos(a) * s * 1.05, cy + math.sin(a) * s * 1.05, **line)
    elif name == "logout":
        c.create_line(cx - s * 0.1, cy - s * 0.8, cx - s * 0.8, cy - s * 0.8, cx - s * 0.8, cy + s * 0.8, cx - s * 0.1, cy + s * 0.8, **line)
        c.create_line(cx - s * 0.2, cy, cx + s * 0.85, cy, **line)
        c.create_line(cx + s * 0.45, cy - s * 0.4, cx + s * 0.85, cy, cx + s * 0.45, cy + s * 0.4, **line)
    elif name == "search":
        c.create_oval(cx - s * 0.8, cy - s * 0.8, cx + s * 0.35, cy + s * 0.35, outline=color, width=lw, tags=tags)
        c.create_line(cx + s * 0.1, cy + s * 0.1, cx + s * 0.85, cy + s * 0.85, **line)


class Card(tk.Canvas):
    """A rounded box. Put widgets in card.inner, or draw on it directly with card.text().
    gradient=(color1, color2) makes a colourful card; decorate(card, w, h) can draw extras."""

    def __init__(self, parent, bg=None, radius=20, pad=16, width=10, height=10, gradient=None, inner=True, border=True):
        super().__init__(parent, width=px(width), height=px(height), bg=parent.cget("bg"), highlightthickness=0)
        self.fill = bg or T.card
        self.radius, self.pad = px(radius), px(pad)
        self.gradient, self.border, self.decorate = gradient, border, None
        self.inner = tk.Frame(self, bg=self.fill)
        state = "normal" if inner and not gradient else "hidden"
        self.window = self.create_window(self.pad, self.pad, window=self.inner, anchor="nw", state=state)
        self.bind("<Configure>", self.draw)

    def text(self, x, y, text, **options):
        return self.create_text(x, y, text=text, **options)

    def draw(self, event):
        w, h, r = event.width, event.height, self.radius
        self.delete("shape")
        if self.gradient:
            color1, color2 = self.gradient
            x = 0
            while x < w:                         # vertical strips = horizontal gradient
                step = 1 if (x < r or x > w - r) else 4          # thin strips at the rounded corners
                edge = min(x + step / 2, w - x - step / 2)
                inset = r - math.sqrt(max(0, r * r - (r - edge) ** 2)) if edge < r else 0
                self.create_rectangle(x, inset, x + step + 1, h - inset, fill=blend(color1, color2, x / max(1, w)),
                                      outline="", tags="shape")
                x += step
        else:
            round_rect(self, 1, 1, w - 1, h - 1, r, fill=self.fill, outline=T.border if self.border else "", tags="shape")
        if self.decorate:
            self.decorate(self, w, h)
        self.tag_lower("shape")
        self.itemconfigure(self.window, width=max(1, w - 2 * self.pad), height=max(1, h - 2 * self.pad))

    def redraw(self):
        self.draw(types.SimpleNamespace(width=self.winfo_width(), height=self.winfo_height()))


class Pill(tk.Canvas):
    """A rounded button. style: primary, soft, danger, good, nav, navactive."""

    def __init__(self, parent, text, command, style="primary", width=110, height=38, anchor="center", icon=None):
        super().__init__(parent, width=px(width), height=px(height), bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
        self.text, self.command, self.anchor, self.icon, self.style = text, command, anchor, icon, style
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", lambda e: self.draw(True))
        self.bind("<Leave>", lambda e: self.draw())

    def colors(self):
        """(background, text colour, hover colour)"""
        return {"primary": (T.accent, "#FFFFFF", T.accent_hover),
                "soft": (T.inset, T.text, T.border),
                "danger": (T.bad, "#FFFFFF", blend(T.bad, "#000000", 0.18)),
                "good": (T.good, "#04281D", blend(T.good, "#000000", 0.15)),
                "nav": (self.cget("bg"), T.muted, T.hover),
                "navactive": (T.accent, "#FFFFFF", T.accent)}[self.style]

    def set_style(self, style):
        self.style = style
        self.draw()

    def draw(self, hovering=False):
        bg, fg, hover = self.colors()
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        round_rect(self, 1, 1, w - 1, h - 1, h / 2, fill=hover if hovering else bg, outline="")
        if self.icon:
            draw_icon(self, self.icon, px(26), h / 2, px(8), fg, hover if hovering else bg, tags="icon")
        if self.anchor == "w":
            self.create_text(px(52) if self.icon else px(20), h / 2, text=self.text, fill=fg, font=BOLD, anchor="w")
        else:
            self.create_text(w / 2, h / 2, text=self.text, fill=fg, font=BOLD)


# ----------------------------------------------------------------- helpers
def label(parent, text, fg=None, font=FONT, **options):
    options.setdefault("bg", parent.cget("bg"))
    return tk.Label(parent, text=text, fg=fg or T.text, font=font, **options)


def entry(parent, variable, width=20, **options):
    return tk.Entry(parent, textvariable=variable, width=width, relief="flat", bg=T.entry, fg=T.text, font=FONT,
                    highlightthickness=1, highlightbackground=T.border, highlightcolor=T.accent,
                    insertbackground=T.text, **options)
