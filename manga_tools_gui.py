import importlib.util
import os
import sys
import threading
from contextlib import redirect_stderr, redirect_stdout

def _ensure_tk():
    """Указывает tkinter путь к tcl/tk, если он не найден автоматически."""
    if sys.platform != "win32" or getattr(sys, "frozen", False):
        return
    base = os.path.dirname(getattr(sys, "_base_executable", sys.executable))
    for root in (os.path.join(base, "tcl"), base):
        if not os.environ.get("TCL_LIBRARY"):
            candidate = os.path.join(root, "tcl8.6")
            if os.path.isdir(candidate):
                os.environ["TCL_LIBRARY"] = candidate
        if not os.environ.get("TK_LIBRARY"):
            candidate = os.path.join(root, "tk8.6")
            if os.path.isdir(candidate):
                os.environ["TK_LIBRARY"] = candidate

_ensure_tk()
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_TITLE = "Manga Chapter Tools — инструменты для глав манги"

OPERATIONS = {
    "archive": {
        "file": "Архивирование-глав-(Archiving-chapters).py",
        "label": "Архивирование глав (в ZIP)",
        "func": "archive_directories",
        "fields": [("input_dir", "Папка с главами", "dir")],
        "kwargs": {"input_dir": "source_dir"},
    },
    "remove_blank": {
        "file": "remove_empty_black_white_photos.py",
        "label": "Удаление пустых фото (белых/чёрных)",
        "func": "remove_blank_photos",
        "fields": [("input_dir", "Папка с фото", "dir")],
        "kwargs": {"input_dir": "input_dir"},
    },
    "copy_file": {
        "file": "bulk_copy_files.py",
        "label": "Копирование файла во все подпапки",
        "func": "copy_file_to_multiple_directories",
        "fields": [("source", "Файл для копирования", "file"),
                   ("dest", "Папка с подпапками", "dir")],
        "kwargs": {"source": "source_file", "dest": "destination_folder"},
    },
    "video": {
        "file": "Each photo is a 10-second video..py",
        "label": "Создание видео из изображений",
        "func": "process_images",
        "fields": [("input_path", "Изображение или папка", "file_dir"),
                   ("fps", "Кадров в секунду (по умолчанию 30)", "int"),
                   ("duration", "Длительность, сек (по умолчанию 10)", "int")],
        "kwargs": {"input_path": "input_path", "fps": "fps", "duration": "duration"},
    },
    "rename": {
        "file": "from i (704) 0 to i (704).py",
        "label": "Переименование файлов (убрать ' 0')",
        "func": "rename_files",
        "fields": [("input_dir", "Папка с файлами", "dir")],
        "kwargs": {"input_dir": "input_path"},
    },
    "resize": {
        "file": "smart_resize_manga.py",
        "label": "Умный ресайз манги под сайт",
        "func": "smart_resize_chapter",
        "fields": [
            ("input_dir", "Папка с папками глав", "dir"),
            ("output_dir", "Куда сохранять (пусто = входная папка + smart_resize_manga)", "dir_optional"),
            ("width", "Ширина, px (пусто = не менять, оставить исходную)", "int_optional"),
            ("page_height", "Высота страницы после нарезки, px (пусто = 1920)", "int_optional"),
            ("out_format", "Формат файлов", "combo", ["jpg", "png"]),
            ("use_text_detector", "Не разрезать текст (детектор)", "check"),
        ],
        "kwargs": {"input_dir": "input_folder", "output_dir": "output_folder",
                   "width": "width", "page_height": "page_height",
                   "out_format": "out_format", "use_text_detector": "use_text_detector"},
    },
}


def resource_path(relative):
    base = getattr(sys, "_MEIPASS", BASE_DIR)
    return os.path.join(base, relative)


def load_script(script_file):
    path = resource_path(script_file)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Не найден файл скрипта: {path}")
    module_name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTqdm:
    """Прогресс-бар без вывода в консоль (для аккуратного журнала в GUI)."""

    def __init__(self, iterable=None, **kwargs):
        self._it = iter(iterable if iterable is not None else [])

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._it)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def update(self, n=1):
        pass

    def set_description(self, desc):
        pass


