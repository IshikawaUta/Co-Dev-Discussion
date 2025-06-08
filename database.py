# database.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv() # Memuat variabel dari .env

MONGO_URI = os.getenv("MONGO_URI")

client = None
db = None

def init_db():
    """
    Menginisialisasi koneksi ke database MongoDB.
    Dipanggil saat aplikasi dimulai.
    """
    global client, db
    if client is None:
        client = MongoClient(MONGO_URI)
        db = client.forum_db # Ganti 'forum_db' dengan nama database yang Anda inginkan di Atlas
        print("MongoDB connected successfully!") # Untuk debugging
    return db

def get_db():
    """
    Mengembalikan objek database yang sudah terinisialisasi.
    """
    if db is None:
        raise Exception("Database not initialized. Call init_db() first.")
    return db