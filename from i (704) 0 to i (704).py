import argparse
import os

def rename_files(input_path):
    """
    Удаляет один пробел и один символ '0' в конце названий файлов
    """
    if not os.path.exists(input_path):
        print(f"Ошибка: путь {input_path} не существует")
        return
        if not os.path.isdir(input_path):
        print(f"Ошибка: {input_path} не является директорией")
        return

    files_processed = 0
    files_renamed = 0

    for filename in os.listdir(input_path):
        old_path = os.path.join(input_path, filename)
        
        if os.path.isfile(old_path):
            files_processed += 1
            
            # Разделяем имя файла и расширение
            name, ext = os.path.splitext(filename)
            
            # Удаляем один пробел и один '0' в конце названия
            new_name = name
            if new_name.endswith(' 0'):
                # Удаляем " 0" в конце
                new_name = new_name[:-2]
            elif new_name.endswith('0'):
                # Удаляем только '0' в конце
                new_name = new_name[:-1]
            elif new_name.endswith(' '):
                # Удаляем только пробел в конце
                new_name = new_name[:-1]
            
            # Формируем новое имя файла
            new_filename = new_name + ext
            new_path = os.path.join(input_path, new_filename)
            
            # Переименовываем только если имя изменилось и файл с новым именем не существует
            if new_path != old_path:
                if not os.path.exists(new_path):
                    try:
                        os.rename(old_path, new_path)
                        print(f"Переименовано: '{filename}' -> '{new_filename}'")
                        files_renamed += 1
                    except OSError as e:
                        print(f"Ошибка при переименовании '{filename}': {str(e)}")
                else:
                    print(f"Предупреждение: файл '{new_filename}' уже существует, пропускаем '{filename}'")

    print(f"\nОбработано файлов: {files_processed}")
    print(f"Переименовано файлов: {files_renamed}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Удаление одного пробела и одного нуля в конце названий фотографий'
    )
    parser.add_argument(
        '-i', '--input', 
        required=True, 
        help='Путь к директории с фотографиями'
    )
    
    args = parser.parse_args()
    rename_files(args.input)