def patch_tqdm():
    try:
        import tqdm
        tqdm.tqdm = FakeTqdm
    except ImportError:
        pass


class OutputSink:
    def __init__(self, callback):
        self._callback = callback

    def write(self, text):
        if text:
            self._callback(text.replace("\r", "\n"))

    def flush(self):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("820x620")
        self.minsize(640, 480)

        self._modules = {}
        self._running = False
        self._current_op = None

        self._build_ui()
        self._set_operation()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        top = ttk.LabelFrame(self, text="Операция")
        top.pack(fill="x", **pad)
        self.op_var = tk.StringVar()
        self.op_combo = ttk.Combobox(
            top, textvariable=self.op_var, state="readonly",
            values=[op["label"] for op in OPERATIONS.values()],
        )
        self.op_combo.pack(side="left", **pad)
        self.op_combo.bind("<<ComboboxSelected>>", lambda e: self._set_operation())

        self.params = ttk.LabelFrame(self, text="Параметры")
        self.params.pack(fill="x", **pad)
        self.param_widgets = {}

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", **pad)
        self.run_btn = ttk.Button(buttons, text="Выполнить", command=self._run)
        self.run_btn.pack(side="left")
        ttk.Button(buttons, text="Очистить журнал", command=self._clear_log).pack(side="left", padx=(8, 0))
        self.status_var = tk.StringVar(value="Готов к работе.")
        ttk.Label(buttons, textvariable=self.status_var).pack(side="right")

        log_frame = ttk.LabelFrame(self, text="Журнал")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(log_frame, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, **pad)

    def _set_operation(self):
        for widget in self.params.winfo_children():
            widget.destroy()
        self.param_widgets = {}

        key = self.op_combo.current()
        if key == -1:
            self.op_combo.current(0)
            key = 0
        self._current_op = list(OPERATIONS.keys())[key]
        fields = OPERATIONS[self._current_op]["fields"]

        for row, field in enumerate(fields):
            fname, flabel, ftype = field[0], field[1], field[2]
            choices = field[3] if len(field) > 3 else None
            ttk.Label(self.params, text=f"{flabel}:").grid(row=row, column=0, sticky="w", padx=8, pady=4)
            self.params.columnconfigure(1, weight=1)

            if ftype == "check":
                var = tk.BooleanVar(value=True)
                check = ttk.Checkbutton(self.params, text="Вкл", variable=var)
                check.grid(row=row, column=1, sticky="w", padx=4, pady=4)
                self.param_widgets[fname] = var
            elif ftype == "combo":
                var = tk.StringVar(value=choices[0] if choices else "")
                combo = ttk.Combobox(self.params, textvariable=var, state="readonly",
                                     values=choices or [], width=20)
                combo.grid(row=row, column=1, sticky="w", padx=4, pady=4)
                self.param_widgets[fname] = var
            else:
                var = tk.StringVar()
                entry = ttk.Entry(self.params, textvariable=var, width=60)
                entry.grid(row=row, column=1, sticky="we", padx=4, pady=4)
                self.param_widgets[fname] = var
                if ftype in ("dir", "file", "file_dir", "dir_optional"):
                    ttk.Button(
                        self.params,
                        text="Обзор...",
                        command=lambda ft=ftype, v=var: self._browse(ft, v),
                    ).grid(row=row, column=2, padx=4, pady=4)

    def _browse(self, ftype, var):
        if ftype in ("dir", "dir_optional"):
            path = filedialog.askdirectory(title="Выберите папку")
        else:
            path = filedialog.askopenfilename(title="Выберите файл")
        if path:
            var.set(path)

    def _collect_args(self, key):
        args = {}
        for field in OPERATIONS[key]["fields"]:
            fname, flabel, ftype = field[0], field[1], field[2]
            var = self.param_widgets[fname]
            if ftype == "check":
                args[fname] = bool(var.get())
                continue
            value = var.get().strip()
            if ftype == "int_optional":
                args[fname] = int(value) if value else None
                continue
            if ftype == "dir_optional":
                args[fname] = value or None
                continue
            if not value:
                raise ValueError(f"Заполните поле: {flabel}")
            if ftype == "int":
                try:
                    value = int(value)
                except ValueError:
                    raise ValueError(f"Поле «{flabel}» должно быть целым числом.")
            args[fname] = value
        return args

    def _run(self):
        if self._running:
            return
        key = self._current_op
        try:
            args = self._collect_args(key)
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))
            return

        self._running = True
        self.run_btn.config(state="disabled")
        self.status_var.set("Выполняется...")
        self._append_log(f"\n>>> {OPERATIONS[key]['label']}\n")

        thread = threading.Thread(target=self._worker, args=(key, args), daemon=True)
        thread.start()

    def _get_module(self, key):
        script_file = OPERATIONS[key]["file"]
        if script_file not in self._modules:
            self._modules[script_file] = load_script(script_file)
        return self._modules[script_file]

    def _worker(self, key, args):
        sink = OutputSink(self._append_log)
        try:
            module = self._get_module(key)
            func_name = OPERATIONS[key]["func"]
            kwargs = {kw: args[arg] for arg, kw in OPERATIONS[key]["kwargs"].items()}
            with redirect_stdout(sink), redirect_stderr(sink):
                func = getattr(module, func_name)
                func(**kwargs)
            self._append_log("\n[Готово] Операция завершена успешно.\n")
        except ImportError as e:
            self._append_log(f"\n[Ошибка] Не установлена зависимость: {e}\n")
            self._append_log("Установите зависимости: pip install -r requirements.txt\n")
        except FileNotFoundError as e:
            self._append_log(f"\n[Ошибка] {e}\n")
        except Exception as e:
            self._append_log(f"\n[Ошибка] {e}\n")
        finally:
            self.after(0, self._finish)

    def _finish(self):
        self._running = False
        self.run_btn.config(state="normal")
        self.status_var.set("Готов к работе.")

    def _append_log(self, text):
        self.after(0, lambda: self._write_log(text))

    def _write_log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")


