import subprocess

subprocess.call(['pip', 'install', 'Pillow'])

import argparse
import os
import sys
import tqdm


def main():
    parser = argparse.ArgumentParser(description="Удаляет пустые фото белых или чёрных из папки")
    parser.add_argument("-i", "--input", dest="input", type=str, required=True, help="Путь к папке")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"Указанная папка не существует: {args.input}")

    total = 0
    deleted = 0
    for root, dirs, files in os.walk(args.input):
        for file in files:
            total += 1
            path = os.path.join(root, file)

            if os.path.getsize(path) == 0:
                if is_black_or_white_photo(path):
                    os.remove(path)
                    deleted += 1

    print(f"Удалено {deleted} из {total} фото")


def is_black_or_white_photo(path):
    with open(path, "rb") as f:
        image = f.read()

    return len(set(image)) <= 2


if __name__ == "__main__":
    main()
