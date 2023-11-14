import shutil
import os
from tqdm import tqdm
import time

# Путь к исходному файлу
source_file = "./000.png"

# Путь к папке, в которой находятся каталоги для копирования
destination_folder = "G:\G"

# Получение списка всех каталогов в папке назначения
folders = [f.path for f in os.scandir(destination_folder) if f.is_dir()]

# Получение общего количества копирований
total_copies = len(folders)

# Начало счетчика времени
start_time = time.time()

# Проход по каждому каталогу и выполнение копирования
for folder in tqdm(folders, desc="Copying"):
    # Создание пути для копии файла в текущем каталоге
    destination_path = os.path.join(folder, os.path.basename(source_file))
    
    # Проверка, существует ли уже файл с таким же именем
    if not os.path.exists(destination_path):
        # Копирование файла
        shutil.copy(source_file, destination_path)

# Расчет времени выполнения
elapsed_time = time.time() - start_time
print(f"Total copies: {total_copies}")
print(f"Time taken: {elapsed_time:.2f} seconds")
