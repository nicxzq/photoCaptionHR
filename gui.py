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


TASKS = {
    "Excel 名单打勾": "excel",
    "证书重命名": "cert",
}

NAME_RULES = {
    "姓名-文档标题": "name-title",
    "文档标题-姓名": "title-name",
    "仅姓名": "name",
}


class PhotoSignApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("PhotoSign")
        self.root.geometry("780x560")
        self.root.minsize(720, 500)
        self.events: queue.Queue[tuple] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.task_var = tk.StringVar(value=next(iter(TASKS)))
        self.rule_var = tk.StringVar(value=next(iter(NAME_RULES)))
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.model_var = tk.StringVar(value=str(default_model_dir()))
        self.status_var = tk.StringVar(value=self.model_status())

        self.build_menu()
        self.build_body()
        self.root.after(100, self.drain_events)

    def build_menu(self) -> None:
        menu = tk.Menu(self.root)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="使用帮助", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        menu.add_cascade(label="帮助", menu=help_menu)
        self.root.config(menu=menu)

    def build_body(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="任务").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Combobox(frame, textvariable=self.task_var, values=list(TASKS), state="readonly").grid(
            row=0, column=1, sticky="ew", pady=6
        )

        ttk.Label(frame, text="命名规则").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(frame, textvariable=self.rule_var, values=list(NAME_RULES), state="readonly").grid(
            row=1, column=1, sticky="ew", pady=6
        )

        self.folder_row(frame, 2, "输入目录", self.input_var)
        self.folder_row(frame, 3, "输出目录", self.output_var)
        self.folder_row(frame, 4, "模型缓存", self.model_var)

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(14, 6))
        ttk.Label(frame, textvariable=self.status_var).grid(row=6, column=0, columnspan=3, sticky="w")

        self.log = scrolledtext.ScrolledText(frame, height=14, state="disabled")
        self.log.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=10)
        frame.rowconfigure(7, weight=1)

        actions = ttk.Frame(frame)
        actions.grid(row=8, column=0, columnspan=3, sticky="e")
        self.start_button = ttk.Button(actions, text="开始处理", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="打开输出目录", command=self.open_output).pack(side=tk.LEFT)

    def folder_row(self, parent: ttk.Frame, row: int, label: str, var: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=6, padx=(0, 8))
        ttk.Button(parent, text="选择", command=lambda: self.choose_folder(var)).grid(row=row, column=2, pady=6)

    def choose_folder(self, var: tk.StringVar) -> None:
        selected = filedialog.askdirectory(initialdir=var.get() or os.getcwd())
        if selected:
            var.set(selected)
            if var is self.model_var:
                self.status_var.set(self.model_status())

    def model_status(self) -> str:
        model_dir = Path(self.model_var.get() or default_model_dir())
        if model_cache_ready(model_dir):
            return f"模型缓存已存在：{model_dir}"
        return f"模型缓存未完整：首次运行会尝试下载；离线时请先准备 det/rec/cls 到 {model_dir}"

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.input_var.get() or not self.output_var.get():
            messagebox.showwarning("缺少目录", "请选择输入目录和输出目录。")
            return
        config = {
            "task": TASKS[self.task_var.get()],
            "input_dir": self.input_var.get(),
            "output_dir": self.output_var.get(),
            "model_dir": self.model_var.get(),
            "name_rule": NAME_RULES[self.rule_var.get()],
        }
        self.start_button.config(state="disabled")
        self.progress["value"] = 0
        self.clear_log()
        self.status_var.set("准备处理...")
        self.worker = threading.Thread(target=self.run_worker, args=(config,), daemon=True)
        self.worker.start()

    def run_worker(self, config: dict[str, Any]) -> None:
        try:
            result = run_batch(
                config["task"],
                config["input_dir"],
                config["output_dir"],
                config["model_dir"],
                name_rule=config["name_rule"],
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
        if total:
            self.progress["maximum"] = total
            self.progress["value"] = index
        if state == "start" and path:
            self.status_var.set(f"处理中 {index}/{total}: {path.name}")
        elif state == "ok" and path:
            self.append_log(f"OK: {path.name} -> {value} file(s)")
        elif state == "failed" and path:
            self.append_log(f"FAILED: {path.name}: {value}")
        elif state == "empty":
            self.status_var.set("输入目录没有找到图片。")

    def finish(self, result: dict[str, int]) -> None:
        self.start_button.config(state="normal")
        self.status_var.set(
            f"完成：输入 {result['input']}，成功 {result['success']}，失败 {result['failed']}，输出 {result['output']}"
        )
        messagebox.showinfo("处理完成", self.status_var.get())

    def fail(self, message: str) -> None:
        self.start_button.config(state="normal")
        self.status_var.set("处理失败")
        self.append_log(message)
        messagebox.showerror("处理失败", message)

    def append_log(self, text: str) -> None:
        self.log.config(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")

    def clear_log(self) -> None:
        self.log.config(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.config(state="disabled")

    def open_output(self) -> None:
        path = self.output_var.get()
        if path and Path(path).exists():
            os.startfile(path)

    def show_help(self) -> None:
        messagebox.showinfo(
            "使用帮助",
            "1. 选择任务、命名规则、输入目录和输出目录。\n"
            "2. 模型缓存建议使用 C:\\PhotoSign\\models。\n"
            "3. 如果模型不存在，联网时会自动下载；离线时请先准备 det/rec/cls 三个目录。",
        )

    def show_about(self) -> None:
        messagebox.showinfo("关于 PhotoSign", "PhotoSign\n批量 OCR 图片处理工具\nOCR: PaddleOCR\n模型缓存与程序分离。")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    PhotoSignApp().run()
