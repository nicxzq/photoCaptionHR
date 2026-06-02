from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from typing import Any
from tkinter import filedialog, messagebox, scrolledtext, ttk

from core.ocr_engine import default_model_dir, model_cache_ready
from core.runner import run_batch
from utils.splash import close_splash


APP_VERSION = "0.1.0"
TASKS = {
    "名单打勾": "excel",
    "证书重命名": "cert",
}
ATTRIBUTES = {
    "sequence": "序号",
    "name": "姓名",
    "title": "文档标题",
    "level": "级别",
}
TASK_ATTRIBUTES = {
    "excel": ("sequence", "name", "title"),
    "cert": ("name", "title", "level"),
}
LOG_COMPACT_HEIGHT = 12
LOG_EXPANDED_HEIGHT = 22


class PhotoSignApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"PhotoSign {APP_VERSION}")
        self.root.geometry("900x700")
        self.root.minsize(780, 620)
        self.root.configure(background="#F5F5F7")
        self.events: queue.Queue[tuple] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.task_var = tk.StringVar(value=next(iter(TASKS)))
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.model_var = tk.StringVar(value=str(default_model_dir()))
        self.separator_var = tk.StringVar(value="-")
        self.status_var = tk.StringVar(value="请选择任务和目录，然后开始处理。")
        self.attribute_vars = {
            attribute: tk.BooleanVar(value=attribute in {"name", "title"})
            for attribute in ATTRIBUTES
        }
        self.attribute_checks: dict[str, ttk.Checkbutton] = {}
        self.log_expanded = False

        self.configure_style()
        self.build_menu()
        self.build_body()
        self.task_var.trace_add("write", self.on_task_change)
        self.on_task_change()
        self.root.after(100, self.drain_events)
        self.root.after(150, close_splash)

    def configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), foreground="#1D1D1F")
        style.configure("App.TFrame", background="#F5F5F7")
        style.configure("Card.TFrame", background="#FFFFFF")
        style.configure("Card.TLabel", background="#FFFFFF", foreground="#1D1D1F")
        style.configure(
            "Title.TLabel",
            background="#F5F5F7",
            foreground="#1D1D1F",
            font=("Segoe UI Semibold", 18),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#F5F5F7",
            foreground="#6E6E73",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Section.TLabel",
            background="#FFFFFF",
            foreground="#1D1D1F",
            font=("Segoe UI Semibold", 11),
        )
        style.configure("Card.TCheckbutton", background="#FFFFFF")
        style.configure("Accent.TButton", background="#007AFF", foreground="#FFFFFF", padding=(16, 8))
        style.map(
            "Accent.TButton",
            background=[("disabled", "#A9CFFF"), ("active", "#0066D6"), ("!disabled", "#007AFF")],
            foreground=[("disabled", "#FFFFFF"), ("!disabled", "#FFFFFF")],
        )
        style.configure("Secondary.TButton", padding=(12, 7))
        style.configure("Horizontal.TProgressbar", troughcolor="#E5E5EA", background="#007AFF")

    def build_menu(self) -> None:
        menu = tk.Menu(self.root)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="使用帮助", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        menu.add_cascade(label="帮助", menu=help_menu)
        self.root.config(menu=menu)

    def build_body(self) -> None:
        page = ttk.Frame(self.root, style="App.TFrame", padding=22)
        page.pack(fill=tk.BOTH, expand=True)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(4, weight=1)

        ttk.Label(page, text="PhotoSign", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            page,
            text="批量 OCR 图片处理工具",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 16))

        self.build_settings_card(page).grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self.build_progress_card(page).grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self.build_log_card(page).grid(row=4, column=0, sticky="nsew")

        footer = ttk.Frame(page, style="App.TFrame")
        footer.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        ttk.Label(footer, text=f"Version {APP_VERSION}", style="Subtitle.TLabel").pack(side=tk.LEFT)
        ttk.Label(footer, text="反馈微信：@carl-xu", style="Subtitle.TLabel").pack(side=tk.RIGHT)

    def build_settings_card(self, parent: ttk.Frame) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text="处理设置", style="Section.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )

        ttk.Label(card, text="任务", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Combobox(card, textvariable=self.task_var, values=list(TASKS), state="readonly").grid(
            row=1, column=1, sticky="ew", pady=5
        )

        ttk.Label(card, text="命名属性", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=5)
        self.attribute_frame = ttk.Frame(card, style="Card.TFrame")
        self.attribute_frame.grid(row=2, column=1, sticky="w", pady=5)
        for index, (attribute, label) in enumerate(ATTRIBUTES.items()):
            checkbox = ttk.Checkbutton(
                self.attribute_frame,
                text=label,
                variable=self.attribute_vars[attribute],
                style="Card.TCheckbutton",
            )
            checkbox.grid(row=0, column=index, sticky="w", padx=(0, 14))
            self.attribute_checks[attribute] = checkbox

        separator_frame = ttk.Frame(card, style="Card.TFrame")
        separator_frame.grid(row=2, column=2, sticky="e", padx=(10, 0), pady=5)
        ttk.Label(separator_frame, text="分隔符", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(separator_frame, textvariable=self.separator_var, width=8).pack(side=tk.LEFT)

        self.folder_row(card, 3, "输入目录", self.input_var)
        self.folder_row(card, 4, "输出目录", self.output_var)
        self.model_entry = self.folder_row(card, 5, "模型缓存", self.model_var, readonly=True)
        return card

    def build_progress_card(self, parent: ttk.Frame) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text="处理进度", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(card, mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 8))
        ttk.Label(card, textvariable=self.status_var, style="Card.TLabel").grid(row=2, column=0, sticky="w")

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=2, column=1, sticky="e")
        self.start_button = ttk.Button(actions, text="开始处理", command=self.start, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            actions,
            text="打开输出目录",
            command=self.open_output,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT)
        return card

    def build_log_card(self, parent: ttk.Frame) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)
        header = ttk.Frame(card, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(header, text="处理日志", style="Section.TLabel").pack(side=tk.LEFT)
        self.log_toggle_button = ttk.Button(
            header,
            text="展开日志",
            command=self.toggle_log,
            style="Secondary.TButton",
        )
        self.log_toggle_button.pack(side=tk.RIGHT)
        self.log = scrolledtext.ScrolledText(
            card,
            height=LOG_COMPACT_HEIGHT,
            relief="flat",
            borderwidth=0,
            background="#FBFBFD",
            foreground="#1D1D1F",
            font=("Consolas", 9),
        )
        self.log.bind("<Key>", self.block_log_edit)
        self.log.grid(row=1, column=0, sticky="nsew")
        return card

    def toggle_log(self) -> None:
        self.log_expanded = not self.log_expanded
        self.log.configure(height=LOG_EXPANDED_HEIGHT if self.log_expanded else LOG_COMPACT_HEIGHT)
        self.log_toggle_button.configure(text="收起日志" if self.log_expanded else "展开日志")

    def folder_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        var: tk.StringVar,
        *,
        readonly: bool = False,
    ) -> ttk.Entry:
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        entry = ttk.Entry(parent, textvariable=var, state="readonly" if readonly else "normal")
        entry.grid(row=row, column=1, sticky="ew", pady=5)
        ttk.Button(
            parent,
            text="选择",
            command=lambda: self.choose_folder(var),
            style="Secondary.TButton",
        ).grid(row=row, column=2, padx=(10, 0), pady=5)
        return entry

    def on_task_change(self, *_args: object) -> None:
        task = TASKS[self.task_var.get()]
        allowed = set(TASK_ATTRIBUTES[task])
        for attribute, checkbox in self.attribute_checks.items():
            if attribute in allowed:
                checkbox.grid()
            else:
                checkbox.grid_remove()
                self.attribute_vars[attribute].set(False)

    def choose_folder(self, var: tk.StringVar) -> None:
        selected = filedialog.askdirectory(initialdir=var.get() or os.getcwd())
        if selected:
            var.set(selected)
            if var is self.model_var:
                self.status_var.set(self.model_status())

    def model_status(self) -> str:
        model_dir = Path(self.model_var.get() or default_model_dir())
        return "模型缓存已就绪。" if model_cache_ready(model_dir) else "模型将在首次处理时加载，请耐心等待。"

    def selected_attributes(self) -> tuple[str, ...]:
        task = TASKS[self.task_var.get()]
        return tuple(attribute for attribute in TASK_ATTRIBUTES[task] if self.attribute_vars[attribute].get())

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.input_var.get() or not self.output_var.get():
            messagebox.showwarning("缺少目录", "请选择输入目录和输出目录。")
            return
        attributes = self.selected_attributes()
        if not attributes:
            messagebox.showwarning("缺少命名属性", "请至少选择一个命名属性。")
            return
        config = {
            "task": TASKS[self.task_var.get()],
            "input_dir": self.input_var.get(),
            "output_dir": self.output_var.get(),
            "model_dir": self.model_var.get(),
            "name_attributes": attributes,
            "separator": self.separator_var.get(),
        }
        self.start_button.config(state="disabled")
        self.clear_log()
        self.start_loading("正在准备处理...")
        self.worker = threading.Thread(target=self.run_worker, args=(config,), daemon=True)
        self.worker.start()

    def run_worker(self, config: dict[str, Any]) -> None:
        try:
            result = run_batch(
                config["task"],
                config["input_dir"],
                config["output_dir"],
                config["model_dir"],
                name_attributes=config["name_attributes"],
                separator=config["separator"],
                progress=self.progress_event,
            )
            self.events.put(("done", result))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def progress_event(self, state: str, path: Path | None, index: int, total: int, value: object) -> None:
        self.events.put(("progress", state, path, index, total, value))

    def drain_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event[0]
            if kind == "progress":
                self.apply_progress(event[1:])
            elif kind == "done":
                self.finish(event[1])
            elif kind == "error":
                self.fail(event[1])
        self.root.after(100, self.drain_events)

    def apply_progress(self, event: tuple) -> None:
        state, path, index, total, value = event
        if state == "initializing":
            self.start_loading(str(value))
            return
        if state == "ready":
            self.stop_loading(total)
            self.status_var.set(str(value))
            return
        if state == "empty":
            self.status_var.set("输入目录没有找到图片。")
            return
        if total:
            self.stop_loading(total)
            self.progress["value"] = index if state in {"ok", "failed"} else max(0, index - 1)
        if state == "start" and path:
            self.status_var.set(f"处理中 {index}/{total}：{path.name}")
            self.append_log(f"[{index}/{total}] {path.name}")
        elif state == "ok" and path:
            self.append_log(f"  OK -> {value} file(s)")
        elif state == "failed" and path:
            self.append_log(f"  FAILED: {value}")

    def start_loading(self, message: str) -> None:
        self.progress.stop()
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self.status_var.set(message)

    def stop_loading(self, total: int = 100) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate", maximum=max(1, total))

    def finish(self, result: dict[str, int]) -> None:
        self.stop_loading(result["input"] or 1)
        self.progress["value"] = result["input"]
        self.start_button.config(state="normal")
        self.status_var.set(
            f"完成：输入 {result['input']}，成功 {result['success']}，失败 {result['failed']}，输出 {result['output']}"
        )
        messagebox.showinfo("处理完成", self.status_var.get())

    def fail(self, message: str) -> None:
        self.stop_loading()
        self.start_button.config(state="normal")
        self.status_var.set("处理失败")
        self.append_log(message)
        messagebox.showerror("处理失败", message)

    def append_log(self, text: str) -> None:
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def clear_log(self) -> None:
        self.log.delete("1.0", tk.END)

    def block_log_edit(self, event: tk.Event) -> str | None:
        if event.state & 0x4 and event.keysym.lower() in {"a", "c"}:
            return None
        return "break"

    def open_output(self) -> None:
        path = self.output_var.get()
        if path and Path(path).exists():
            os.startfile(path)

    def show_help(self) -> None:
        messagebox.showinfo(
            "使用帮助",
            "1. 选择任务，并勾选需要参与文件命名的属性。\n"
            "2. 属性分隔符可以自定义，也可以留空。\n"
            "3. 选择输入目录和输出目录后，点击“开始处理”。\n"
            "4. 首次加载 OCR 模型可能需要一些时间，请等待进度提示。",
        )

    def show_about(self) -> None:
        messagebox.showinfo(
            "关于 PhotoSign",
            f"PhotoSign v{APP_VERSION}\n"
            "批量 OCR 图片处理工具\n\n"
            "本软件最终解释权归作者所有\n"
            "问题反馈：微信 @carl-xu",
        )

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    PhotoSignApp().run()
