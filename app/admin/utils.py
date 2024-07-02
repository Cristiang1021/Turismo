import os
from flask import current_app
from cloudinary.uploader import upload

def upload_to_cloudinary(file):
    if file and allowed_file(file.filename):
        try:
            result = upload(file, folder=current_app.config['CLOUDINARY_FOLDER'])
            return result['secure_url']
        except Exception as e:
            print(f"Error uploading to Cloudinary: {e}")
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']