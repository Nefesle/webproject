from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash
db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(50), unique=True, nullable=False, index=True)
    telegram = db.Column(db.String(100), index=True)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<User {self.nickname}>'

    def set_password(self, password):
        self.password = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @validates('nickname')
    def validate_nickname(self, key, nickname):
        if len(nickname) < 3 or len(nickname) > 16:
            raise ValueError('Никнейм должен быть длиной от 3 до 16 символов.')
        return nickname