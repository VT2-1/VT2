# Клонирование репозитория
git clone https://github.com/cherry220-v/VT2.git
cd VT2

# Убедитесь, что у вас установлена правильная версия Python
python3 --version

# Если Python версии ниже 3.10.7, установите нужную версию
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev

# Сделать Python 3.10 по умолчанию
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
sudo update-alternatives --config python3

# Создание и активация виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей из requirements.txt
pip install -r requirements.txt

# Установка PyInstaller
pip install pyinstaller

# Сборка проекта с помощью файла ui.spec
pyinstaller ui.spec

# Запуск собранного приложения
./dist/ui
