from flask import Blueprint, render_template, redirect, url_for, abort, flash, request
from bson.objectid import ObjectId
from flask_login import login_required, current_user
from extensions import mongo, mail
from flask_mail import Message
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from flask import send_from_directory

admin_bp = Blueprint('admin', __name__)

# ------------------ UPLOAD SETTINGS ------------------
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------ ADMIN DASHBOARD ------------------
@admin_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        abort(403)

    users_collection = mongo.db.users
    pending_users = list(users_collection.find({'status': 'pending'}))
    approved_users = list(users_collection.find({'status': 'approved'}))

    # For demo, hardcoded news stats
    total_news = 1200
    real_news = 850
    fake_news = 350

    return render_template(
        'dashboard_admin.html',
        pending_users=pending_users,
        approved_users=approved_users,
        total_news=total_news,
        real_news=real_news,
        fake_news=fake_news
    )

# ------------------ APPROVE USER ------------------
@admin_bp.route('/admin/approve/<user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if current_user.role != 'admin':
        abort(403)

    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user:
        mongo.db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'status': 'approved'}})

        user_name = user.get('full_name', 'User')

        msg = Message(
            'Account Approved',
            sender=os.getenv('MAIL_USERNAME'),
            recipients=[user['email']]
        )
        msg.body = f"""
Dear {user_name},

Congratulations! Your account has been approved.
You can now log in and start using all the features.

Welcome aboard!

Regards,
Admin Team
"""
        mail.send(msg)

    flash('User approved successfully.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

# ------------------ REJECT USER ------------------
@admin_bp.route('/admin/reject/<user_id>', methods=['POST'])
@login_required
def reject_user(user_id):
    if current_user.role != 'admin':
        abort(403)

    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user:
        user_name = user.get('full_name', 'User')

        msg = Message(
            'Account Registration Update',
            sender=os.getenv('MAIL_USERNAME'),
            recipients=[user['email']]
        )
        msg.body = f"""
Dear {user_name},

Thank you for registering with us.
After careful review, we regret to inform you that your account request has been declined at this time.

If you wish to reapply in the future or have questions, feel free to contact us.

Regards,
Admin Team
"""
        mail.send(msg)

        mongo.db.users.delete_one({'_id': ObjectId(user_id)})

    flash('User rejected and deleted successfully.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

# ------------------ UNAPPROVE USER ------------------
# ------------------ UNAPPROVE USER ------------------
@admin_bp.route('/admin/unapprove/<user_id>', methods=['POST'])
@login_required
def unapprove_user(user_id):
    if current_user.role != 'admin':
        abort(403)

    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

    # Get reason from form
    reason = request.form.get('reason', 'No reason provided.')

    # Update user status to pending (unapproved)
    mongo.db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'status': 'pending'}})

    user_name = user.get('full_name', 'User')

    # Send email with reason
    msg = Message(
        'Account Status Update',
        sender=os.getenv('MAIL_USERNAME'),
        recipients=[user['email']]
    )
    msg.body = f"""
Dear {user_name},

This is to inform you that your account status has been changed to unapproved (pending review).

Reason: {reason}

If you have any questions, please contact the admin team.

Regards,
Admin Team
"""
    mail.send(msg)

    flash('User has been unapproved successfully.', 'success')
    return redirect(url_for('admin.user_profile', user_id=user_id))

# ------------------ VIEW USER PROFILE ------------------
@admin_bp.route('/admin/user/<user_id>')
@login_required
def user_profile(user_id):
    if current_user.role != 'admin':
        abort(403)

    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return "User not found", 404

    return render_template('user_profile.html', user=user)

# ------------------ EDIT ADMIN PROFILE ------------------
@admin_bp.route('/admin/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if current_user.role != 'admin':
        abort(403)

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')

        update_data = {
            'full_name': full_name,
            'email': email,
            'phone_number': phone_number
        }

        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                update_data['profile_image'] = filename

        mongo.db.users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$set': update_data}
        )

        flash('Profile updated successfully.', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    user = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
    return render_template('edit_profile_admin.html', user=user)


# View notification form
@admin_bp.route('/admin/notifications', methods=['GET', 'POST'])
@login_required
def admin_notifications():
    if current_user.role != 'admin':
        abort(403)

    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        file = request.files.get('file')
        file_name = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            file_name = filename

        # Insert the notification
        mongo.db.notifications.insert_one({
            'title': title,
            'message': message,
            'file': file_name,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        # Fetch all user emails
        users = mongo.db.users.find({}, {"email": 1})
        recipient_emails = [user['email'] for user in users if 'email' in user]

        # Send emails
        subject = f"📢 New Notification: {title}"
        body = f"Hello,\n\nA new notification has been posted by the Admin:\n\nTitle: {title}\nMessage: {message}"

        msg = Message(subject, recipients=recipient_emails)
        msg.body = body
        mail.send(msg)

        flash("Notification posted and email sent to all users.", "success")
        return redirect(url_for('admin.admin_notifications'))

    notifications = list(mongo.db.notifications.find().sort('created_at', -1))
    return render_template('notifications_admin.html', notifications=notifications)

@admin_bp.route('/download/<filename>')
@login_required
def download_file_admin(filename):
    from werkzeug.utils import secure_filename
    safe_filename = secure_filename(filename)
    return send_from_directory(UPLOAD_FOLDER, safe_filename, as_attachment=True)
