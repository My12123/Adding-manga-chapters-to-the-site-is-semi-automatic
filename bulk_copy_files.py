import argparse
import shutil
import time
from pathlib import Path
from tqdm import tqdm

def copy_file_to_multiple_directories(source_file, destination_folder):
    """Copies a file to all subdirectories within a directory."""

    source_path = Path(source_file).resolve()  # Crucial: Resolve the path
    destination_dir = Path(destination_folder).resolve() #Crucial: Resolve the path

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}") #Print resolved path
    if not destination_dir.exists():
        raise NotADirectoryError(f"Destination folder not found: {destination_dir}") #Print resolved path
    if not destination_dir.is_dir():
        raise NotADirectoryError(f"Destination is not a directory: {destination_dir}")

    folders = [f for f in destination_dir.iterdir() if f.is_dir()]
    total_copies = len(folders)

    start_time = time.perf_counter()

    with tqdm(total=total_copies, desc="Copying files", unit="file") as pbar:
        for folder in folders:
            destination_path = folder / source_path.name
            try:
                shutil.copy2(source_path, destination_path)
                pbar.update(1)
                pbar.set_description(f"Copying to {folder.name}")
            except shutil.SameFileError:
                print(f"Source and destination are the same: {destination_path}")
                pbar.update(1)
            except OSError as e:
                print(f"Error copying to {destination_path}: {e}")
                pbar.update(1)
                pbar.set_description(f"Error copying to {folder.name}")

    elapsed_time = time.perf_counter() - start_time
    print(f"Total files copied: {total_copies}")
    print(f"Time taken: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    epilog = """ИНСТРУКЦИЯ:
  Скрипт копирует один файл во все подпапки указанной папки.

Примеры:
  python bulk_copy_files.py "C:\\файл.txt" -i "C:\\папка\\главы"
  python bulk_copy_files.py "logo.png" -i "C:\\путь с пробелами\\папка"

Примечания:
  - Копируются только непосредственные подпапки (без вложенности).
  - Если файл с таким именем уже есть, он будет перезаписан.
  - При ошибке копирования скрипт продолжает работу с остальными папками.
"""
    parser = argparse.ArgumentParser(
        description="Copy a file to all subdirectories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog)
    parser.add_argument("source_file", type=str, help="Path to the file to copy")
    parser.add_argument("-i", "--input", dest="destination_folder", type=str, required=True,
                        help="Folder whose subdirectories receive the copy")
    args = parser.parse_args()

    source_file = Path(args.source_file)  # Forward slashes are more portable
    destination_folder = Path(args.destination_folder)

    print(f"Source Path (before resolve): {source_file}") #Debug print
    print(f"Destination Path (before resolve): {destination_folder}") #Debug print

    copy_file_to_multiple_directories(source_file, destination_folder)
