#!/usr/bin/env python
# coding: utf-8

import tkinter as tk

class ToggledFrame(tk.Frame):

    def __init__(self, master, text="", bg="", *args, **options):
        tk.Frame.__init__(self, master, bg=bg, *args, **options)

        self.show = tk.IntVar()
        self.show.set(0)

        self.title_frame = tk.Frame(self, bg=bg)
        self.title_frame.pack(fill="x", expand=1)

        tk.Label(self.title_frame,
            text=text,
            bg=bg,
            ).pack(side="left", fill="x", expand=1)

        self.toggle_button = tk.Checkbutton(self.title_frame,
            width=2,
            text='+',
            command=self.toggle,
            bg=bg,
            variable=self.show)
        self.toggle_button.pack(side="left")

        self.sub_frame = tk.Frame(self, bg=bg, relief="sunken", borderwidth=1)

    def toggle(self):
        if bool(self.show.get()):
            self.sub_frame.pack(fill="x", expand=1)
            self.toggle_button.configure(text='-')
        else:
            self.sub_frame.forget()
            self.toggle_button.configure(text='+')
