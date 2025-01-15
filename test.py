import argparse
import sys

# Создаем парсер для аргументов командной строки
parser = argparse.ArgumentParser(description="VT2 help message.\n--log /path to write log to file.\nargs to open files.")
parser.add_argument('files', nargs='*', help="Список файлов для открытия")
parser.add_argument('--log', type=str, help="Путь к файлу лога", default=None)

# Обрабатываем аргументы
args = parser.parse_args()

# Обрабатываем аргумент с флагом --log
if args.log:
    log_file_path = args.log
    print(f"Лог будет записан в файл: {log_file_path}")
else:
    log_file_path = None
    print("Лог не указан.")

# Пример использования пути к лог-файлу
if log_file_path:
    # Здесь можно открыть лог-файл или передать путь в соответствующий объект для записи лога
    with open(log_file_path, 'a') as log_file:
        log_file.write("Логирование начато...\n")

# Пример открытия файлов (если есть)
if args.files:
    print(args.files)