def run_selftest():
    """Самопроверка упакованного exe: проверяет PIL, cv2 и tqdm реальным вызовом."""
    import tempfile
    import traceback

    result_path = os.path.join(tempfile.gettempdir(), "manga_tools_selftest.txt")
    try:
        import numpy as np
        from PIL import Image as PILImage

        src = tempfile.mkdtemp()

        # PIL + cv2: create a blank white photo, then remove it with remove_blank_photos
        PILImage.fromarray(np.full((60, 40, 3), 255, dtype=np.uint8)).save(
            os.path.join(src, "blank.jpg"))

        module = load_script("remove_empty_black_white_photos.py")
        module.remove_blank_photos(src)
        cv2_ok = not os.path.exists(os.path.join(src, "blank.jpg"))

        # PIL + tqdm: resize a PNG page (structure: src\Глава 1\page.png)
        chapter = os.path.join(src, "Глава 1")
        os.makedirs(chapter, exist_ok=True)
        PILImage.fromarray(np.full((60, 40, 3), 200, dtype=np.uint8)).save(
            os.path.join(chapter, "p01.png"))
        module = load_script("smart_resize_manga.py")
        out = tempfile.mkdtemp()
        module.smart_resize_chapter(src, out, width=None, use_text_detector=False)
        pil_ok = os.path.isdir(os.path.join(out, "Глава 1")) and bool(
            os.listdir(os.path.join(out, "Глава 1")))

        message = "SELFTEST OK (cv2=%s, PIL=%s)" % (cv2_ok, pil_ok)
    except Exception:
        message = "SELFTEST ERROR: " + traceback.format_exc()

    with open(result_path, "w", encoding="utf-8") as f:
        f.write(message)


if __name__ == "__main__":
    patch_tqdm()
    if os.environ.get("MANGA_TOOLS_SELFTEST"):
        import io
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            run_selftest()
        sys.exit(0)
    App().mainloop()
