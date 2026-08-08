import argparse
import os


def is_black_or_white_photo(path, threshold=8):
    import cv2

    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        return False
    min_val, max_val = int(image.min()), int(image.max())
    return max_val <= threshold or min_val >= 255 - threshold


def remove_blank_photos(input_dir):
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Указанная папка не существует: {input_dir}")

    total = 0
    deleted = 0
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            total += 1
            path = os.path.join(root, file)
            try:
                if is_black_or_white_photo(path):
                    os.remove(path)
                    deleted += 1
            except OSError as e:
                print(f"Не удалось обработать {path}: {e}")

    print(f"Удалено {deleted} из {total} фото")
    return deleted


def main():
    epilog = """ИНСТРУКЦИЯ:
  Скрипт удаляет из папки (и всех вложенных подпапок) пустые фотографии,
  полностью белые или полностью чёрные.

Примеры:
  python remove_empty_black_white_photos.py -i "C:\\фото\\главы"
  python remove_empty_black_white_photos.py -i "C:\\путь с пробелами\\фото"

Примечания:
  - Удаление происходит необратимо, без корзины.
  - Фотографии, которые не удалось прочитать, пропускаются.
  - Порог пустоты по умолчанию: 8 уровней яркости.
"""
    parser = argparse.ArgumentParser(
        description="Удаляет пустые фото белых или чёрных из папки",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog)
    parser.add_argument("-i", "--input", dest="input", type=str, required=True, help="Путь к папке")
    args = parser.parse_args()

    remove_blank_photos(args.input)


if __name__ == "__main__":
    main()
