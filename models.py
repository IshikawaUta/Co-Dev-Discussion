import datetime
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from database import get_db

class User(UserMixin):
    """
    Model untuk user yang akan login.
    Mengimplementasikan UserMixin untuk integrasi dengan Flask-Login.
    """
    def __init__(self, username, email, password_hash, role='user', _id=None):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role  # Default role adalah 'user', bisa 'admin'
        self._id = _id if _id else ObjectId()

    def get_id(self):
        """Mengembalikan ID unik user sebagai string, diperlukan oleh Flask-Login."""
        return str(self._id)

    def is_admin(self):
        """Mengecek apakah user memiliki role 'admin'."""
        return self.role == 'admin'

    @staticmethod
    def find_by_username(username):
        """Mencari user berdasarkan username."""
        user_data = get_db().users.find_one({"username": username})
        if user_data:
            return User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=user_data["password_hash"],
                role=user_data.get("role", 'user'),  # Ambil role, default 'user'
                _id=user_data["_id"]
            )
        return None

    @staticmethod
    def find_by_id(user_id):
        """Mencari user berdasarkan ObjectId."""
        try:
            # Pastikan user_id bisa dikonversi ke ObjectId
            user_data = get_db().users.find_one({"_id": ObjectId(user_id)})
            if user_data:
                return User(
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=user_data["password_hash"],
                    role=user_data.get("role", 'user'),  # Ambil role, default 'user'
                    _id=user_data["_id"]
                )
        except Exception:
            # Mengatasi error jika user_id bukan format ObjectId yang valid
            return None
        return None

    def save(self):
        """Menyimpan user baru ke database. Password_hash diasumsikan sudah di-hash."""
        get_db().users.insert_one({
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "role": self.role,
            "created_at": datetime.datetime.utcnow() # Tambahkan timestamp pembuatan user
        })

    def check_password(self, password):
        """Mengecek password yang dimasukkan dengan hash yang tersimpan."""
        return check_password_hash(self.password_hash, password)


class Topic:
    """Model untuk topik diskusi."""
    def __init__(self, title, content, author_id, author_username, created_at=None, updated_at=None, _id=None):
        self.title = title
        self.content = content
        self.author_id = ObjectId(author_id) # Simpan author_id sebagai ObjectId
        self.author_username = author_username
        self.created_at = created_at if created_at else datetime.datetime.utcnow()
        self.updated_at = updated_at if updated_at else datetime.datetime.utcnow()
        self._id = _id if _id else ObjectId()

    def save(self):
        """Menyimpan topik baru atau memperbarui topik yang sudah ada."""
        if self._id and get_db().topics.count_documents({"_id": self._id}) > 0:
            # Update topik yang sudah ada
            get_db().topics.update_one(
                {"_id": self._id},
                {"$set": {
                    "title": self.title,
                    "content": self.content,
                    "updated_at": datetime.datetime.utcnow()
                }}
            )
        else:
            # Masukkan topik baru
            result = get_db().topics.insert_one({
                "title": self.title,
                "content": self.content,
                "author_id": self.author_id,
                "author_username": self.author_username,
                "created_at": self.created_at,
                "updated_at": self.updated_at
            })
            self._id = result.inserted_id
        return self._id

    def update(self):
        """Memperbarui topik yang sudah ada (metode alias untuk save dengan update)."""
        self.save()

    def delete(self):
        """Menghapus topik dan semua postingan yang terkait."""
        get_db().topics.delete_one({"_id": self._id})
        # Penting: Pastikan topic_id di koleksi posts juga disimpan sebagai ObjectId
        get_db().posts.delete_many({"topic_id": self._id})

    @staticmethod
    def get_paginated_topics(page, per_page):
        """Mengambil topik dengan pagination."""
        skip = (page - 1) * per_page
        topics_data = list(get_db().topics.find().sort("created_at", -1).skip(skip).limit(per_page))
        total_topics = get_db().topics.count_documents({})
        
        # Konversi data mentah dari DB ke objek Topic
        topics = [Topic(
            title=t["title"],
            content=t["content"],
            author_id=t["author_id"],
            author_username=t["author_username"],
            created_at=t["created_at"],
            updated_at=t.get("updated_at", t["created_at"]), # Ambil updated_at jika ada
            _id=t["_id"]
        ) for t in topics_data]
        
        return topics, total_topics

    @staticmethod
    def find_by_id(topic_id):
        """Mencari topik berdasarkan ObjectId."""
        try:
            topic_data = get_db().topics.find_one({"_id": ObjectId(topic_id)})
            if topic_data:
                return Topic(
                    title=topic_data["title"],
                    content=topic_data["content"],
                    author_id=topic_data["author_id"],
                    author_username=topic_data["author_username"],
                    created_at=topic_data["created_at"],
                    updated_at=topic_data.get("updated_at", topic_data["created_at"]),
                    _id=topic_data["_id"]
                )
        except Exception:
            return None
        return None
    
    @staticmethod
    def search_topics(query_text, page, per_page):
        """Mencari topik berdasarkan teks menggunakan Atlas Search dengan pagination."""
        skip = (page - 1) * per_page

        # Pipeline agregasi untuk Atlas Search
        # 'topic_text_index' adalah nama indeks Atlas Search yang Anda buat di Atlas
        pipeline = [
            {
                '$search': {
                    'index': 'topic_text_index', 
                    'text': {
                        'query': query_text,
                        'path': ['title', 'content'] # Mencari di bidang title dan content
                    }
                }
            },
            {'$sort': {'created_at': -1}}, # Urutkan berdasarkan tanggal terbaru
            {
                '$facet': {
                    'totalData': [{'$skip': skip}, {'$limit': per_page}],
                    'totalCount': [{'$count': 'count'}]
                }
            }
        ]

        # Jalankan pipeline
        result = list(get_db().topics.aggregate(pipeline))

        # Ekstrak hasil
        # Handle kasus di mana tidak ada hasil atau dokumen kosong dari $facet
        topics_data = result[0]['totalData'] if result and 'totalData' in result[0] else []
        total_results = result[0]['totalCount'][0]['count'] if result and 'totalCount' in result[0] and result[0]['totalCount'] else 0

        # Konversi data mentah dari DB ke objek Topic
        topics = [Topic(
            title=t["title"],
            content=t["content"],
            author_id=t["author_id"],
            author_username=t["author_username"],
            created_at=t["created_at"],
            updated_at=t.get("updated_at", t["created_at"]),
            _id=t["_id"]
        ) for t in topics_data]

        return topics, total_results


