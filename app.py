# Тестовое задание на позицию “Full-stack разработчик”в компанию MYCEGO
#
# Задание:
# Создайте веб-приложение на Flask или Django, которое взаимодействует с API Яндекс.Диска. Приложение должно реализовать следующий функционал:
# 1.	Просмотр файлов на Яндекс.Диске по вводу публичной ссылки (public_key):
# После успешной авторизации пользователь должен видеть список всех файлов и папок, хранящихся по указанной публичной ссылке.
# 2.	Загрузка определенных файлов:
# Пользователь должен иметь возможность выбирать файлы из списка и загружать их на свой локальный компьютер через интерфейс веб-приложения.
# Технические требования:
# •	Использовать Flask или Django в качестве фреймворка для веб-приложения.
# •	Получать список файлов с Яндекс.Диска с помощью REST API.
# •	Реализовать возможность скачивания выбранных пользователем файлов с Яндекс.Диска на локальный компьютер.
# •	Приложение должно иметь простой веб-интерфейс для отображения списка файлов и кнопок для их загрузки.
# Дополнительные требования:
# •	Для работы с API Яндекс.Диска можно использовать библиотеку requests/aiohttp или любую другую HTTP-клиентскую библиотеку.
# •	Документирование кода, аннотация типов.
# •	Код должен быть выложен на GitHub или аналогичный сервис, с историей коммитов.
# Критерии оценки:
# •	Корректность реализации авторизации и работы с API.
# •	Удобство и простота интерфейса.
# •	Читабельность и структурированность кода.
# •	Наличие инструкций по запуску и использованию приложения.
# •	Соответствие заданиям техническим и дополнительным требованиям.
# Опциональные задачи (необязательные, но будут плюсом):
# 1.	Реализовать систему фильтрации файлов по типу (например, только документы или только изображения).
# 2.	Возможность скачивания нескольких файлов одновременно.
# 3.	Реализовать кэширование списка файлов, чтобы не запрашивать его каждый раз с сервера.

# https://disk.yandex.ru/d/bmJBMpJjL-mrsQ


from flask import Flask, render_template, request, send_file, redirect, url_for
import requests
from io import BytesIO

app = Flask(__name__)

YANDEX_API_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"


# Получение списка файлов по публичной ссылке
def get_files_from_public_link(public_key: str) -> dict:
    params = {'public_key': public_key}
    response = requests.get(YANDEX_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {'error': 'Ошибка при получении данных с Яндекс.Диска.'}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        public_key = request.form.get("public_key")
        return redirect(url_for("files", public_key=public_key))
    return render_template("index.html")


@app.route("/files")
def files():
    public_key = request.args.get("public_key")
    files_data = get_files_from_public_link(public_key)
    if 'error' in files_data:
        return files_data['error']
    items = files_data['_embedded']['items']
    return render_template("files.html", items=items, public_key=public_key)


# Загрузка выбранного файла
@app.route("/download", methods=["GET"])
def download():
    public_key = request.args.get("public_key")
    file_path = request.args.get("file_path")

    download_url = f"{YANDEX_API_URL}/download?public_key={public_key}&path={file_path}"
    response = requests.get(download_url)

    if response.status_code == 200:
        download_link = response.json()['href']
        file_response = requests.get(download_link)
        return send_file(BytesIO(file_response.content),
                         download_name=file_path.split('/')[-1])
    else:
        return "Ошибка при загрузке файла."


if __name__ == "__main__":
    app.run(debug=False)
