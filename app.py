from flask import Flask, render_template, g, redirect, url_for, request, flash, abort, jsonify
import sqlite3
import os
import datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.instance_path, 'projects.db')
app.config['SECRET_KEY'] = 'your_secret_key'  
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        return User(user["id"], user["username"])
    return None


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        try:
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()
            print("Database initialized successfully.")
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
            db.rollback()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()

@app.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow}

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            login_user(User(user["id"], user["username"]))
            return redirect(url_for('projects'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Project Management Routes
@app.route('/projects')
def projects():
    db = get_db()
    if current_user.is_authenticated:
        projects = db.execute('SELECT * FROM projects').fetchall()
    else:
        projects = db.execute('SELECT * FROM projects WHERE is_public = 1').fetchall()
    return render_template('projects.html', projects=projects)

@app.route('/projects/add', methods=['GET', 'POST'])
@login_required
def add_project():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        url = request.form['url']
        thumbnail = request.form.get('thumbnail', '')  # Optional thumbnail

        db = get_db()
        db.execute('INSERT INTO projects (title, description, url, thumbnail) VALUES (?, ?, ?, ?)', 
                   (title, description, url, thumbnail))
        db.commit()
        return redirect(url_for('projects'))
    
    return render_template('add_project.html')


@app.route('/projects/edit/<int:project_id>', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    db = get_db()
    project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if project is None:
        abort(404)

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        url = request.form['url']
        thumbnail = request.form.get('thumbnail', project['thumbnail'])  # Keep old thumbnail if not changed

        db.execute('UPDATE projects SET title = ?, description = ?, url = ?, thumbnail = ? WHERE id = ?', 
                   (title, description, url, thumbnail, project_id))
        db.commit()
        return redirect(url_for('projects'))

    return render_template('edit_project.html', project=project)


@app.route('/projects/toggle/<int:project_id>')
@login_required
def toggle_project(project_id):
    db = get_db()
    project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if project is None:
        abort(404)
    new_visibility = 1 if project['is_public'] == 0 else 0
    db.execute('UPDATE projects SET is_public = ? WHERE id = ?', (new_visibility, project_id))
    db.commit()
    return redirect(url_for('projects'))

@app.route('/projects/delete/<int:project_id>')
@login_required
def delete_project(project_id):
    db = get_db()
    project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if project is None:
        abort(404)
    db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    db.commit()
    return redirect(url_for('projects'))

# Basic Routes (to be expanded)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
    
@app.route('/upload_thumbnail', methods=['POST'])
@login_required
def upload_thumbnail():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        return jsonify({"filename": filename}), 200

    return jsonify({"error": "Invalid file type"}), 400

@app.route('/delete_thumbnail/<int:project_id>', methods=['POST'])
@login_required
def delete_thumbnail(project_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()

    if not project or not project["thumbnail"]:
        return jsonify({"error": "No thumbnail to delete"}), 400

    # Get the file path
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], project["thumbnail"])
    
    try:
        # Delete the file from the server
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Update the database to remove the thumbnail reference
        db.execute("UPDATE projects SET thumbnail = NULL WHERE id = ?", (project_id,))
        db.commit()
        
        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    os.makedirs(app.instance_path, exist_ok=True)
    print(f"instance path: {app.instance_path}")
    app.run(debug=True)