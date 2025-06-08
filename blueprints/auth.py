from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from werkzeug.security import generate_password_hash
from forms.forms import RegistrationForm, LoginForm # Import forms

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Route untuk pendaftaran user baru."""
    if current_user.is_authenticated:
        return redirect(url_for('forum.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        hashed_password = generate_password_hash(password)
        new_user = User(username, email, hashed_password)
        new_user.save()
        flash('Pendaftaran berhasil! Silakan masuk.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Route untuk login user."""
    if current_user.is_authenticated:
        return redirect(url_for('forum.index'))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.find_by_username(username)

        if user and user.check_password(password):
            login_user(user)
            flash('Berhasil masuk!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('forum.index'))
        else:
            flash('Nama pengguna atau kata sandi tidak valid.', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Route untuk logout user."""
    logout_user()
    flash('Anda telah berhasil keluar.', 'info')
    return redirect(url_for('auth.login'))
