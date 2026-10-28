
import tkinter as tk

root = tk.Tk()
root.title("Nha Rong Co Tu")
root.geometry("800x480")
root.configure(bg="#f3e8d0")

title = tk.Label(
    root,
    text="NHA RONG CO TU",
    font=("Arial", 28, "bold"),
    bg="#f3e8d0",
    fg="#6b3e1e"
)
title.pack(pady=40)

message = tk.Label(
    root,
    text="Xin chao! Toi la gia lang.\nHay dua nhan vat vao de nghe cau chuyen!",
    font=("Arial", 18),
    bg="#f3e8d0",
    fg="#333333",
    wraplength=700
)
message.pack(pady=30)

root.mainloop()
