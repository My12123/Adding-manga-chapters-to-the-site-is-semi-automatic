import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(BASE, "venv", "Scripts", "python.exe")
GUI = os.path.join(BASE, "manga_tools_gui.py")
NAME = "Manga Chapter Tools"

SCRIPTS = [
    "Архивирование-глав-(Archiving-chapters).py",
    "remove_empty_black_white_photos.py",
    "bulk_copy_files.py",
    "Each photo is a 10-second video..py",
    "from i (704) 0 to i (704).py",
    "smart_resize_manga.py",
    "requirements.txt",
]


def run(cmd):
    print("> " + " ".join(cmd))
    return subprocess.call(cmd, cwd=BASE)


def _ensure_tk_env():
    """Задаёт пути tcl/tk для venv, иначе PyInstaller исключит tkinter из exe."""
    if sys.platform != "win32":
        return
    base = getattr(sys, "base_prefix", sys.prefix)
    for root in (os.path.join(base, "tcl"), base):
        if not os.environ.get("TCL_LIBRARY"):
            candidate = os.path.join(root, "tcl8.6")
            if os.path.isdir(candidate):
                os.environ["TCL_LIBRARY"] = candidate
        if not os.environ.get("TK_LIBRARY"):
            candidate = os.path.join(root, "tk8.6")
            if os.path.isdir(candidate):
                os.environ["TK_LIBRARY"] = candidate


def main():
    _ensure_tk_env()

    if not os.path.exists(VENV_PY):
        print("[ERROR] Виртуальное окружение не найдено.")
        print("Сначала запустите 'Installer for Windows CPU.bat'.")
        return 1

    py = VENV_PY

    print("[1/4] Установка PyInstaller...")
    if run([py, "-m", "pip", "install", "--upgrade", "pyinstaller"]) != 0:
        print("[ERROR] Не удалось установить PyInstaller.")
        return 1

    for d in ("build", "dist"):
        path = os.path.join(BASE, d)
        if os.path.isdir(path):
            shutil.rmtree(path)
    spec = os.path.join(BASE, f"{NAME}.spec")
    if os.path.exists(spec):
        os.remove(spec)

    print("[2/4] Сборка exe (может занять несколько минут)...")
    cmd = [
        py, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--name", NAME,
        "--collect-all", "cv2",
        "--collect-submodules", "PIL",
        "--hidden-import", "numpy",
        "--hidden-import", "tqdm",
    ]
    for script in SCRIPTS:
        cmd += ["--add-data", f"{script};."]
    cmd.append(GUI)

    if run(cmd) != 0:
        print("[ERROR] Сборка не удалась.")
        return 1

    print("[3/4] Копирование exe в папку проекта...")
    dist_exe = os.path.join(BASE, "dist", f"{NAME}.exe")
    target = os.path.join(BASE, f"{NAME}.exe")
    if os.path.exists(dist_exe):
        shutil.copy2(dist_exe, target)
        print(f"[4/4] Готово. Исполняемый файл: {target}")
    else:
        print(f"[4/4] Исполняемый файл находится в папке: {dist_exe}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
