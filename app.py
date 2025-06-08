from flask import Flask, redirect, url_for
from flask_login import LoginManager
from database import init_db
from models import User # Pastikan User diimpor dari models.py
from blueprints.auth import auth_bp
from blueprints.forum import forum_bp
import os
from dotenv import load_dotenv

load_dotenv() # Memuat variabel dari .env

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Tambahkan baris ini untuk membuat fungsi str() tersedia di Jinja2
app.jinja_env.globals.update(str=str)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login' # Akan redirect ke halaman login jika user belum login

@login_manager.user_loader
def load_user(user_id):
    """
    Callback untuk Flask-Login yang memuat user dari ID.
    Digunakan setiap kali Flask-Login perlu mengambil objek user dari sesi.
    """
    return User.find_by_id(user_id)

# Inisialisasi database saat aplikasi dimulai
# Menggunakan app.app_context() memastikan bahwa operasi database dilakukan dalam konteks aplikasi
with app.app_context():
    init_db()

# Registrasi Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(forum_bp, url_prefix='/') # Forum di root URL

if __name__ == '__main__':
    # Pastikan debug=False saat produksi
    app.run(debug=True)
