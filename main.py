from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, User  # Импортируем модели базы данных
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Для работы с flash-сообщениями
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "instance", "database.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Отключаем ненужные предупреждения

# Настройка путей
app.template_folder = 'html_files'  # Шаблоны находятся в html_files
app.static_folder = 'static'        # Статические файлы находятся в static

# Инициализация базы данных
db.init_app(app)

# Регулярные выражения для валидации
NAME_REGEX = re.compile(r'^[а-яА-ЯёЁ]+$')  # Имя и фамилия только на кириллице
CITY_REGEX = re.compile(r'^[а-яА-ЯёЁ\s-]+$')  # Город: только кириллица, пробелы и дефисы
TELEGRAM_REGEX = re.compile(r'^@[a-zA-Z0-9_]{3,}$')  # Телеграм: начинается с @, английские буквы, цифры, подчёркивания
NICKNAME_REGEX = re.compile(r'^[a-zA-Z0-9]{2,16}$')  # Никнейм: английские буквы, цифры, длина от 2 до 16
PASSWORD_REGEX = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
)  # Пароль: минимум 8 символов, одна заглавная, одна строчная, одна цифра, один спецсимвол


# Создание таблиц при первом запуске
with app.app_context():
    db.create_all()


# Главная страница
@app.route('/')
def index():
    return render_template('base.html')  # Используем render_template


# Страница регистрации
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        # Получаем данные из формы
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        city = request.form['city']
        telegram = request.form['telegram']  # Необязательное поле
        nickname = request.form['nickname']
        password = request.form['password']

        # Проверка фамилии
        if not NAME_REGEX.match(last_name) or len(last_name) < 2:
            flash('Фамилия должна быть написана на кириллице, без цифр и спецсимволов, минимум 2 символа.', 'error')
            return redirect(url_for('registration'))

        # Проверка города
        if not CITY_REGEX.match(city):
            flash('Город должен быть написан на кириллице, без спецсимволов.', 'error')
            return redirect(url_for('registration'))

            # Проверка телеграм-аккаунта (если указан)
        if telegram and not TELEGRAM_REGEX.match(telegram):
            flash('Телеграм-аккаунт должен начинаться с @ и содержать только английские буквы, цифры и подчёркивания.',
                  'error')
            return redirect(url_for('registration'))

            # Проверка никнейма
        if not NICKNAME_REGEX.match(nickname):
            flash('Никнейм должен быть написан английскими буквами, длина от 2 до 16 символов.', 'error')
            return redirect(url_for('registration'))

            # Проверка пароля
        if not PASSWORD_REGEX.match(password):
            flash(
                'Пароль должен содержать минимум 8 символов, одну заглавную букву, одну строчную букву, одну цифру и один спецсимвол.',
                'error')
            return redirect(url_for('registration'))

            # Проверка уникальности никнейма
        if User.query.filter_by(nickname=nickname).first():
            flash('Этот никнейм уже занят. Пожалуйста, выберите другой.', 'error')
            return redirect(url_for('registration'))

        # Хэшируем пароль
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Создание нового пользователя
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            city=city,
            telegram=telegram,
            nickname=nickname,
            password=hashed_password
        )

        new_user.set_password(password)

        try:
            # Добавление пользователя в базу данных
            db.session.add(new_user)
            db.session.commit()
            flash('Вы успешно зарегистрированы!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Произошла ошибка: {str(e)}', 'error')

    return render_template('registration.html')


# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nick = request.form.get('nickname')
        password = request.form.get('password')

        # Проверка, что данные были отправлены
        if not nick or not password:
            flash('Пожалуйста, заполните все поля.', 'error')
            return redirect(url_for('login'))

        # Поиск пользователя по никнейму
        user = User.query.filter(User.nickname == nick).first()

        # Проверка, найден ли пользователь
        if user is None:
            flash('Пользователь с таким никнеймом не найден.', 'error')
            return redirect(url_for('login'))

        # Проверка пароля
        if check_password_hash(user.password, password):
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный никнейм или пароль.', 'error')

    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)