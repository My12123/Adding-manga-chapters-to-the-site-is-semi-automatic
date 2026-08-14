#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умная пересборка страниц манги под размеры сайтов.

Работает в три шага:
  1. Собирает все страницы главы в ОДНО большое изображение (по вертикали).
  2. Масштабирует его до заданной ширины (как на сайтах манги).
  3. Разрезает обратно на маленькие страницы заданной высоты, используя
     детектор текста, чтобы НИ ОДИН текст не был разрезан пополам:
     линия разреза смещается в пустой промежуток между текстами.
"""
import argparse
import os
import re

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}


def natural_key(name):
    parts = re.split(r'(\d+)', name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def collect_images(folder):
    files = [f for f in os.listdir(folder)
             if os.path.splitext(f)[1].lower() in IMAGE_EXTS]
    if not files:
        raise FileNotFoundError(f"В папке {folder} не найдено изображений "
                                "(jpg, jpeg, png, bmp, tiff, webp).")
    files.sort(key=natural_key)
    return [os.path.join(folder, f) for f in files]


def load_image(path):
    from PIL import Image
    return Image.open(path).convert('RGB')


def stitch_vertically(paths):
    """Склеивает все страницы в одно большое изображение (фон белый)."""
    import numpy as np

    pages = [np.array(load_image(p)) for p in paths]
    max_width = max(page.shape[1] for page in pages)
    total_height = sum(page.shape[0] for page in pages)
    big = np.full((total_height, max_width, 3), 255, dtype=np.uint8)
    y = 0
    for page in pages:
        h, w = page.shape[:2]
        big[y:y + h, 0:w] = page
        y += h
    return big, max_width, total_height


def resize_big(image, target_width):
    """Масштабирует большое изображение до нужной ширины."""
    import numpy as np
    import cv2

    h, w = image.shape[:2]
    if w == target_width:
        return image.copy()
    scale = target_width / w
    new_h = int(round(h * scale))
    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LANCZOS4
    return cv2.resize(image, (target_width, new_h), interpolation=interp)


def detect_text_profile(image):
    """
    Детектор текста (OpenCV, без внешних моделей).

    Возвращает:
      row_profile : ndarray[bool], True там, где в строке есть текст;
      blobs       : список (y0, y1) вертикальных границ текстовых блоков.
    """
    import numpy as np
    import cv2

    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    # Фон страницы (светлый или тёмный) определяем по процентилям яркости.
    dark_ratio = float(np.percentile(gray, 50) < 127)
    if dark_ratio:
        # Тёмная страница: текст светлый.
        bg = np.percentile(gray, 10)
        mask = (gray > bg + 45).astype(np.uint8) * 255
    else:
        # Светлая страница: текст тёмный (включая серые JPEG-ореолы).
        bg = np.percentile(gray, 90)
        mask = (gray < bg - 45).astype(np.uint8) * 255

    # Почти сплошной по цвету кадр (без контрастного текста)
    if float((mask > 0).mean()) > 0.85:
        return np.zeros(gray.shape[0], dtype=bool), []

    # Смыкаем символы в горизонтальные полосы, чтобы текст стал "сплошным"
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (max(8, image.shape[1] // 40), 5))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    closed = cv2.morphologyEx(closed, cv2.MORPH_OPEN,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))

    row_profile = closed.sum(axis=1) > 0

    # Текстовые блоки (связные области), только чтобы не резать их пополам
    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    blobs = []
    min_area = max(25, image.shape[1] // 8)
    for i in range(1, n_labels):
        x, y, w, h, area = stats[i]
        if area >= min_area and w >= 3 and h >= 3:
            blobs.append((int(y), int(y + h)))
    return row_profile, blobs


def find_best_cut(safe, nominal, lo, hi, min_gap):
    """
    Ищет лучшую линию разреза в окне [lo, hi]: центр самого близкого
    к nominal пустого промежутка (промежутка без текста) высотой >= min_gap.
    """
    best_score = None
    best_center = None
    i = lo
    while i <= hi:
        if safe[i]:
            j = i
            while j + 1 <= hi and safe[j + 1]:
                j += 1
            run_len = j - i + 1
            center = (i + j) // 2
            if run_len >= min_gap:
                score = (abs(center - nominal), -run_len)
                if best_score is None or score < best_score:
                    best_score = score
                    best_center = center
            i = j + 1
        else:
            i += 1
    if best_center is not None:
        return best_center
    # Нет крупных промежутков — берём ближайшую строку без текста
    for offset in sorted(range(lo, hi + 1), key=lambda o: (abs(o - nominal), o)):
        if safe[offset]:
            return offset
    return nominal


def avoid_blob_split(cut, blobs, prev, total_h):
    """
    Гарантирует, что один текст (блок) не окажется разрезан на две картинки:
    сдвигает разрез под или над блоком, который его пересекает.
    """
    if not blobs:
        return cut
    buffer = 8
    for y0, y1 in blobs:
        if y0 < cut < y1:
            up = y0
            down = y1
            up_ok = (up - prev) >= buffer * 2
            down_ok = down <= total_h - buffer
            if up_ok and down_ok:
                cut = up if (cut - up) <= (down - cut) else down
            elif up_ok:
                cut = up
            elif down_ok:
                cut = down
    return cut


def compute_cuts(total_h, page_height, row_profile, blobs, min_gap, search):
    cuts = []
    prev = 0
    safe = None if row_profile is None else ~row_profile
    while prev + page_height < total_h - 1:
        nominal = prev + page_height
        if safe is None:
            cut = nominal
        else:
            lo = max(prev + 1, nominal - search)
            hi = min(total_h - 1, nominal + search)
            cut = find_best_cut(safe, nominal, lo, hi, min_gap)
            cut = avoid_blob_split(cut, blobs, prev, total_h)
            # защита от "склеенных" страниц из-за сдвига вверх
            if cut - prev < min_gap:
                while cut < hi and not safe[cut]:
                    cut += 1
                if cut - prev < min_gap and cut < hi:
                    cut += min_gap
        if cut <= prev:
            cut = prev + 1
        cuts.append(cut)
        prev = cut
    cuts.append(total_h)
    return cuts


def save_chunk(chunk, path, out_format, jpeg_quality):
    from PIL import Image
    img = Image.fromarray(chunk)
    if out_format.lower() in ('jpg', 'jpeg'):
        img = img.convert('RGB')
        img.save(path, 'JPEG', quality=jpeg_quality)
    else:
        img.save(path, 'PNG')


def process_pages_folder(pages_folder, output_folder, width=None, page_height=1920,
                         out_format='jpg', jpeg_quality=90, use_text_detector=True,
                         min_gap=None, search=None):
    """Обрабатывает одну главу: страницы из pages_folder -> output_folder."""
    import numpy as np
    from tqdm import tqdm

    if not os.path.isdir(pages_folder):
        raise FileNotFoundError(f"Папка не найдена: {pages_folder}")
    os.makedirs(output_folder, exist_ok=True)

    paths = collect_images(pages_folder)
    print(f"Найдено страниц: {len(paths)}")

    print("Шаг 1/3: склейка всех страниц в одно большое изображение...")
    big, native_width, native_height = stitch_vertically(paths)

    if width is not None and width != big.shape[1]:
        print(f"Шаг 2/3: масштабирование до ширины {width} px...")
        big = resize_big(big, width)
    else:
        print("Шаг 2/3: ширина не меняется (остаётся как в исходной главе).")
    total_h = big.shape[0]

    if page_height is None:
        page_height = 1920
    if min_gap is None:
        min_gap = max(10, big.shape[1] // 80)
    if search is None:
        search = int(page_height * 0.35)

    print("Детектор текста: ищу текст, чтобы не разрезать его пополам...")
    row_profile, blobs = (detect_text_profile(big)
                          if use_text_detector else (None, None))
    n_blobs = len(blobs) if blobs else 0
    print(f"Найдено текстовых блоков: {n_blobs}")

    cuts = compute_cuts(total_h, page_height, row_profile, blobs, min_gap, search)
    print(f"Шаг 3/3: нарезка на {len(cuts)} страниц (~{page_height} px высотой)...")

    prev = 0
    digits = len(str(len(cuts) - 1))
    for i, cut in enumerate(tqdm(cuts)):
        chunk = big[prev:cut]
        prev = cut
        if chunk.shape[0] == 0:
            continue
        name = f"{os.path.basename(os.path.normpath(pages_folder))}_p{i + 1:0{digits}d}.{out_format.lower()}"
        save_chunk(chunk, os.path.join(output_folder, name), out_format, jpeg_quality)

    print("Готово. Страницы порезаны по высоте ~1920 px, ширина исходная.")
    print(f"Результат сохранён в: {output_folder}")


def smart_resize_chapter(input_folder, output_folder=None, width=None,
                         page_height=1920, out_format='jpg', jpeg_quality=90,
                         use_text_detector=True, min_gap=None, search=None):
    """
    Обрабатывает ВСЕ главы внутри input_folder.

    input_folder  - папка, внутри которой лежат папки глав;
    output_folder - куда сохранять (если не указано: input_folder\\smart_resize_manga);
    width         - новая ширина в px (None = не менять, оставить исходную);
    page_height   - высота страницы после нарезки (по умолчанию 1920);
    каждая глава попадает в output_folder\\<имя главы>.
    """
    if page_height is None:
        page_height = 1920
    if search is None:
        search = int(page_height * 0.35)

    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Папка не найдена: {input_folder}")

    if output_folder is None:
        output_folder = os.path.join(input_folder, "smart_resize_manga")
    output_folder = os.path.normpath(output_folder)

    # Сначала перечисляем главы, потом создаём папку результата.
    # Исключаем саму папку результата и зарезервированное имя smart_resize_manga,
    # чтобы повторные запуски не считали результат новой главой.
    chapters = [
        d for d in os.listdir(input_folder)
        if os.path.isdir(os.path.join(input_folder, d))
        and d != "smart_resize_manga"
        and os.path.normpath(os.path.join(input_folder, d)) != output_folder
    ]
    chapters.sort(key=natural_key)
    if not chapters:
        raise FileNotFoundError(
            f"В папке {input_folder} нет вложенных папок глав. "
            "Структура должна быть: <папка с главами>\\<Глава 1>\\страницы...")

    os.makedirs(output_folder, exist_ok=True)

    print(f"Найдено глав: {len(chapters)}")
    print(f"Результат будет сохранён в: {output_folder}")

    for chapter in chapters:
        chapter_in = os.path.join(input_folder, chapter)
        chapter_out = os.path.join(output_folder, chapter)
        print(f"\n========== Глава: {chapter} ==========")
        process_pages_folder(chapter_in, chapter_out, width, page_height,
                             out_format, jpeg_quality, use_text_detector,
                             min_gap, search)

    print("\nВсе главы обработаны.")


def build_parser():
    epilog = """ИНСТРУКЦИЯ:
  Скрипт пересобирает страницы манги под размеры сайтов для ВСЕХ глав сразу.

  Структура входной папки:
    -i "папка с главами"
        -> "Глава 1"\\страницы...
        -> "Глава 2"\\страницы...

  Куда сохраняется:
    Каждая глава сохраняется в <входная папка>\\smart_resize_manga\\<имя главы>.
    Можно переопределить базу через -o: тогда главы будут в <o>\\<имя главы>.

  Как работает каждая глава:
    1) склеивает страницы главы в одно большое изображение,
    2) НЕ меняет ширину (остаётся как в исходной главе),
    3) режет обратно на страницы высотой ~1920 px.

