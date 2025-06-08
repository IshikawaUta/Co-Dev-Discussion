from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import Topic, Post, User
from datetime import datetime
from math import ceil
from forms.forms import TopicForm, PostForm
from functools import wraps
from database import get_db

forum_bp = Blueprint('forum', __name__)

def admin_required(f):
    """
    Decorator kustom untuk memastikan user adalah admin.
    Digunakan untuk melindungi route yang hanya bisa diakses oleh admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
            return redirect(url_for('forum.index')) # Atau halaman 403 Forbidden
        return f(*args, **kwargs)
    return decorated_function

@forum_bp.route('/')
def index():
    """Route utama untuk menampilkan daftar topik dengan pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = 10 # Jumlah topik per halaman
    topics, total_topics = Topic.get_paginated_topics(page, per_page)
    
    total_pages = ceil(total_topics / per_page) if total_topics > 0 else 1
    
    return render_template('index.html', 
                           topics=topics, 
                           page=page, 
                           total_pages=total_pages, 
                           per_page=per_page)

@forum_bp.route('/new_topic', methods=['GET', 'POST'])
@login_required
def new_topic():
    """Route untuk membuat topik baru."""
    form = TopicForm()
    if form.validate_on_submit():
        new_topic = Topic(
            title=form.title.data,
            content=form.content.data,
            author_id=current_user.get_id(), # current_user.get_id() mengembalikan string
            author_username=current_user.username,
            created_at=datetime.utcnow()
        )
        new_topic.save()
        flash('Topik baru berhasil dibuat!', 'success')
        return redirect(url_for('forum.index'))
    return render_template('new_topic.html', form=form)

@forum_bp.route('/topic/<topic_id>', methods=['GET', 'POST'])
def topic_detail(topic_id):
    """Route untuk menampilkan detail topik dan memungkinkan balasan."""
    topic = Topic.find_by_id(topic_id)
    if not topic:
        flash('Topik tidak ditemukan.', 'danger')
        return redirect(url_for('forum.index'))

    # Pagination untuk postingan/balasan
    page = request.args.get('page', 1, type=int)
    per_page = 5 # Jumlah postingan per halaman
    # Pastikan topic._id dikonversi ke string saat diteruskan ke get_posts_for_topic
    posts, total_posts = Post.get_posts_for_topic(str(topic._id), page, per_page) 
    total_pages = ceil(total_posts / per_page) if total_posts > 0 else 1

    form = PostForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Anda harus login untuk memposting balasan.', 'warning')
            return redirect(url_for('auth.login'))

        new_post = Post(
            topic_id=str(topic._id), # Pastikan topic_id adalah string untuk constructor Post
            content=form.content.data,
            author_id=current_user.get_id(),
            author_username=current_user.username,
            created_at=datetime.utcnow()
        )
        new_post.save()
        flash('Balasan Anda telah diposting!', 'success')
        # Redirect ke halaman terakhir postingan agar post baru terlihat
        last_page = ceil((total_posts + 1) / per_page) if (total_posts + 1) > 0 else 1
        return redirect(url_for('forum.topic_detail', topic_id=topic_id, page=last_page))

    return render_template('topic_detail.html', 
                           topic=topic, 
                           posts=posts, 
                           page=page, 
                           total_pages=total_pages,
                           form=form)

