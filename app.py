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


from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import requests
from io import BytesIO
from typing import Dict, Any
from flask_caching import Cache
import zipfile
import os
import logging
import re

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

YANDEX_API_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"

# Определение MIME-типов для документов
DOCUMENT_MIME_TYPES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/jpg'
    # Добавьте другие MIME-типы документов по необходимости
]


# Функция для проверки валидности URL Яндекс.Диска
def is_valid_yandex_disk_url(url: str) -> bool:
    pattern = r'^https?://disk\.yandex\.ru/d/[\w-]+$'
    return re.match(pattern, url) is not None


@cache.memoize(timeout=300)  # Кэшировать на 5 минут
def get_files_from_public_link(public_key: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Получает список файлов и папок по публичной ссылке Яндекс.Диска.
    """
    params = {'public_key': public_key, 'limit': limit, 'offset': offset}
    try:
        response = requests.get(YANDEX_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        logging.debug(f"Ответ API: {data}")
        return data
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
        return {'error': f"HTTP error occurred: {http_err}"}
    except Exception as err:
        logging.error(f"Other error occurred: {err}")
        return {'error': f"Other error occurred: {err}"}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        public_key = request.form.get("public_key")
        if not public_key:
            flash("Пожалуйста, введите публичную ссылку.", "danger")
            return redirect(url_for("index"))
        if not is_valid_yandex_disk_url(public_key):
            flash("Введена некорректная публичная ссылка на Яндекс.Диск.", "danger")
            return redirect(url_for("index"))
        return redirect(url_for("files", public_key=public_key))
    return render_template("index.html")


@app.route("/files")
def files():
    public_key = request.args.get("public_key")
    try:
        page = max(int(request.args.get("page", 1)), 1)  # Обеспечить, что страница >= 1
    except ValueError:
        page = 1
    file_type = request.args.get("file_type", "")
    limit = 100
    offset = (page - 1) * limit

    logging.debug(f"Получен запрос с public_key={public_key}, page={page}, file_type={file_type}")

    files_data = get_files_from_public_link(public_key, limit=limit, offset=offset)
    if 'error' in files_data:
        flash(files_data['error'], "danger")
        return redirect(url_for("index"))

    items = files_data.get('_embedded', {}).get('items', [])

    # Фильтрация только словарей
    items = [item for item in items if isinstance(item, dict)]

    # Функция для безопасного получения mime_type
    def get_mime_type(item):
        file_info = item.get('file', {})
        if isinstance(file_info, dict):
            return file_info.get('mime_type', '').lower()
        return ''

    # Логирование MIME-типов всех файлов
    for idx, item in enumerate(items):
        mime_type = get_mime_type(item)
        logging.debug(f"Файл {idx}: {item.get('name', 'Без имени')} - MIME тип: {mime_type}")

    # Фильтрация по типу
    if file_type:
        if file_type == 'image':
            items = [
                item for item in items
                if item.get('type') == 'file' and
                   get_mime_type(item).startswith('image/')
            ]
        elif file_type == 'document':
            items = [
                item for item in items
                if item.get('type') == 'file' and
                   get_mime_type(item) in [m.lower() for m in DOCUMENT_MIME_TYPES]
            ]
        elif file_type == 'other':
            items = [
                item for item in items
                if item.get('type') == 'file' and
                   not get_mime_type(item).startswith('image/') and
                   get_mime_type(item) not in [m.lower() for m in DOCUMENT_MIME_TYPES]
            ]

    # Получение общего количества элементов без учёта фильтрации
    total_items = files_data.get('_embedded', {}).get('total', 0)

    logging.debug(f"Total items: {total_items}")

    # Определение наличия следующей и предыдущей страниц
    next_page = page + 1 if offset + limit < total_items else None
    prev_page = page - 1 if page > 1 else None

    logging.debug(f"Pagination - Prev: {prev_page}, Next: {next_page}")

    return render_template(
        "files.html",
        items=items,
        public_key=public_key,
        next_page=next_page,
        prev_page=prev_page,
        file_type=file_type
    )


# Загрузка выбранного файла
@app.route("/download", methods=["GET"])
def download():
    public_key = request.args.get("public_key")
    file_path = request.args.get("file_path")

    if not public_key or not file_path:
        flash("Некорректные параметры для скачивания.", "danger")
        return redirect(url_for("index"))

    download_url = f"{YANDEX_API_URL}/download"
    params = {'public_key': public_key, 'path': file_path}
    try:
        response = requests.get(download_url, params=params)
        response.raise_for_status()
        download_link = response.json()['href']
        file_response = requests.get(download_link)
        return send_file(
            BytesIO(file_response.content),
            download_name=os.path.basename(file_path),
            as_attachment=True
        )
    except requests.exceptions.HTTPError as http_err:
        flash(f"HTTP error occurred: {http_err}", "danger")
    except Exception as err:
        flash(f"Error occurred: {err}", "danger")
    return redirect(url_for("files", public_key=public_key))


# Скачивание нескольких файлов
@app.route("/download_multiple", methods=["POST"])
def download_multiple():
    public_key = request.form.get("public_key")
    file_paths = request.form.getlist("file_paths")

    if not public_key or not file_paths:
        flash("Нет выбранных файлов для скачивания.", "warning")
        return redirect(url_for("files", public_key=public_key))

    # Создание временного архива
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for file_path in file_paths:
            download_url = f"{YANDEX_API_URL}/download"
            params = {'public_key': public_key, 'path': file_path}
            try:
                response = requests.get(download_url, params=params)
                response.raise_for_status()
                download_link = response.json()['href']
                file_response = requests.get(download_link)
                zip_file.writestr(os.path.basename(file_path), file_response.content)
            except requests.exceptions.HTTPError:
                flash(f"Ошибка при загрузке файла: {file_path}", "danger")
            except Exception:
                flash(f"Не удалось загрузить файл: {file_path}", "danger")

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        download_name='files.zip',
        as_attachment=True
    )


if __name__ == "__main__":
    app.run(debug=False)
