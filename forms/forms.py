from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User # Menggunakan models.User untuk validasi
from database import get_db # Impor get_db

class RegistrationForm(FlaskForm):
    """Form untuk pendaftaran user baru."""
    username = StringField('Nama Pengguna', validators=[DataRequired('Nama pengguna wajib diisi.'), Length(min=4, max=20, message='Nama pengguna harus antara 4 hingga 20 karakter.')])
    email = StringField('Email', validators=[DataRequired('Email wajib diisi.'), Email('Format email tidak valid.')])
    password = PasswordField('Kata Sandi', validators=[DataRequired('Kata sandi wajib diisi.'), Length(min=6, message='Kata sandi minimal 6 karakter.')])
    confirm_password = PasswordField('Konfirmasi Kata Sandi', 
                                     validators=[DataRequired('Konfirmasi kata sandi wajib diisi.'), EqualTo('password', message='Kata sandi tidak cocok.')])
    submit = SubmitField('Daftar')

    def validate_username(self, username):
        """Validator kustom untuk username yang sudah ada."""
        user = User.find_by_username(username.data)
        if user:
            raise ValidationError('Nama pengguna ini sudah digunakan. Harap pilih yang lain.')

    def validate_email(self, email):
        """Validator kustom untuk email yang sudah ada."""
        user = get_db().users.find_one({"email": email.data}) 
        if user:
            raise ValidationError('Email ini sudah terdaftar. Harap gunakan email lain.')

class LoginForm(FlaskForm):
    """Form untuk login user."""
    username = StringField('Nama Pengguna', validators=[DataRequired('Nama pengguna wajib diisi.')])
    password = PasswordField('Kata Sandi', validators=[DataRequired('Kata sandi wajib diisi.')])
    submit = SubmitField('Masuk')

class TopicForm(FlaskForm):
    """Form untuk membuat atau mengedit topik."""
    title = StringField('Judul', validators=[DataRequired('Judul wajib diisi.'), Length(min=5, max=100, message='Judul harus antara 5 hingga 100 karakter.')])
    content = TextAreaField('Konten', validators=[DataRequired('Konten wajib diisi.'), Length(min=10, message='Konten minimal 10 karakter.')])
    submit = SubmitField('Buat Topik')

class PostForm(FlaskForm):
    """Form untuk membuat atau mengedit postingan/balasan."""
    content = TextAreaField('Balasan Anda', validators=[DataRequired('Balasan tidak boleh kosong.'), Length(min=5, message='Balasan minimal 5 karakter.')])
    submit = SubmitField('Kirim Balasan')