@forum_bp.route('/topic/<topic_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_topic(topic_id):
    """Route untuk mengedit topik."""
    topic = Topic.find_by_id(topic_id)
    if not topic:
        flash('Topik tidak ditemukan.', 'danger')
        return redirect(url_for('forum.index'))

    # Hanya penulis topik atau admin yang bisa mengedit
    if not (current_user.get_id() == str(topic.author_id) or current_user.is_admin()):
        flash('Anda tidak memiliki izin untuk mengedit topik ini.', 'danger')
        return redirect(url_for('forum.topic_detail', topic_id=topic_id))

    form = TopicForm(obj=topic) # Isi form dengan data topik yang sudah ada
    if form.validate_on_submit():
        topic.title = form.title.data
        topic.content = form.content.data
        topic.update() # Memanggil metode update di model
        flash('Topik berhasil diperbarui!', 'success')
        return redirect(url_for('forum.topic_detail', topic_id=topic_id))
    
    return render_template('edit_topic.html', topic=topic, form=form)

@forum_bp.route('/topic/<topic_id>/delete', methods=['POST'])
@login_required
def delete_topic(topic_id):
    """Route untuk menghapus topik."""
    topic = Topic.find_by_id(topic_id)
    if not topic:
        flash('Topik tidak ditemukan.', 'danger')
        return redirect(url_for('forum.index'))

    # Hanya penulis topik atau admin yang bisa menghapus
    if not (current_user.get_id() == str(topic.author_id) or current_user.is_admin()):
        flash('Anda tidak memiliki izin untuk menghapus topik ini.', 'danger')
        return redirect(url_for('forum.topic_detail', topic_id=topic_id))

    topic.delete() # Memanggil metode delete di model
    flash('Topik berhasil dihapus!', 'success')
    return redirect(url_for('forum.index'))

@forum_bp.route('/post/<post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """Route untuk mengedit postingan."""
    post = Post.find_by_id(post_id)
    if not post:
        flash('Postingan tidak ditemukan.', 'danger')
        # Redirect ke halaman utama atau halaman sebelumnya jika post tidak ditemukan
        return redirect(url_for('forum.index')) 

    # Hanya penulis postingan atau admin yang bisa mengedit
    if not (current_user.get_id() == str(post.author_id) or current_user.is_admin()):
        flash('Anda tidak memiliki izin untuk mengedit postingan ini.', 'danger')
        return redirect(url_for('forum.topic_detail', topic_id=str(post.topic_id)))

    form = PostForm(obj=post) # Isi form dengan data post yang sudah ada
    if form.validate_on_submit():
        post.content = form.content.data
        post.update() # Memanggil metode update di model
        flash('Postingan berhasil diperbarui!', 'success')
        return redirect(url_for('forum.topic_detail', topic_id=str(post.topic_id)))
    
    return render_template('edit_post.html', post=post, form=form)

@forum_bp.route('/post/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    """Route untuk menghapus postingan."""
    post = Post.find_by_id(post_id)
    if not post:
        flash('Postingan tidak ditemukan.', 'danger')
        return redirect(url_for('forum.index'))

    # Hanya penulis postingan atau admin yang bisa menghapus
    if not (current_user.get_id() == str(post.author_id) or current_user.is_admin()):
        flash('Anda tidak memiliki izin untuk menghapus postingan ini.', 'danger')
        return redirect(url_for('forum.topic_detail', topic_id=str(post.topic_id)))

    topic_id_redirect = str(post.topic_id) # Simpan topic_id sebelum dihapus dan pastikan string
    post.delete() # Memanggil metode delete di model
    flash('Postingan berhasil dihapus!', 'success')
    return redirect(url_for('forum.topic_detail', topic_id=topic_id_redirect))

@forum_bp.route('/user/<username>')
def user_profile(username):
    """Route untuk menampilkan profil user dan topik yang dibuat."""
    user = User.find_by_username(username)
    if not user:
        flash('User tidak ditemukan.', 'danger')
        return redirect(url_for('forum.index'))
    
    # Ambil topik yang dibuat oleh user ini
    # Pastikan author_id adalah ObjectId untuk query
    user_topics_data = list(get_db().topics.find({"author_id": user._id}).sort("created_at", -1))
    
    # Konversi data mentah ke objek Topic
    user_topics = [Topic(
        title=t["title"],
        content=t["content"],
        author_id=t["author_id"],
        author_username=t["author_username"],
        created_at=t["created_at"],
        updated_at=t.get("updated_at", t["created_at"]),
        _id=t["_id"]
    ) for t in user_topics_data]

    return render_template('user_profile.html', user=user, user_topics=user_topics)

@forum_bp.route('/search')
def search():
    """Route untuk melakukan pencarian topik menggunakan Atlas Search."""
    query = request.args.get('q', '', type=str).strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    topics = []
    total_results = 0
    total_pages = 0

    if query:
        topics, total_results = Topic.search_topics(query, page, per_page)
        total_pages = ceil(total_results / per_page) if total_results > 0 else 1

    return render_template('search_results.html', 
                           query=query, 
                           topics=topics, 
                           page=page, 
                           total_pages=total_pages,
                           total_results=total_results)
