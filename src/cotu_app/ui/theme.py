"""Shared colors and native touch controls for the 800×480 kiosk."""

BG = "#F4F1E9"
SURFACE = "#FFFEFB"
INK = "#233E36"
MUTED = "#5C6E64"
PRIMARY = "#245D49"
PRIMARY_PRESSED = "#174534"
ACCENT = "#A4492F"
SOFT = "#E5EDE4"
SELECTED = "#F4E5C9"
LINE = "#D9DED3"
FONT = "DejaVu Sans"


def configure_styles(root):
    from tkinter import ttk
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Story.TFrame", background=BG)
    style.configure("Paper.TFrame", background=SURFACE)
    style.configure("Story.TNotebook", background=BG, borderwidth=0, tabmargins=0)
    # Navigation uses native Buttons with larger touch areas below the content.
    style.layout("Story.TNotebook.Tab", [])
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=INK, font=(FONT, 10))
    style.configure("TButton", font=(FONT, 11, "bold"), padding=(12, 13),
                    background=SOFT, foreground=INK, borderwidth=0)
    style.map("TButton", background=[("active", "#D5E2D3"), ("disabled", "#EBEDE8")],
              foreground=[("disabled", "#6C776F")])
    style.configure("Story.TButton", font=(FONT, 11, "bold"), padding=(12, 13))
    for name, color, active in (("Primary", PRIMARY, PRIMARY_PRESSED),
                                ("Mic", ACCENT, "#863A25"),
                                ("Header", PRIMARY, PRIMARY_PRESSED)):
        style.configure(f"{name}.TButton", font=(FONT, 11, "bold"), padding=(12, 13),
                        background=color, foreground="white", borderwidth=0)
        style.map(f"{name}.TButton", background=[("disabled", "#E1E5DD"), ("active", active)],
                  foreground=[("disabled", "#667268")])
    for name in ("TEntry", "Story.TEntry"):
        style.configure(name, padding=10, fieldbackground=SURFACE,
                        foreground=INK, bordercolor=LINE, insertcolor=PRIMARY)
    style.configure("Story.TCombobox", padding=10, foreground=INK)
    style.configure("Story.Vertical.TScrollbar", arrowsize=24, width=24,
                    background=SOFT, troughcolor=BG)
