"""
gui.py - all screens (Tkinter).   Colours and custom widgets are in widgets.py.

  BasePage                 parent of every page (inheritance)
  DashboardPage, MedicinesPage, InventoryPage, SalesPage, ReportsPage
                           each page overrides build() and refresh()  (polymorphism)
  LoginWindow              login screen
  DrugManagementSystem     main window: sidebar, header, page switching, dark/light theme
"""
import csv
import math
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

from drug import Drug, CATEGORIES, LOW_STOCK_LIMIT
from widgets import (T, px, blend, prepare_window, setup_styles, round_rect, draw_icon,
                     Card, Pill, label, entry, FONT, BOLD, SMALL, H2, BIG)

DRUG_COLUMNS = ("ID", "Name", "Category", "Manufacturer", "Price (Rs.)", "Quantity", "Expiry Date", "Status")
DRUG_WIDTHS = (70, 190, 90, 140, 100, 85, 105, 90)
SMALL_COLUMNS = ("ID", "Name", "Qty", "Expiry")
SMALL_WIDTHS = (60, 180, 50, 100)


# -------------------------------------------------------------- table helpers
def table_card(parent, title, columns, widths, height=6, color=None):
    """A rounded card with a title and a Treeview table. Returns (card, tree)."""
    card = Card(parent)
    card.title_label = label(card.inner, title, fg=color, font=H2)
    if title:
        card.title_label.pack(anchor="w", pady=(0, 8))
    frame = tk.Frame(card.inner, bg=T.card)
    frame.pack(fill="both", expand=True)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
    for column, width in zip(columns, widths):
        tree.heading(column, text=column)
        tree.column(column, width=px(width), anchor="w")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y", padx=(6, 0))
    tree.tag_configure("expired", background=T.row_bad, foreground=T.bad_text)   # expired = red
    tree.tag_configure("low", background=T.row_warn, foreground=T.warn_text)     # low stock = amber
    return card, tree


def drug_tag(drug):
    return ("expired",) if drug.is_expired() else ("low",) if drug.is_low_stock() else ()


def fill_drug_tree(tree, drugs):
    tree.delete(*tree.get_children())
    for d in drugs:    # iid = drug id, so the ID is read back exactly as typed
        tree.insert("", "end", iid=d.drug_id, tags=drug_tag(d), values=(
            d.drug_id, d.name, d.category, d.manufacturer, f"{d.price:.2f}", d.quantity, d.expiry_date, d.status()))


def fill_small_tree(tree, drugs):
    tree.delete(*tree.get_children())
    for d in drugs:
        tree.insert("", "end", iid=d.drug_id, tags=drug_tag(d), values=(d.drug_id, d.name, d.quantity, d.expiry_date))


def stat_card(parent, title, note, icon, color):
    """Overview card drawn on a canvas. color=None gives the colourful gradient card."""
    hero = color is None
    card = Card(parent, height=124, inner=False, gradient=(T.grad1, T.grad2) if hero else None, border=not hero)
    main, sub = ("#FFFFFF", "#E6E8FF") if hero else (T.text, T.muted)
    card.text(px(22), px(28), title, fill=sub, font=FONT, anchor="w")
    card.value = card.text(px(22), px(68), "0", fill=main, font=BIG, anchor="w")
    card.text(px(22), px(102), note, fill=sub, font=SMALL, anchor="w")

    def decorate(c, w, h):          # the round icon on the right
        cx, cy, r = w - px(48), px(44), px(25)
        circle = blend(T.grad1, "#FFFFFF", 0.3) if hero else blend(T.card, color, 0.2)
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=circle, outline="", tags="shape")
        draw_icon(c, icon, cx, cy, px(10), "#FFFFFF" if hero else color, circle)
    card.decorate = decorate
    return card


