import os
from flask import render_template, request, redirect, url_for, flash, send_from_directory, current_app
from werkzeug.utils import secure_filename
from . import storage
from flask_login import login_required

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'docx', 'xlsx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@storage.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            flash('File uploaded successfully!', 'success')
            return redirect(url_for('storage.index'))
        else:
            flash('Invalid file type.', 'danger')
    files = os.listdir(UPLOAD_FOLDER)
    return render_template('storage/index.html', files=files)

@storage.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@storage.route('/delete/<filename>', methods=['POST'])
@login_required
def delete_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash('File deleted.', 'success')
    else:
        flash('File not found.', 'danger')
    return redirect(url_for('storage.index'))