class Post:
    """Model untuk postingan (balasan) dalam topik."""
    def __init__(self, topic_id, content, author_id, author_username, created_at=None, updated_at=None, _id=None):
        self.topic_id = ObjectId(topic_id) # Simpan topic_id sebagai ObjectId
        self.content = content
        self.author_id = ObjectId(author_id) # Simpan author_id sebagai ObjectId
        self.author_username = author_username
        self.created_at = created_at if created_at else datetime.datetime.utcnow()
        self.updated_at = updated_at if updated_at else datetime.datetime.utcnow()
        self._id = _id if _id else ObjectId()

    def save(self):
        """Menyimpan postingan baru atau memperbarui postingan yang sudah ada."""
        if self._id and get_db().posts.count_documents({"_id": self._id}) > 0:
            # Update postingan yang sudah ada
            get_db().posts.update_one(
                {"_id": self._id},
                {"$set": {
                    "content": self.content,
                    "updated_at": datetime.datetime.utcnow()
                }}
            )
        else:
            # Masukkan postingan baru
            result = get_db().posts.insert_one({
                "topic_id": self.topic_id,
                "content": self.content,
                "author_id": self.author_id,
                "author_username": self.author_username,
                "created_at": self.created_at,
                "updated_at": self.updated_at
            })
            self._id = result.inserted_id
        return self._id

    def update(self):
        """Memperbarui postingan yang sudah ada (metode alias untuk save dengan update)."""
        self.save()

    def delete(self):
        """Menghapus postingan."""
        get_db().posts.delete_one({"_id": self._id})

    @staticmethod
    def find_by_id(post_id):
        """Mencari postingan berdasarkan ObjectId."""
        try:
            post_data = get_db().posts.find_one({"_id": ObjectId(post_id)})
            if post_data:
                return Post(
                    topic_id=post_data["topic_id"],
                    content=post_data["content"],
                    author_id=post_data["author_id"],
                    author_username=post_data["author_username"],
                    created_at=post_data["created_at"],
                    updated_at=post_data.get("updated_at", post_data["created_at"]),
                    _id=post_data["_id"]
                )
        except Exception:
            return None
        return None

    @staticmethod
    def get_posts_for_topic(topic_id, page, per_page):
        """Mengambil postingan berdasarkan topik dengan pagination."""
        skip = (page - 1) * per_page
        # Pastikan kueri menggunakan ObjectId untuk topic_id
        posts_data = list(get_db().posts.find({"topic_id": ObjectId(topic_id)}).sort("created_at", 1).skip(skip).limit(per_page))
        total_posts = get_db().posts.count_documents({"topic_id": ObjectId(topic_id)})
        
        # Konversi data mentah dari DB ke objek Post
        posts = [Post(
            topic_id=p["topic_id"],
            content=p["content"],
            author_id=p["author_id"],
            author_username=p["author_username"],
            created_at=p["created_at"],
            updated_at=p.get("updated_at", p["created_at"]),
            _id=p["_id"]
        ) for p in posts_data]

        return posts, total_posts