# -------------------------------------------------------------------- pages
class BasePage(tk.Frame):
    """Parent of every page. Each child page overrides build() and refresh()."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=T.bg)
        self.app, self.inventory, self.sales = app, app.inventory, app.sales
        self.build()

    def build(self):
        raise NotImplementedError

    def refresh(self):
        pass


class DashboardPage(BasePage):
    def build(self):
        self.mode = "stock"
        self.drugs, self.daily, self.top, self.stats = [], [], [], {"total": 0, "low_stock": 0, "expired": 0}
        self.columnconfigure((0, 1, 2, 3), weight=1, uniform="col")
        self.rowconfigure((1, 2), weight=1)

        specs = [("total", "Total Medicines", "medicines in the store", "pill", None),
                 ("available_stock", "Available Stock", "units that are not expired", "box", T.good),
                 ("low_stock", "Low Stock", f"{LOW_STOCK_LIMIT} units or fewer", "warn", T.warn),
                 ("expired", "Expired", "remove from shelf", "clock", T.bad)]
        self.cards = {}
        for i, (key, title, note, icon, color) in enumerate(specs):
            card = stat_card(self, title, note, icon, color)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 7, 0 if i == 3 else 7), pady=(0, 14))
            self.cards[key] = card

        # --- chart card with two tabs: stock levels / sales trend
        chart_card = Card(self)
        chart_card.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(0, 7), pady=(0, 14))
        head = tk.Frame(chart_card.inner, bg=T.card)
        head.pack(fill="x", pady=(0, 6))
        self.chart_title = label(head, "Stock Levels", font=H2)
        self.chart_title.pack(side="left")
        self.tab_sales = Pill(head, "Sales (7 days)", lambda: self.set_mode("sales"), "soft", width=120, height=30)
        self.tab_sales.pack(side="right")
        self.tab_stock = Pill(head, "Stock", lambda: self.set_mode("stock"), "primary", width=80, height=30)
        self.tab_stock.pack(side="right", padx=6)
        self.chart = tk.Canvas(chart_card.inner, bg=T.card, highlightthickness=0)
        self.chart.pack(fill="both", expand=True)
        self.chart.bind("<Configure>", lambda e: self.draw_chart())

        # --- donut: stock status
        donut_card = Card(self)
        donut_card.grid(row=1, column=2, sticky="nsew", padx=7, pady=(0, 14))
        label(donut_card.inner, "Stock Status", font=H2).pack(anchor="w")
        self.donut = tk.Canvas(donut_card.inner, bg=T.card, highlightthickness=0)
        self.donut.pack(fill="both", expand=True)
        self.donut.bind("<Configure>", lambda e: self.draw_donut())

        # --- top selling medicines
        top_card = Card(self)
        top_card.grid(row=1, column=3, rowspan=2, sticky="nsew", padx=(7, 0))
        label(top_card.inner, "Top Selling Medicine", font=H2).pack(anchor="w")
        self.top_canvas = tk.Canvas(top_card.inner, bg=T.card, highlightthickness=0)
        self.top_canvas.pack(fill="both", expand=True, pady=(8, 0))
        self.top_canvas.bind("<Configure>", lambda e: self.draw_top())

        # --- low-stock and expired monitoring table
        card, self.tree = table_card(self, "Needs Attention (low stock and expired)", SMALL_COLUMNS + ("Status",),
                                     SMALL_WIDTHS + (100,), height=4)
        card.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=(0, 7))

    def refresh(self):
        self.stats = self.inventory.stats()
        for key, card in self.cards.items():
            card.itemconfigure(card.value, text=f"{self.stats[key]:,}")
        self.drugs = self.inventory.get_all()[:12]
        self.daily = self.sales.daily_totals(7)
        self.top = self.sales.top_selling()
        self.draw_chart()
        self.draw_donut()
        self.draw_top()
        self.tree.delete(*self.tree.get_children())
        for d in self.inventory.low_stock() + self.inventory.expired():
            self.tree.insert("", "end", iid=d.drug_id, tags=drug_tag(d),
                             values=(d.drug_id, d.name, d.quantity, d.expiry_date, d.status()))

    def set_mode(self, mode):
        self.mode = mode
        self.chart_title.config(text="Stock Levels" if mode == "stock" else "Sales Analytics")
        self.tab_stock.set_style("primary" if mode == "stock" else "soft")
        self.tab_sales.set_style("primary" if mode == "sales" else "soft")
        self.draw_chart()

    # ----- charts (drawn with canvas shapes)
    def draw_chart(self):
        self.chart.delete("all")
        w, h = self.chart.winfo_width(), self.chart.winfo_height()
        if h < px(80):
            return
        if self.mode == "stock":
            self.draw_bars(w, h)
        else:
            self.draw_sales(w, h)

    def draw_bars(self, w, h):
        """One rounded bar per medicine: the track is the maximum, the colour shows the stock."""
        c, drugs = self.chart, self.drugs
        if not drugs:
            return
        slot = w / len(drugs)
        bar = min(px(36), slot * 0.6)
        top, bottom = px(6), h - px(22)
        biggest = max(d.quantity for d in drugs) or 1
        for i, d in enumerate(drugs):
            x = slot * i + slot / 2
            round_rect(c, x - bar / 2, top, x + bar / 2, bottom, bar / 2, fill=T.inset, outline="")
            height = max(bar, (bottom - top) * d.quantity / biggest)
            color = T.bad if d.is_expired() else T.warn if d.is_low_stock() else T.accent
            round_rect(c, x - bar / 2, bottom - height, x + bar / 2, bottom, bar / 2, fill=color, outline="")
            c.create_text(x, bottom - height + bar / 2, text=d.quantity, font=SMALL,
                          fill="#1B1403" if color == T.warn else "#FFFFFF")
            c.create_text(x, h - px(8), text=d.drug_id, fill=T.muted, font=SMALL)

    def draw_sales(self, w, h):
        """Area/line chart of the money earned in the last 7 days."""
        c, data = self.chart, self.daily
        left, right, top, bottom = px(50), px(16), px(34), h - px(26)
        top_value = (max(v for _, v in data) or 1) * 1.15
        for i in range(4):                                  # grid lines + y labels
            y = bottom - (bottom - top) * i / 3
            c.create_line(left, y, w - right, y, fill=T.inset)
            c.create_text(left - px(8), y, text=f"{top_value * i / 3:,.0f}", fill=T.muted, font=SMALL, anchor="e")
        xs = [left + (w - left - right) * i / (len(data) - 1) for i in range(len(data))]
        ys = [bottom - (bottom - top) * v / top_value for _, v in data]
        points = [p for xy in zip(xs, ys) for p in xy]
        c.create_polygon([xs[0], bottom] + points + [xs[-1], bottom], fill=blend(T.card, T.accent, 0.22), outline="")
        c.create_line(*points, fill=T.accent, width=px(3), joinstyle="round", capstyle="round")
        best = max(range(len(data)), key=lambda i: data[i][1])
        for i, (name, value) in enumerate(data):
            r = px(5)
            c.create_oval(xs[i] - r, ys[i] - r, xs[i] + r, ys[i] + r, fill=T.card, outline=T.accent, width=px(2))
            c.create_text(xs[i], h - px(9), text=name, fill=T.muted, font=SMALL)
        bubble = px(38)
        round_rect(c, xs[best] - bubble, ys[best] - px(36), xs[best] + bubble, ys[best] - px(14), px(8), fill=T.accent, outline="")
        c.create_text(xs[best], ys[best] - px(25), text=f"Rs.{data[best][1]:,.0f}", fill="#FFFFFF", font=SMALL)

    def draw_donut(self):
        c = self.donut
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if h < px(120):
            return
        total, low, expired = self.stats["total"], self.stats["low_stock"], self.stats["expired"]
        parts = [("Normal", total - low - expired, T.accent), ("Low stock", low, T.warn), ("Expired", expired, T.bad)]
        thick = px(15)
        size = min(w - px(20), h - px(84))
        cx, cy = w / 2, size / 2 + px(8)
        box = (cx - size / 2 + thick / 2, cy - size / 2 + thick / 2, cx + size / 2 - thick / 2, cy + size / 2 - thick / 2)
        c.create_oval(*box, outline=T.inset, width=thick)
        start = 90
        for name, count, color in parts:
            if total and count:
                extent = -min(359.9, 360 * count / total)
                c.create_arc(*box, start=start, extent=extent, style="arc", outline=color, width=thick)
                start += extent
        c.create_text(cx, cy - px(6), text=str(total), fill=T.text, font=("Segoe UI", 18, "bold"))
        c.create_text(cx, cy + px(12), text="total", fill=T.muted, font=("Segoe UI", 8))
        for i, (name, count, color) in enumerate(parts):    # legend
            y = cy + size / 2 + px(20) + i * px(20)
            c.create_oval(px(20), y - px(5), px(30), y + px(5), fill=color, outline="")
            c.create_text(px(40), y, text=name, fill=T.text, font=FONT, anchor="w")
            c.create_text(w - px(20), y, text=str(count), fill=T.muted, font=BOLD, anchor="e")

    def draw_top(self):
        c = self.top_canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if not self.top:
            c.create_text(w / 2, h / 2, text="No sales yet", fill=T.muted, font=FONT)
            return
        colors = [(T.accent, "#FFFFFF"), (T.accent2, "#06222B"), (T.good, "#04281D")]
        slot, pill = w / 3, min(px(54), w / 3 * 0.7)
        bottom = h - px(46)
        for i, (name, units, money) in enumerate(self.top):
            x = slot * i + slot / 2
            round_rect(c, x - pill / 2, px(4), x + pill / 2, bottom, pill / 2, fill=T.inset, outline="")
            height = max(pill * 1.8, (bottom - px(4)) * units / self.top[0][1])
            bg, fg = colors[i]
            round_rect(c, x - pill / 2, bottom - height, x + pill / 2, bottom, pill / 2, fill=bg, outline="")
            c.create_text(x, bottom - height / 2, text=name[:max(4, int(height / px(9)))], angle=90, fill=fg, font=BOLD)
            c.create_text(x, bottom + px(16), text=f"{units} sold", fill=T.text, font=SMALL)
            c.create_text(x, bottom + px(32), text=f"Rs.{money:,.0f}", fill=T.muted, font=SMALL)


class MedicinesPage(BasePage):
    def build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        fields = [("Drug ID", "id"), ("Medicine Name", "name"), ("Category", "category"),
                  ("Manufacturer", "manufacturer"), ("Price (Rs.)", "price"),
                  ("Quantity", "quantity"), ("Expiry (YYYY-MM-DD)", "expiry")]
        self.vars = {key: tk.StringVar() for _, key in fields}
        self.vars["category"].set(CATEGORIES[0])

        # --- the form
        form = Card(self, height=222)
        form.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        box = form.inner
        box.columnconfigure((0, 1, 2, 3), weight=1, uniform="f")
        for i, (text, key) in enumerate(fields):
            row, col = (i // 4) * 2, i % 4
            label(box, text, fg=T.muted).grid(row=row, column=col, sticky="w", padx=6)
            if key == "category":
                widget = ttk.Combobox(box, textvariable=self.vars[key], values=CATEGORIES, state="readonly")
            else:
                widget = entry(box, self.vars[key])
            widget.grid(row=row + 1, column=col, sticky="ew", padx=6, pady=(2, 8), ipady=4)
        buttons = tk.Frame(box, bg=T.card)
        buttons.grid(row=4, column=0, columnspan=4, sticky="w", padx=6, pady=(4, 0))
        for text, command, style in (("Add", self.add, "primary"), ("Update", self.update, "good"),
                                     ("Delete", self.delete, "danger"), ("Clear", self.clear, "soft")):
            Pill(buttons, text, command, style, width=100).pack(side="left", padx=(0, 8))
        self.tip = label(buttons, "", fg=T.muted)
        self.tip.pack(side="left", padx=10)

        # --- the search bar
        bar = tk.Frame(self, bg=T.bg)
        bar.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        label(bar, "Search by name or ID:", font=BOLD).pack(side="left")
        self.search_var = tk.StringVar()
        box_entry = entry(bar, self.search_var, width=30)
        box_entry.pack(side="left", padx=10, ipady=5)
        box_entry.bind("<Return>", lambda e: self.search())
        Pill(bar, "Search", self.search, "primary", width=100).pack(side="left", padx=(0, 8))
        Pill(bar, "Show All", self.show_all, "soft", width=100).pack(side="left")

        # --- the table
        card, self.tree = table_card(self, "", DRUG_COLUMNS, DRUG_WIDTHS, height=10)
        card.grid(row=2, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def refresh(self):
        fill_drug_tree(self.tree, self.inventory.search(self.search_var.get()))

    def read_form(self):
        """Turn the form into a Drug object (shows an error and returns None if invalid)."""
        v = self.vars
        try:
            return Drug.create(v["id"].get(), v["name"].get(), v["category"].get(), v["manufacturer"].get(),
                               v["price"].get(), v["quantity"].get(), v["expiry"].get())
        except ValueError as error:
            messagebox.showerror("Invalid input", str(error))

    def add(self):
        drug = self.read_form()
        if drug is None:
            return
        try:
            self.inventory.add_drug(drug)
        except ValueError as error:
            messagebox.showerror("Cannot add medicine", str(error))
            return
        messagebox.showinfo("Success", f"{drug.name} was added successfully.")
        self.clear()
        self.refresh()

    def update(self):
        drug = self.read_form()
        if drug is None:
            return
        try:
            self.inventory.update_drug(drug)
        except ValueError as error:
            messagebox.showerror("Cannot update medicine", str(error))
            return
        messagebox.showinfo("Success", f"{drug.name} was updated successfully.")
        self.clear()
        self.refresh()

    def delete(self):
        drug_id = self.vars["id"].get().strip().upper()
        if not drug_id:
            messagebox.showwarning("Select a medicine", "Click a row (or type a Drug ID) first.")
            return
        if not messagebox.askyesno("Confirm delete", f"Delete medicine {drug_id}? This cannot be undone."):
            return
        try:
            self.inventory.delete_drug(drug_id)
        except ValueError as error:
            messagebox.showerror("Cannot delete medicine", str(error))
            return
        messagebox.showinfo("Success", f"Medicine {drug_id} was deleted.")
        self.clear()
        self.refresh()

    def search(self):
        results = self.inventory.search(self.search_var.get())
        fill_drug_tree(self.tree, results)
        if not results:
            messagebox.showinfo("Search", "No medicines matched your search.")

    def show_all(self):
        self.search_var.set("")
        self.refresh()

    def clear(self):
        for key, variable in self.vars.items():
            variable.set(CATEGORIES[0] if key == "category" else "")
        self.tip.config(text="")
        self.tree.selection_remove(self.tree.selection())

    def on_select(self, event=None):
        """Clicking a row copies it into the form."""
        selected = self.tree.selection()
        drug = self.inventory.get_drug(selected[0]) if selected else None
        if drug is None:
            return
        for key, value in (("id", drug.drug_id), ("name", drug.name), ("category", drug.category),
                           ("manufacturer", drug.manufacturer), ("price", f"{drug.price:.2f}"),
                           ("quantity", drug.quantity), ("expiry", drug.expiry_date)):
            self.vars[key].set(value)
        self.tip.config(text=drug.storage_advice())      # polymorphic call


class InventoryPage(BasePage):
    def build(self):
        self.ids = []
        self.columnconfigure((0, 1), weight=1, uniform="half")
        self.rowconfigure(1, weight=1)

        top = Card(self, height=84)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        row = top.inner
        label(row, "Medicine:", font=BOLD).pack(side="left")
        self.combo = ttk.Combobox(row, state="readonly", width=34)
        self.combo.pack(side="left", padx=8)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.show_stock())
        self.stock_label = label(row, "Current stock: -", fg=T.accent, font=BOLD)
        self.stock_label.pack(side="left", padx=10)
        self.amount = tk.StringVar(value="1")
        label(row, "Amount:", font=BOLD).pack(side="left", padx=(8, 4))
        entry(row, self.amount, width=6).pack(side="left", padx=(0, 10), ipady=4)
        Pill(row, "Increase", lambda: self.change(1), "good", width=100).pack(side="left", padx=(0, 8))
        Pill(row, "Decrease", lambda: self.change(-1), "danger", width=100).pack(side="left")

        card, self.low_tree = table_card(self, "Low-Stock Medicines", SMALL_COLUMNS, SMALL_WIDTHS, 10, T.warn_text)
        card.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        card, self.exp_tree = table_card(self, "Expired Medicines", SMALL_COLUMNS, SMALL_WIDTHS, 10, T.bad_text)
        card.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

    def selected_id(self):
        index = self.combo.current()
        return self.ids[index] if 0 <= index < len(self.ids) else None

    def show_stock(self):
        drug = self.inventory.get_drug(self.selected_id()) if self.selected_id() else None
        self.stock_label.config(text=f"Current stock: {drug.quantity}" if drug else "Current stock: -")

    def refresh(self):
        current = self.selected_id()
        drugs = self.inventory.get_all()
        self.ids = [d.drug_id for d in drugs]
        self.combo["values"] = [f"{d.drug_id} - {d.name}" for d in drugs]
        if current in self.ids:
            self.combo.current(self.ids.index(current))
        else:
            self.combo.set("")
        self.show_stock()
        fill_small_tree(self.low_tree, self.inventory.low_stock())
        fill_small_tree(self.exp_tree, self.inventory.expired())

    def change(self, sign):
        """sign = +1 to increase stock, -1 to decrease it."""
        drug_id = self.selected_id()
        if drug_id is None:
            messagebox.showwarning("Select a medicine", "Please choose a medicine first.")
            return
        try:
            amount = int(self.amount.get().strip())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid amount", "Amount must be a whole number greater than zero.")
            return
        try:
            new_quantity = self.inventory.adjust_stock(drug_id, sign * amount)
        except ValueError as error:
            messagebox.showerror("Stock error", str(error))
            return
        messagebox.showinfo("Stock updated", f"New stock level: {new_quantity} units.")
        self.refresh()


class SalesPage(BasePage):
    def build(self):
        self.drugs = []
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        form = Card(self, width=350)
        form.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        box = form.inner
        label(box, "New Sale", font=H2).pack(anchor="w", pady=(0, 10))
        label(box, "Select medicine", fg=T.muted).pack(anchor="w")
        self.combo = ttk.Combobox(box, state="readonly", width=34)
        self.combo.pack(pady=(2, 10), ipady=3)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.show_info())
        self.info = label(box, "", justify="left", fg=T.text)
        self.info.pack(anchor="w", pady=(0, 10))
        label(box, "Quantity", fg=T.muted).pack(anchor="w")
        self.qty = tk.StringVar(value="1")
        self.qty.trace_add("write", lambda *args: self.show_total())    # total updates while typing
        entry(box, self.qty, width=12).pack(anchor="w", pady=(2, 14), ipady=4)

        total = Card(box, gradient=(T.grad1, T.grad2), height=92, radius=18, inner=False, border=False)
        total.pack(fill="x", pady=(0, 14))
        total.text(px(20), px(26), "Total price", fill="#E6E8FF", font=FONT, anchor="w")
        self.total_id = total.text(px(20), px(60), "Rs. 0.00", fill="#FFFFFF", font=("Segoe UI", 22, "bold"), anchor="w")
        self.total_card = total
        Pill(box, "Complete Sale", self.sell, "primary", width=300, height=42).pack(fill="x", pady=(0, 8))
        Pill(box, "Clear", self.clear, "soft", width=300, height=42).pack(fill="x")

        card, self.tree = table_card(self, "Recent Sales", ("Sale #", "Date", "Medicine", "Qty", "Total (Rs.)"),
                                     (60, 165, 170, 50, 90), height=14)
        card.grid(row=0, column=1, sticky="nsew")

    def selected_drug(self):
        index = self.combo.current()
        return self.drugs[index] if 0 <= index < len(self.drugs) else None

    def refresh(self):
        current = self.selected_drug().drug_id if self.selected_drug() else None
        # only medicines that are in stock and not expired can be sold
        self.drugs = [d for d in self.inventory.get_all() if not d.is_expired() and d.quantity > 0]
        self.combo["values"] = [f"{d.drug_id} - {d.name}  (stock {d.quantity})" for d in self.drugs]
        ids = [d.drug_id for d in self.drugs]
        if current in ids:
            self.combo.current(ids.index(current))
        else:
            self.combo.set("")
        self.show_info()
        self.tree.delete(*self.tree.get_children())
        for sale in self.sales.history():
            self.tree.insert("", "end", values=(sale[0], sale[1], sale[3], sale[4], f"{sale[6]:.2f}"))

    def show_info(self):
        drug = self.selected_drug()
        if drug:
            self.info.config(text=f"Unit price: Rs. {drug.price:.2f}\nIn stock: {drug.quantity}\nExpires: {drug.expiry_date}")
        else:
            self.info.config(text="Unit price: -\nIn stock: -\nExpires: -")
        self.show_total()

    def show_total(self):
        drug, total = self.selected_drug(), 0.0
        try:
            quantity = int(self.qty.get().strip())
            if drug and quantity > 0:
                total = self.sales.calculate_total(drug, quantity)
        except ValueError:
            pass
        self.total_card.itemconfigure(self.total_id, text=f"Rs. {total:,.2f}")

    def sell(self):
        drug = self.selected_drug()
        if drug is None:
            messagebox.showwarning("Select a medicine", "Please choose a medicine to sell.")
            return
        try:
            total = self.sales.sell(drug.drug_id, self.qty.get(), self.app.login.username)
        except ValueError as error:
            messagebox.showerror("Sale not completed", str(error))
            return
        messagebox.showinfo("Sale completed", f"Sold {self.qty.get().strip()} x {drug.name}\nTotal: Rs. {total:,.2f}")
        self.qty.set("1")
        self.refresh()

    def clear(self):
        self.combo.set("")
        self.qty.set("1")
        self.show_info()


class ReportsPage(BasePage):
    def build(self):
        self.columns, self.rows, self.current = (), [], "all"
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        buttons = tk.Frame(self, bg=T.bg)
        buttons.grid(row=0, column=0, sticky="w", pady=(0, 12))
        for text, key in (("All Medicines", "all"), ("Low Stock", "low"), ("Expired", "expired"), ("Sales History", "sales")):
            Pill(buttons, text, lambda k=key: self.show(k), "soft", width=130).pack(side="left", padx=(0, 8))
        Pill(buttons, "Export CSV", self.export, "primary", width=120).pack(side="left", padx=(12, 0))

        revenue = Card(self, gradient=(T.grad1, T.grad2), height=100, radius=20, inner=False, border=False)
        revenue.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        revenue.text(px(24), px(30), "Total Sales Revenue", fill="#E6E8FF", font=FONT, anchor="w")
        self.revenue_id = revenue.text(px(24), px(64), "", fill="#FFFFFF", font=("Segoe UI", 22, "bold"), anchor="w")
        self.summary_lines = ["", ""]
        revenue.decorate = lambda c, w, h: [
            c.create_text(w - px(24), px(36 + 26 * i), text=line, fill="#E6E8FF", font=SMALL, anchor="e", tags="shape")
            for i, line in enumerate(self.summary_lines)]
        self.revenue = revenue

        card, self.tree = table_card(self, " ", DRUG_COLUMNS, DRUG_WIDTHS, height=12)
        card.grid(row=2, column=0, sticky="nsew")
        self.table_title = card.title_label

    def refresh(self):
        self.show(self.current)

    def show(self, report):
        self.current = report
        if report == "sales":
            title = "Sales History"
            self.columns = ("Sale #", "Date", "Drug ID", "Medicine", "Qty", "Unit Price", "Total (Rs.)", "Sold By")
            widths = (60, 150, 70, 180, 50, 80, 90, 90)
            self.rows = [((s[0], s[1], s[2], s[3], s[4], f"{s[5]:.2f}", f"{s[6]:.2f}", s[7]), ()) for s in self.sales.history()]
        else:
            title, getter = {"all": ("All Medicine Records", self.inventory.get_all),
                             "low": ("Low-Stock Medicines", self.inventory.low_stock),
                             "expired": ("Expired Medicines", self.inventory.expired)}[report]
            self.columns, widths = DRUG_COLUMNS, DRUG_WIDTHS
            self.rows = [((d.drug_id, d.name, d.category, d.manufacturer, f"{d.price:.2f}", d.quantity,
                           d.expiry_date, d.status()), drug_tag(d)) for d in getter()]

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = self.columns
        for column, width in zip(self.columns, widths):
            self.tree.heading(column, text=column)
            self.tree.column(column, width=px(width), anchor="w")
        for values, tags in self.rows:
            self.tree.insert("", "end", values=values, tags=tags)
        self.table_title.config(text=f"{title}  ({len(self.rows)} records)")
        self.table_title.pack(anchor="w", pady=(0, 8), before=self.tree.master)
        self.revenue.itemconfigure(self.revenue_id, text=f"Rs. {self.sales.total_revenue():,.2f}")
        self.summary_lines = [self.inventory.summary(), self.sales.summary()]
        self.revenue.redraw()

    def export(self):
        if not self.rows:
            messagebox.showinfo("Export", "There is nothing to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV file", "*.csv")],
                                            initialfile=f"report_{self.current}.csv")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(self.columns)
                writer.writerows(values for values, _ in self.rows)
            messagebox.showinfo("Export", f"Report saved to:\n{path}")


# ------------------------------------------------------------------ windows
class LoginWindow(tk.Tk):
    def __init__(self, login):
        super().__init__()
        self.login = login
        self.title("PharmaCare - Login")
        prepare_window(self, 460, 660)
        self.resizable(False, False)
        self.configure(bg=T.bg)

        card = Card(self, radius=28, pad=26, width=390, height=580)
        card.place(relx=0.5, rely=0.5, anchor="center")
        box = card.inner

        banner = Card(box, gradient=(T.grad1, T.grad2), height=118, radius=20, inner=False, border=False)
        banner.pack(fill="x", pady=(0, 18))
        banner.text(px(22), px(42), "PharmaCare", fill="#FFFFFF", font=("Segoe UI", 20, "bold"), anchor="w")
        banner.text(px(22), px(74), "Drug Management System", fill="#E6E8FF", font=FONT, anchor="w")

        def decorate(c, w, h):          # soft circles on the banner
            for x, y, r, amount in ((w - px(52), px(56), px(30), 0.22), (w - px(92), px(80), px(16), 0.30)):
                c.create_oval(x - r, y - r, x + r, y + r, fill=blend(T.grad2, "#FFFFFF", amount), outline="", tags="shape")
            draw_icon(c, "pill", w - px(52), px(56), px(12), "#FFFFFF", blend(T.grad2, "#FFFFFF", 0.22))
        banner.decorate = decorate

        label(box, "Welcome back", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        label(box, "Sign in to continue", fg=T.muted).pack(anchor="w", pady=(0, 14))
        label(box, "Username", fg=T.muted).pack(anchor="w")
        self.user = tk.StringVar()
        self.user_entry = entry(box, self.user)
        self.user_entry.pack(fill="x", pady=(2, 12), ipady=6)
        label(box, "Password", fg=T.muted).pack(anchor="w")
        self.password = tk.StringVar()
        self.pass_entry = entry(box, self.password, show="*")
        self.pass_entry.pack(fill="x", pady=(2, 6), ipady=6)
        self.show_pass = tk.BooleanVar()
        tk.Checkbutton(box, text="Show password", variable=self.show_pass, bg=T.card, fg=T.muted, font=FONT,
                       activebackground=T.card, activeforeground=T.text, selectcolor=T.entry, highlightthickness=0, bd=0,
                       command=self.toggle).pack(anchor="w")
        self.message = label(box, "", fg=T.bad_text, wraplength=px(300))
        self.message.pack(pady=6)
        Pill(box, "Login", self.attempt, "primary", width=300, height=44).pack(fill="x")
        label(box, "Demo account:  admin / admin123", fg=T.muted).pack(pady=12)

        self.bind("<Return>", lambda e: self.attempt())
        self.user_entry.focus()

    def toggle(self):
        self.pass_entry.config(show="" if self.show_pass.get() else "*")

    def attempt(self):
        try:
            success = self.login.authenticate(self.user.get(), self.password.get())
        except ValueError as error:                 # empty fields
            self.message.config(text=str(error))
            return
        except PermissionError as error:            # locked
            messagebox.showerror("Locked", str(error))
            self.destroy()
            return
        if success:
            self.destroy()
        elif self.login.is_locked():
            messagebox.showerror("Too many attempts", "Too many failed attempts. The application will close.")
            self.destroy()
        else:
            self.password.set("")
            self.message.config(text=f"Incorrect username or password. {self.login.remaining_attempts} attempt(s) left.")


def icon_button(parent, icon, command):
    """A round clickable icon (bell, theme switch). Returns the canvas."""
    canvas = tk.Canvas(parent, width=px(42), height=px(42), bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
    canvas.create_oval(1, 1, px(42) - 1, px(42) - 1, fill=T.inset, outline="")
    draw_icon(canvas, icon, px(21), px(21), px(9), T.text, T.inset, tags="icon")
    canvas.bind("<Button-1>", lambda e: command())
    return canvas


class DrugManagementSystem(tk.Tk):
    """Main window: sidebar + header + pages. Controls the whole application."""

    PAGES = {"Dashboard": ("Overview", DashboardPage, "grid", ""),
             "Medicines": ("Medicines", MedicinesPage, "pill", "Add, update and search medicines"),
             "Inventory": ("Inventory", InventoryPage, "box", "Stock, low-stock and expiry monitoring"),
             "Sales": ("Sales", SalesPage, "bag", "Sell medicines"),
             "Reports": ("Reports", ReportsPage, "chart", "Records and revenue")}

    def __init__(self, inventory, sales, login):
        super().__init__()
        self.inventory, self.sales, self.login = inventory, sales, login
        self.logged_out = False
        self.current = "Dashboard"
        self.title("PharmaCare - Drug Management System")
        width, height = prepare_window(self, 1240, 760)
        self.minsize(min(px(1100), width), min(px(680), height))
        self.build_all()
        self.show_page("Dashboard")

    def build_all(self):
        self.configure(bg=T.bg)
        self.build_sidebar()
        self.build_header()
        self.build_pages()

    # ----- sidebar
    def build_sidebar(self):
        sidebar = Card(self, bg=T.sidebar, radius=26, width=230, pad=18)
        sidebar.pack(side="left", fill="y", padx=16, pady=16)
        box = sidebar.inner
        brand = tk.Frame(box, bg=T.sidebar)
        brand.pack(anchor="w", pady=(4, 26))
        logo = Card(brand, gradient=(T.grad1, T.grad2), width=40, height=40, radius=13, pad=0, inner=False, border=False)
        logo.text(px(20), px(20), "+", fill="#FFFFFF", font=("Segoe UI", 18, "bold"))
        logo.pack(side="left")
        label(brand, "PharmaCare", font=("Segoe UI", 16, "bold")).pack(side="left", padx=10)

        # bottom part first, so it stays at the bottom
        Pill(box, "Logout", self.logout, "nav", height=44, anchor="w", icon="logout").pack(side="bottom", fill="x")
        self.health = Card(box, gradient=(T.grad1, T.grad2), height=130, radius=18, pad=0, inner=False, border=False)
        self.health.pack(side="bottom", fill="x", pady=(0, 12))
        self.health_percent = 0
        self.health.text(px(18), px(26), "Stock Health", fill="#E6E8FF", font=FONT, anchor="w")
        self.health_value = self.health.text(px(18), px(60), "0%", fill="#FFFFFF", font=("Segoe UI", 22, "bold"), anchor="w")
        self.health_note = self.health.text(px(18), px(110), "", fill="#E6E8FF", font=SMALL, anchor="w")
        self.health.decorate = self.draw_health_bar

        self.nav = {}
        for name, (title, page_class, icon, note) in self.PAGES.items():
            pill = Pill(box, title, lambda n=name: self.show_page(n), "nav", height=44, anchor="w", icon=icon)
            pill.pack(fill="x", pady=3)
            self.nav[name] = pill

    def draw_health_bar(self, c, w, h):
        x1, x2, y, t = px(18), w - px(18), px(84), px(8)
        round_rect(c, x1, y, x2, y + t, t / 2, fill=blend(T.grad1, "#FFFFFF", 0.3), outline="", tags="shape")
        if self.health_percent > 0:
            end = max(x1 + t, x1 + (x2 - x1) * self.health_percent / 100)
            round_rect(c, x1, y, end, y + t, t / 2, fill="#FFFFFF", outline="", tags="shape")

    def update_health(self, stats):
        ok = stats["total"] - stats["low_stock"] - stats["expired"]
        self.health_percent = round(100 * ok / stats["total"]) if stats["total"] else 100
        self.health.itemconfigure(self.health_value, text=f"{self.health_percent}%")
        self.health.itemconfigure(self.health_note, text=f"{ok} of {stats['total']} medicines are OK")
        self.health.redraw()

    # ----- header
    def build_header(self):
        self.right = tk.Frame(self, bg=T.bg)
        self.right.pack(side="left", fill="both", expand=True, padx=(0, 16), pady=16)
        header = Card(self.right, radius=24, pad=12, height=72)
        header.pack(fill="x")
        box = header.inner
        box.columnconfigure(1, weight=1)
        box.rowconfigure(0, weight=1)

        titles = tk.Frame(box, bg=T.card)
        titles.grid(row=0, column=0, sticky="w", padx=(8, 0))
        self.page_title = label(titles, "", font=("Segoe UI", 14, "bold"))
        self.page_title.pack(anchor="w")
        self.page_note = label(titles, "", fg=T.muted, font=SMALL)
        self.page_note.pack(anchor="w")

        search = Card(box, bg=T.inset, radius=20, pad=8, height=42, border=False)    # rounded search bar
        search.grid(row=0, column=1, sticky="ew", padx=30)
        self.search_var = tk.StringVar()
        field = tk.Entry(search.inner, textvariable=self.search_var, relief="flat", bg=T.inset, fg=T.text, font=FONT,
                         highlightthickness=0, insertbackground=T.text)
        field.pack(fill="both", expand=True, padx=8)
        field.bind("<Return>", lambda e: self.header_search())
        label(search.inner, "Search medicine, press Enter", fg=T.muted, font=SMALL).place(relx=1, rely=0.5, anchor="e", x=-px(10))

        tools = tk.Frame(box, bg=T.card)
        tools.grid(row=0, column=2, sticky="e", padx=(0, 8))
        self.bell = icon_button(tools, "bell", lambda: self.show_page("Inventory"))
        self.bell.pack(side="left", padx=4)
        theme_icon = "sun" if T.name == "dark" else "moon"
        icon_button(tools, theme_icon, self.toggle_theme).pack(side="left", padx=4)
        avatar = tk.Canvas(tools, width=px(40), height=px(40), bg=T.card, highlightthickness=0)
        avatar.create_oval(1, 1, px(40) - 1, px(40) - 1, fill=T.accent, outline="")
        avatar.create_text(px(20), px(20), text=self.login.full_name[0], fill="#FFFFFF", font=("Segoe UI", 13, "bold"))
        avatar.pack(side="left", padx=(12, 0))
        who = tk.Frame(tools, bg=T.card)
        who.pack(side="left", padx=8)
        label(who, self.login.full_name, font=BOLD).pack(anchor="w")
        label(who, "Online", fg=T.good, font=SMALL).pack(anchor="w")

    def update_bell(self, stats):
        count = stats["low_stock"] + stats["expired"]
        self.bell.delete("badge")
        if count:
            r = px(9)
            self.bell.create_oval(px(42) - 2 * r, 0, px(42), 2 * r, fill=T.bad, outline=T.card, width=2, tags="badge")
            self.bell.create_text(px(42) - r, r, text=str(count), fill="#FFFFFF", font=("Segoe UI", 8, "bold"), tags="badge")

    # ----- pages
    def build_pages(self):
        container = tk.Frame(self.right, bg=T.bg)
        container.pack(fill="both", expand=True, pady=(14, 0))
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.pages = {}
        for name, (title, page_class, icon, note) in self.PAGES.items():
            self.pages[name] = page_class(container, self)
            self.pages[name].grid(row=0, column=0, sticky="nsew")

    def greeting(self):
        hour = datetime.now().hour
        word = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        return f"{word}, {self.login.full_name}   |   {datetime.now().strftime('%A, %d %B %Y')}"

    def show_page(self, name):
        self.current = name
        for key, pill in self.nav.items():                 # active menu item is highlighted
            pill.set_style("navactive" if key == name else "nav")
        title, page_class, icon, note = self.PAGES[name]
        self.page_title.config(text=title)
        self.page_note.config(text=self.greeting() if name == "Dashboard" else note)
        stats = self.inventory.stats()
        self.update_health(stats)
        self.update_bell(stats)
        page = self.pages[name]
        page.refresh()            # same call, every page does its own thing
        page.tkraise()

    def header_search(self):
        """Search from the top bar: jump to the Medicines page and show the results."""
        self.pages["Medicines"].search_var.set(self.search_var.get())
        self.show_page("Medicines")

    def toggle_theme(self):
        """Switch between dark and light: change the colours, then build the screen again."""
        self.after(10, self.switch_theme)

    def switch_theme(self):
        T.use("light" if T.name == "dark" else "dark")
        for child in self.winfo_children():
            child.destroy()
        setup_styles(self)
        self.build_all()
        self.show_page(self.current)

    def logout(self):
        if messagebox.askyesno("Logout", "Do you want to log out?"):
            self.logged_out = True
            self.login.logout()
            self.destroy()
