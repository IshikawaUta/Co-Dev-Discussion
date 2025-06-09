from flask import Flask, redirect, url_for
from flask_login import LoginManager
from database import init_db
from models import User # Pastikan User diimpor dari models.py
from blueprints.auth import auth_bp
from blueprints.forum import forum_bp
# Import fungsi create_messages_blueprint, bukan langsung messages_bp
from blueprints.messages import create_messages_blueprint 
import os
from dotenv import load_dotenv
from flask_socketio import SocketIO # Import SocketIO

load_dotenv() # Memuat variabel dari .env

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Tambahkan baris ini untuk membuat fungsi str() tersedia di Jinja2
app.jinja_env.globals.update(str=str)

# Inisialisasi Flask-Login
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

# Inisialisasi Flask-SocketIO setelah inisialisasi Flask app
# Gunakan `async_mode='eventlet'` atau `async_mode='gevent'` jika Anda berencana untuk deployment yang serius
# Untuk pengembangan, mode default biasanya cukup.
socketio = SocketIO(app, cors_allowed_origins="*") # Izinkan CORS jika diperlukan, atau batasi sesuai kebutuhan

# Registrasi Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(forum_bp, url_prefix='/') # Forum di root URL

# Buat instance blueprint messages dengan meneruskan objek socketio
# Ini memecahkan circular import
messages_bp = create_messages_blueprint(socketio)
app.register_blueprint(messages_bp, url_prefix='/') # Pesan pribadi di root URL, atau bisa '/messages'


if __name__ == '__main__':
    # Pastikan debug=False saat produksi
    # Jalankan aplikasi dengan socketio.run
    socketio.run(app, debug=True)
