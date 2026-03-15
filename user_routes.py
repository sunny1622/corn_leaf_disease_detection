from flask import Blueprint, render_template, flash, redirect, url_for, request, send_from_directory
from bson.objectid import ObjectId
from datetime import datetime
from extensions import mongo
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os

# For prediction
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np

user_bp = Blueprint('user', __name__)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Load the model once at the beginning
model = load_model('corn_model.h5')

# Labels must match model training order
labels = ['Blight', 'Common Rust', 'Cercospora', 'Healthy']

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------ DASHBOARD ------------------
@user_bp.route('/dashboard')
@login_required
def user_dashboard():
    user = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('auth.login'))

    if isinstance(user.get('created_at'), str):
        try:
            user['created_at'] = datetime.strptime(user['created_at'], '%Y-%m-%d %H:%M:%S')
        except:
            user['created_at'] = None

    return render_template('dashboard_user.html', user=user)

# ------------------ EDIT PROFILE ------------------
@user_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('user.user_dashboard'))

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

        flash("Profile updated successfully.", "success")
        return redirect(url_for('user.user_dashboard'))

    return render_template('edit_profile_user.html', user=user)

# ------------------ VIEW NOTIFICATIONS ------------------
@user_bp.route('/notifications')
@login_required
def view_notifications():
    notifications = list(mongo.db.notifications.find().sort('created_at', -1))
    return render_template('notifications_user.html', notifications=notifications)

# ------------------ DOWNLOAD FILE ------------------
@user_bp.route('/download/<filename>')
@login_required
def download_file(filename):
    safe_filename = secure_filename(filename)
    return send_from_directory(UPLOAD_FOLDER, safe_filename, as_attachment=True)

# ------------------ PREDICT DISEASE ------------------
@user_bp.route('/predict_disease', methods=['POST'])
@login_required
def predict_disease():
    if 'image' not in request.files:
        flash("No file part.", "danger")
        return redirect(url_for('user.user_dashboard'))

    file = request.files['image']
    if file.filename == '':
        flash("No selected file.", "danger")
        return redirect(url_for('user.user_dashboard'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            # ✅ Load and preprocess the image
            img = image.load_img(filepath, target_size=(224, 224))
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = img_array / 255.0  # Normalize

            # ✅ Make prediction
            prediction = model.predict(img_array)
            print("🔍 Prediction Vector:", prediction)

            predicted_index = np.argmax(prediction[0])
            predicted_label = labels[predicted_index]
            confidence = float(prediction[0][predicted_index])

            flash(f"Prediction: {predicted_label} (Confidence: {confidence:.2f})", "info")

        except Exception as e:
            flash(f"Prediction error: {str(e)}", "danger")
            return redirect(url_for('user.user_dashboard'))

        user = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
        return render_template('dashboard_user.html', user=user, prediction=predicted_label, confidence=confidence)

    else:
        flash("Invalid file type.", "danger")
        return redirect(url_for('user.user_dashboard'))
