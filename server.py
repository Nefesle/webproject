from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import FileField, BooleanField
from wtforms.validators import DataRequired
from models import db, User, Photo
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import Application
from datetime import datetime
from PIL import Image
import json
import os
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Для работы с flash-сообщениями
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "instance", "database.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Отключаем ненужные предупреждения
app.secret_key = '30186634f3c3a296a283eade295d4264'

# Настройка путей
app.template_folder = 'html_files'  # Шаблоны находятся в html_files
app.static_folder = 'static'  # Статические файлы находятся в static

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['THUMBNAIL_FOLDER'] = os.path.join(BASE_DIR, 'static', 'thumbnails')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['THUMBNAIL_FOLDER'], exist_ok=True)

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


def create_thumbnail(file_path, thumbnail_size=(150, 150)):

    try:
        image = Image.open(file_path)
        image.thumbnail(thumbnail_size)

        # Генерируем путь для миниатюры
        base_name, ext = os.path.splitext(file_path)
        thumbnail_filename = f"{base_name}_thumb{ext}"
        thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], os.path.basename(thumbnail_filename))

        # Сохраняем миниатюру
        image.save(thumbnail_path)
        return thumbnail_path
    except Exception as e:
        print(f"Ошибка при создании миниатюры: {e}")
        return None


class PhotoUploadForm(FlaskForm):
    photo = FileField('Загрузить фото', validators=[DataRequired()])
    anonymous = BooleanField('Опубликовать анонимно')


# Главная страница
@app.route('/')
def index():
    user = None

    if 'username' in session:
        user = User.query.filter_by(nickname=session['username']).first()

    photos = Photo.query.order_by(Photo.uploaded_at.desc()).limit(7).all()
    return render_template('base.html', logged_in=('username' in session), user=user, photos=photos)


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
        id_user = request.form.get('id')

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
            session['username'] = nick  # Сохраняем имя пользователя в сессии
            return redirect(url_for('index'))
        else:
            flash('Неверный никнейм или пароль.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


@app.route('/profile')
def profile():
    if 'username' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))

    # Получаем полный объект пользователя из БД
    user = User.query.filter_by(nickname=session['username']).first()

    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('index'))

    # Передаем объект user в шаблон
    return render_template('profile.html', user=user)


@app.route('/profile/photos')
def profile_photos():
    if 'username' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))

    user = User.query.filter_by(nickname=session['username']).first()
    photos = Photo.query.filter_by(user_id=user.id).order_by(Photo.uploaded_at.desc()).all()
    return render_template('profile_photos.html', photos=photos, user=user)


@app.route('/delete_photo/<int:photo_id>', methods=['POST'])
def delete_photo(photo_id):
    # Проверка авторизации
    if 'username' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))

    # Поиск фотографии
    photo = Photo.query.get(photo_id)
    if not photo:
        flash('Фотография не найдена.', 'error')
        return redirect(url_for('profile_photos'))

    # Проверка, принадлежит ли фотография текущему пользователю
    nickname = session['username']
    user = User.query.filter_by(nickname=nickname).first()
    if photo.user_id != user.id:
        flash('У вас нет прав для удаления этой фотографии.', 'error')
        return redirect(url_for('profile_photos'))

    # Удаление фотографии
    try:
        db.session.delete(photo)
        db.session.commit()
        flash('Фотография успешно удалена.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при удалении фотографии.', 'error')

    return redirect(url_for('profile_photos'))


