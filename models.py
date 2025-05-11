from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash
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

    def set_password(self, password):
        self.password = generate_password_hash(password, method='pbkdf2:sha256')


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(100))

    def __repr__(self):
        return f'<Event {self.title}>'


class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    experience = db.Column(db.Text, nullable=False)
    equipment = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')  # pending/approved/rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship('Event', backref='applications')

    def __repr__(self):
        return f'<User {self.nickname}>'

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @validates('nickname')
    def validate_nickname(self, key, nickname):
        if len(nickname) < 3 or len(nickname) > 16:
            raise ValueError('Никнейм должен быть длиной от 3 до 16 символов.')
        return nickname
