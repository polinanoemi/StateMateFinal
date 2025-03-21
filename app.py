import os
import pytesseract
from PIL import Image
import fitz  # PyMuPDF версии 1.25.3
import re
from flask import Flask, render_template, request, send_file, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequestKeyError
from openai import OpenAI


# Загрузка секретных ключей
with open("secrets.txt", "r") as f:
    secrets = dict(line.strip().split("=") for line in f if "=" in line)

# Настройка Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = secrets.get("TESSERACT_PATH")

# Инициализация DeepSeek API
client = OpenAI(api_key=secrets.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "data/uploads"
app.config["RESPONSE_FOLDER"] = "data/responses"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["RESPONSE_FOLDER"], exist_ok=True)

jinja_options = app.jinja_options.copy()
jinja_options.update(dict(
    block_start_string='<%',
    block_end_string='%>',
    variable_start_string='{{',
    variable_end_string='}}',
    comment_start_string='<#',
    comment_end_string='#>',
))
app.jinja_options = jinja_options


# Функции для обработки файлов
def extract_text_with_ocr(file_path: str) -> str:
    """Извлекает текст из файла с использованием OCR."""
    try:
        if file_path.lower().endswith('.pdf'):
            return extract_text_from_pdf(file_path)
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang='rus+eng')
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        return f"Ошибка OCR: {str(e)}"


def extract_text_from_pdf(file_path: str) -> str:
    """Извлекает текст из PDF с использованием PyMuPDF и Tesseract OCR."""
    try:
        text = ""
        with fitz.open(file_path) as doc:
            for page_num, page in enumerate(doc):
                pix = page.get_pixmap()
                img_path = os.path.join(app.config["UPLOAD_FOLDER"], f"page_{page_num + 1}.png")
                pix.save(img_path)
                img = Image.open(img_path)
                page_text = pytesseract.image_to_string(img, lang='rus+eng')
                text += page_text + "\n"
                os.remove(img_path)
        return text
    except Exception as e:
        return f"Ошибка при обработке PDF: {str(e)}"


def generate_response(text: str) -> str:
    """Генерирует ответ с помощью DeepSeek API."""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": 'Составь ответ на прикрепленный запрос госоргана, согласно законодательству РФ:' +text}
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка API: {str(e)}"


def save_to_file(content: str, filename: str, folder: str) -> str:
    """Сохраняет текст в файл."""
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


# Маршруты Flask
@app.route("/", methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        text = request.form.get('text')
        flag = True
        if not text:
            try:
                file = request.files['file']
                if file:
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    text = extract_text_with_ocr(filepath)
                else:
                    flag = False
            except BadRequestKeyError:
                flag = False

        if flag:
            res_text = generate_response(text)
            item3 = request.form.get('invisible_item2')
            item2 = request.form.get('invisible_item1')
            item1 = res_text
        else:
            item1 = request.form.get('invisible_item1')
            item2 = request.form.get('invisible_item2')
            item3 = request.form.get('invisible_item3')

        return render_template("StateMateFinal2.html", invisible_item1=item1, invisible_item2=item2, invisible_item3=item3)
    return render_template("StateMateFinal2.html", invisible_item1=' ', invisible_item2=' ', invisible_item3=' ')


@app.route("/dashboard")
def dashboard():
    # Чтение истории запросов и ответов
    history = []
    for filename in os.listdir(app.config["RESPONSE_FOLDER"]):
        if filename.endswith(".txt"):
            with open(os.path.join(app.config["RESPONSE_FOLDER"], filename), "r", encoding="utf-8") as f:
                history.append({"filename": filename, "content": f.read()})
    return render_template("dashboard.html", history=history)


@app.route("/demo", methods=["GET", "POST"])
def demo():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)
            text = extract_text_with_ocr(filepath)
            response = generate_response(text)
            save_to_file(response, f"response_{file.filename}.txt", app.config["RESPONSE_FOLDER"])
            return render_template("demo.html", response=response)
    return render_template("demo.html")


@app.route("/contacts")
def contacts():
    return render_template("contacts.html")


@app.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join(app.config["RESPONSE_FOLDER"], filename), as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