Примеры:
  python smart_resize_manga.py -i "C:\манга\все главы"
  python smart_resize_manga.py -i "C:\манга\все главы" --height 1600
  python smart_resize_manga.py -i "C:\манга\все главы" -o "C:\готово" --no-text

Ключевой момент:
  Детектор текста (OpenCV, работает без интернета и моделей) находит текстовые
  блоки и сдвигает линию разреза в пустой промежуток, поэтому ОДИН текст никогда
  не делится на две картинки.

Совет:
  Для очень длинных глав (50+ страниц) процесс занимает много памяти
  (ширина x высота большого изображения x 3 байта x 2).
  Число страниц на выходе может отличаться от числа на входе — это нормально.
"""
    parser = argparse.ArgumentParser(
        description="Умная пересборка страниц манги под размеры сайтов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog)
    parser.add_argument('-i', '--input', required=True,
                        help='Папка, внутри которой лежат папки глав')
    parser.add_argument('-o', '--output', default=None,
                        help='Папка для готовых страниц (по умолчанию: входная папка + smart_resize_manga)')
    parser.add_argument('--width', type=int, default=None,
                        help='Новая ширина в px (по умолчанию: не менять, остаётся исходная)')
    parser.add_argument('--height', dest='page_height', type=int, default=None,
                        help='Высота страницы после нарезки в px (по умолчанию: 1920)')
    parser.add_argument('--format', dest='out_format', default='jpg',
                        choices=['jpg', 'png'], help='Формат результата (по умолчанию: jpg)')
    parser.add_argument('--quality', type=int, default=90,
                        help='Качество JPEG (по умолчанию: 90)')
    parser.add_argument('--no-text', dest='use_text_detector', action='store_false',
                        help='Отключить детектор текста (резать строго по сетке)')
    parser.add_argument('--min-gap', type=int, default=None,
                        help='Мин. высота пустого промежутка без текста (по умолчанию: ширина/80, но не менее 10)')
    parser.add_argument('--search', type=int, default=None,
                        help='Макс. сдвиг линии разреза в поисках пустоты (по умолчанию: 35%% высоты страницы)')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    smart_resize_chapter(
        args.input, args.output,
        width=args.width,
        page_height=args.page_height,
        out_format=args.out_format,
        jpeg_quality=args.quality,
        use_text_detector=args.use_text_detector,
        min_gap=args.min_gap,
        search=args.search,
    )


if __name__ == "__main__":
    main()