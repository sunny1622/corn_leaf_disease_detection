from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from extensions import mongo, login_manager, mail
from models.user_model import User
from flask_mail import Message
import random
import logging
import os

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None

# ------------------ REGISTER ------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone_number = request.form.get('phone_number')

        existing_user = mongo.db.users.find_one({"email": email})
        if existing_user:
            flash("Email already registered.", "danger")
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(password)
        new_user = {
            "full_name": full_name,
            "email": email,
            "password": hashed_password,
            "phone_number": phone_number,
            "role": "user",
            "status": "pending",
            "profile_image": "",
        }
        mongo.db.users.insert_one(new_user)

        # Notify user
        try:
            msg_user = Message(
                "Registration Received - Awaiting Approval",
                sender=os.getenv('MAIL_USERNAME'),
                recipients=[email],
                body=f"Hi {full_name},\n\nThank you for registering. Your account is pending admin approval.\n\n- Team"
            )
            mail.send(msg_user)
        except Exception as e:
            pass  # silently ignore if needed; or log if production

        flash("Registration submitted! Awaiting admin approval.", "success")
        return redirect(url_for('auth.login'))

    return render_template('register.html')


# ------------------ LOGIN ------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user_data = mongo.db.users.find_one({'email': email})
        if not user_data or not check_password_hash(user_data['password'], password):
            flash('Invalid credentials.', 'danger')
            return redirect(url_for('auth.login'))

        if user_data.get('status') != 'approved':
            flash('Your account is not approved yet.', 'warning')
            return redirect(url_for('auth.login'))

        user = User(user_data)
        login_user(user)
        flash('Logged in successfully!', 'success')
        return redirect(url_for('admin.admin_dashboard' if user_data['role'] == 'admin' else 'user.user_dashboard'))

    return render_template('login.html')


# ------------------ LOGOUT ------------------
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('main.index'))


# ------------------ FORGOT PASSWORD ------------------
@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = mongo.db.users.find_one({'email': email})
        if user:
            otp = random.randint(100000, 999999)
            session['reset_otp'] = otp
            session['reset_email'] = email

            msg = Message('Password Reset OTP',
                          sender='your_email@gmail.com',
                          recipients=[email])
            msg.body = f'Your OTP for password reset is: {otp}'
            mail.send(msg)

            flash('OTP sent to your email.')
            return redirect(url_for('auth.reset_password'))
        else:
            flash('Email not found.')
    return render_template('forgot_password.html')

# ------------------ RESET PASSWORD ------------------
@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        otp_entered = request.form['otp']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('auth.reset_password'))

        if int(otp_entered) == int(session.get('reset_otp', 0)):
            email = session.get('reset_email')
            hashed_password = generate_password_hash(new_password)
            mongo.db.users.update_one({'email': email}, {'$set': {'password': hashed_password}})
            session.pop('reset_otp', None)
            session.pop('reset_email', None)
            flash('Password reset successful. Please login.')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid OTP.')

    return render_template('reset_password.html')


# ------------------ CHANGE PASSWORD ------------------
@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        user = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})

        if not check_password_hash(user['password'], current_password):
            flash('Current password is incorrect.')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('New passwords do not match.')
            return redirect(url_for('auth.change_password'))

        hashed_password = generate_password_hash(new_password)
        mongo.db.users.update_one({'_id': ObjectId(current_user.id)}, {'$set': {'password': hashed_password}})

        flash('Password changed successfully!')
        return redirect(url_for('user.user_dashboard'))

    return render_template('change_password.html')
