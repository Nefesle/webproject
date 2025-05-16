from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    city = db.Column(db.String(100))
    telegram = db.Column(db.String(50))
    nickname = db.Column(db.String(16), unique=True)
    password = db.Column(db.String(128))
    applications = db.relationship('Application', backref='user', lazy=True)
    photos = db.relationship('Photo', backref='user')

    def set_password(self, password):
        self.password = generate_password_hash(password, method='pbkdf2:sha256')


class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)  # Первичный ключ
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    medal = db.Column(db.Boolean, default=False)  # Поле для заказа медали
    date = db.Column(db.String(8), nullable=False)
    distance = db.Column(db.Integer, nullable=False)


class Photo(db.Model):
    __tablename__ = 'photos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # Имя оригинального файла
    thumbnail_filename = db.Column(db.String(255), nullable=True)  # Имя миниатюры
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # ID пользователя
    is_anonymous = db.Column(db.Boolean, default=False)  # Флаг анонимности
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)  # Дата загрузки
