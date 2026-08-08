import argparse
import os
import subprocess
import sys
import time
import zipfile


def ensure_dependencies():
    """Install required packages before importing them."""
    try:
        import tqdm  # noqa: F401
    except ImportError:
        requirements = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements])


def parse_arguments():
    epilog = """ИНСТРУКЦИЯ:
  Скрипт массово архивирует главы манги. В папке -i каждая подпапка
  считается одной главой и упаковывается в отдельный ZIP-архив.

Примеры:
  python "Архивирование-глав-(Archiving-chapters).py" -i "C:\\манга\\главы"
  python "Архивирование-глав-(Archiving-chapters).py" -i "C:\\путь с пробелами\\главы"

Примечания:
  - Уже существующие ZIP-архивы пропускаются.
  - Внутренняя структура вложенных папок внутри главы сохраняется.
  - Используется максимальное сжатие (ZIP_DEFLATED, уровень 9).
  - Если зависимости не установлены, они установятся автоматически.
"""
    parser = argparse.ArgumentParser(
        description='Bulk archive manga chapter directories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog)
    parser.add_argument('-i', '--input', type=str, required=True,
                        help='Path to the folder with many manga chapters')
    return parser.parse_args()


def archive_directories(source_dir):
    from tqdm import tqdm
    start_time = time.time()

    directories = [
        name for name in os.listdir(source_dir)
        if os.path.isdir(os.path.join(source_dir, name))
    ]

    for directory in tqdm(directories):
        zip_path = os.path.join(source_dir, f"{directory}.zip")
        if os.path.exists(zip_path):
            continue

        directory_path = os.path.join(source_dir, directory)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
            for root, _, filenames in os.walk(directory_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if os.path.isfile(file_path):
                        arcname = os.path.relpath(file_path, directory_path)
                        zip_file.write(file_path, arcname=arcname)

    print(f"Total execution time: {time.time() - start_time:.2f} seconds")


if __name__ == '__main__':
    ensure_dependencies()
    args = parse_arguments()
    archive_directories(args.input)