@app.route('/event-application', methods=['GET', 'POST'])
def event_application():
    if 'username' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))

    user = User.query.filter_by(nickname=session['username']).first()
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('profile'))

    # Загрузка данных о мероприятиях из JSON-файла
    with open('static/events.json', 'r', encoding='utf-8') as f:
        events_data = json.load(f)

    # Получаем даты, на которые пользователь уже подал заявки
    registered_dates = [app.date for app in Application.query.filter_by(user_id=user.id).all()]

    if request.method == 'POST':
        selected_date = request.form.get('selected_date')
        medal = 'medal' in request.form
        selected_distance = request.form.get('selected_distance')

        if not selected_date:
            flash('Заполните обязательные поля', 'error')
            return redirect(url_for('event_application'))

        # Преобразуем текущую дату и выбранную дату в объекты datetime
        current_date = datetime.strptime(datetime.now().strftime('%d.%m'), '%d.%m')
        try:
            selected_date_obj = datetime.strptime(selected_date, '%d.%m')
        except ValueError:
            flash('Некорректный формат даты.', 'error')
            return redirect(url_for('event_application'))

        # Проверка на текущую дату
        if selected_date_obj < current_date:
            flash('Регистрация на бревет задним числом невозможна.', 'warning')
            return redirect(url_for('event_application'))

        # Проверка, была ли уже подана заявка на эту дату
        if selected_date in registered_dates:
            flash('Вы уже подали заявку на эту дату', 'error')
            return redirect(url_for('event_application'))

        new_application = Application(
            user_id=user.id,
            date=selected_date,
            medal=medal,
            distance=selected_distance
        )

        try:
            db.session.add(new_application)
            db.session.commit()
            flash('Заявка успешно отправлена!', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'error')
            return redirect(url_for('event_application'))

    print("Registered dates:", registered_dates)
    return render_template(
        'event_application.html',
        user=user,
        events=events_data,
        registered_dates=registered_dates  # Передаем даты в шаблон
    )

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))

    # Получаем пользователя из базы данных
    user = User.query.filter_by(nickname=session['username']).first()
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Получаем данные из формы
        new_nickname = request.form.get('nickname')
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')

        # Проверка никнейма
        if new_nickname and new_nickname != user.nickname:
            if User.query.filter_by(nickname=new_nickname).first():
                flash('Этот никнейм уже занят.', 'error')
                return redirect(url_for('edit_profile'))
            user.nickname = new_nickname
            session['username'] = new_nickname  # Обновляем сессию

        # Проверка пароля
        if old_password or new_password:
            if not check_password_hash(user.password, old_password):
                flash('Старый пароль неверен.', 'error')
                return redirect(url_for('edit_profile'))
                # Проверка нового пароля
            if new_password == old_password:
                flash('Пароли совпадают.', 'error')
                return redirect(url_for('edit_profile'))
            if not PASSWORD_REGEX.match(new_password):
                flash(
                    'Пароль должен содержать минимум 8 символов, одну заглавную букву, одну строчную букву, одну цифру и один спецсимвол.',
                    'error'
                )
                return redirect(url_for('edit_profile'))

            if new_password:
                user.password = generate_password_hash(new_password)

        # Сохраняем изменения
        try:
            db.session.commit()
            flash('Профиль успешно обновлён!', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'error')

    return render_template('edit_profile.html', user=user)


@app.route('/my-applications')
def my_applications():
    if 'username' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))

    # Получаем пользователя из сессии
    user = User.query.filter_by(nickname=session['username']).first()

    # Получаем все заявки пользователя
    applications = Application.query.filter_by(user_id=user.id).all()

    # Преобразуем данные для удобного отображения в шаблоне
    events_data = {}
    for app in applications:
        if app.date not in events_data:
            events_data[app.date] = []
        events_data[app.date].append({
            'id': app.id,
            'distance': app.distance,
            'medal': app.medal
        })

    return render_template('my_applications.html', events=events_data)


@app.route('/delete-application/<int:application_id>', methods=['POST'])
def delete_application(application_id):
    if 'username' not in session:
        flash('Требуется авторизация', 'error')
        return redirect(url_for('login'))

    # Получаем пользователя из сессии
    user = User.query.filter_by(nickname=session['username']).first()

    # Находим заявку
    application = Application.query.get(application_id)

    if not application or application.user_id != user.id:
        flash('Заявка не найдена или вы не имеете прав на её удаление', 'error')
        return redirect(url_for('my_applications'))

    try:
        db.session.delete(application)
        db.session.commit()
        flash('Заявка успешно удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении заявки: {str(e)}', 'error')

    return redirect(url_for('my_applications'))


@app.template_filter('datetimeformat')
def format_datetime(value, format="%d.%m.%Y %H:%M"):
    if isinstance(value, datetime):
        return value.strftime(format)
    return value


@app.route('/album')
def album():
    photos = Photo.query.order_by(Photo.uploaded_at.desc()).all()
    return render_template('album.html', photos=photos)


@app.route('/upload-photo', methods=['GET', 'POST'])
def upload_photo():
    if 'username' not in session:
        flash('Требуется авторизация для загрузки фото.', 'error')
        return redirect(url_for('login'))

    form = PhotoUploadForm()
    if form.validate_on_submit():
        # Получаем файл
        photo_file = form.photo.data
        if photo_file:
            # Сохраняем файл
            filename = secure_filename(photo_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo_file.save(file_path)

            # Создаем миниатюру
            thumbnail_path = create_thumbnail(file_path)
            thumbnail_filename = os.path.basename(thumbnail_path)

            # Создаем запись в базе данных
            user = User.query.filter_by(nickname=session['username']).first()
            new_photo = Photo(
                filename=filename,
                thumbnail_filename=thumbnail_filename,
                user_id=None if form.anonymous.data else user.id,
                is_anonymous=form.anonymous.data
            )
            try:
                db.session.add(new_photo)
                db.session.commit()
                flash('Фото успешно загружено!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка: {str(e)}', 'error')

    return render_template('upload_photo.html', form=form)


if __name__ == '__main__':
    app.run(debug=True)
