# database.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
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
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) # Timeout 5 detik
            # The ismaster command is cheap and does not require auth.
            client.admin.command('ismaster') 
            db = client.forum_db # Ganti 'forum_db' dengan nama database yang Anda inginkan di Atlas
            print("MongoDB connected successfully!") # Untuk debugging
        except ServerSelectionTimeoutError as err:
            print(f"MongoDB connection timeout: {err}")
            # Anda bisa mempertimbangkan untuk mengeluarkan exception atau menangani ini dengan cara lain
            # Misalnya, aplikasi tidak akan berfungsi tanpa DB, jadi mungkin exit.
            raise ConnectionFailure(f"Could not connect to MongoDB: {err}")
        except ConnectionFailure as err:
            print(f"MongoDB connection failed: {err}")
            raise ConnectionFailure(f"Could not connect to MongoDB: {err}")
        except Exception as err:
            print(f"An unexpected error occurred during MongoDB connection: {err}")
            raise Exception(f"Unexpected error connecting to MongoDB: {err}")
    return db

def get_db():
    """
    Mengembalikan objek database yang sudah terinisialisasi.
    """
    if db is None:
        print("Warning: Database not initialized, attempting to initialize...")
        init_db() # Coba inisialisasi jika belum
        if db is None: # Jika masih null setelah mencoba inisialisasi
            raise Exception("Database not initialized. Call init_db() first or check connection issues.")
    return db
