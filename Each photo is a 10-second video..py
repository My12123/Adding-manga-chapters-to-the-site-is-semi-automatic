import argparse
import os
import cv2
from pathlib import Path

def create_video_from_image(image_path, fps=30, duration=10):
    """Создает видео из одного изображения"""
    try:
        # Загружаем изображение
        img = cv2.imread(image_path)
        if img is None:
            print(f"Ошибка: Не удалось загрузить изображение {image_path}!")
            return False

        # Получаем размеры изображения
        height, width, _ = img.shape

        # Формируем имя выходного файла
        name_without_ext = os.path.splitext(image_path)[0]
        output_path = f"{name_without_ext}.mp4"

        # Создаём видеописатель
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(
            output_path,
            fourcc,
            fps,
            (width, height)
        )

        # Рассчитываем количество кадров
        total_frames = fps * duration

        # Генерируем кадры
        for _ in range(total_frames):
            video_writer.write(img)

        # Освобождаем ресурсы
        video_writer.release()
        print(f"✓ Видео создано: {output_path}")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка при обработке {image_path}: {e}")
        return False

def process_images(input_path, fps=30, duration=10):
    """Обрабатывает все изображения по указанному пути"""
    input_path = Path(input_path)
    
    # Определяем, что обрабатывать: файл или папку
    if input_path.is_file():
        # Один файл
        if input_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
            create_video_from_image(str(input_path), fps, duration)
        else:
            print(f"Ошибка: {input_path} не является изображением!")
    
    elif input_path.is_dir():
        # Папка с изображениями
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        image_files = []
        
        # Собираем все изображения из папки и подпапок
        for ext in image_extensions:
            image_files.extend(input_path.rglob(f'*{ext}'))
            image_files.extend(input_path.rglob(f'*{ext.upper()}'))
        
        if not image_files:
            print(f"В папке {input_path} не найдено изображений!")
            return
        
        print(f"Найдено {len(image_files)} изображений для обработки...")
        
        # Обрабатываем каждое изображение
        success_count = 0
        for image_file in image_files:
            if create_video_from_image(str(image_file), fps, duration):
                success_count += 1
        
        print(f"\nОбработка завершена! Успешно: {success_count}/{len(image_files)}")
        
    else:
        print(f"Ошибка: Путь {input_path} не существует!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Пакетное создание видео из изображений')
    parser.add_argument('-i', '--input', required=True, 
                       help='Путь к изображению или папке с изображениями')
    parser.add_argument('--fps', type=int, default=30,
                       help='Частота кадров (по умолчанию: 30)')
    parser.add_argument('--duration', type=int, default=10,
                       help='Длительность видео в секундах (по умолчанию: 10)')
    
    args = parser.parse_args()

    print("=== Конвертер изображений в видео ===")
    print(f"Входной путь: {args.input}")
    print(f"Частота кадров: {args.fps} FPS")
    print(f"Длительность видео: {args.duration} секунд")
    print("=" * 40)
    
    process_images(args.input, args.fps, args.duration)