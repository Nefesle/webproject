from flask import Flask, send_from_directory, render_template

app = Flask(__name__)


# Главная страница
@app.route('/')
def index():
    return send_from_directory('html_files', 'base.html')


# Страница регистрации
@app.route('/registration')
def registration():
    return send_from_directory('html_files', 'registration.html')


if __name__ == '__main__':
    app.run(debug=True)