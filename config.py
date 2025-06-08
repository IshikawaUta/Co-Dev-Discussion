# config.py
import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    MONGO_URI = os.getenv('MONGO_URI')
    # Anda bisa menambahkan konfigurasi lain di sini di masa mendatang
    # seperti UPLOAD_FOLDER, MAIL_SERVER, dll.