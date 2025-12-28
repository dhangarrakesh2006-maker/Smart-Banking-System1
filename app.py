from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
from decimal import Decimal
from werkzeug.utils import secure_filename
from flask_wtf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate

# App setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', 'dev-secret')
# prefer to auto-reload templates during development
app.config['TEMPLATES_AUTO_RELOAD'] = True
# Configure upload folder. In serverless/read-only environments (e.g. Vercel)
# we must not attempt writes at import time. Prefer an env var, then
# project static folder, and finally fall back to a writable temp folder.
preferred_upload = os.environ.get('UPLOAD_FOLDER') or os.path.join('static', 'uploads')
upload_folder = preferred_upload
try:
  os.makedirs(preferred_upload, exist_ok=True)
except OSError:
  # likely read-only filesystem; try /tmp which is writable on many hosts
  try:
    tmp_folder = os.path.join('/tmp', 'uploads')
    os.makedirs(tmp_folder, exist_ok=True)
    upload_folder = tmp_folder
    print('Using /tmp uploads folder because preferred path is not writable')
  except Exception:
    # leave upload_folder as preferred (we can't create it) — handle at runtime
    print('Could not create upload folders; continuing without creating directories')

app.config['UPLOAD_FOLDER'] = upload_folder
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

# Ensure instance folder exists if possible, but ignore failures on read-only FS
try:
  os.makedirs('instance', exist_ok=True)
except OSError:
  pass

# Try to wire up a database if models.py is present
use_db = False
try:
  from models import db, User, ATM, Transaction
  use_db = True
  # Use absolute path and forward slashes so SQLite opens correctly on Windows
  db_path = os.path.abspath(os.path.join('instance', 'smartbank.sqlite'))
  db_uri = 'sqlite:///' + db_path.replace('\\', '/')
  # Allow overriding via environment variable for production DBs (MySQL/Postgres)
  env_db = os.environ.get('SQLALCHEMY_DATABASE_URI')
  if env_db:
    app.config['SQLALCHEMY_DATABASE_URI'] = env_db
  else:
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', db_uri)
  app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
  db.init_app(app)
  # security and auth helpers
  csrf = CSRFProtect()
  csrf.init_app(app)
  login_manager = LoginManager()
  login_manager.init_app(app)
  migrate = Migrate()
  migrate.init_app(app, db)
  
  @login_manager.user_loader
  def load_user(user_id):
    try:
      return User.query.get(int(user_id))
    except Exception:
      return None
except Exception:
  use_db = False


@app.route('/')
def home():
  # Check if splash screen was already shown
  splash_done = request.args.get('splash')
  if not splash_done:
    return render_template('splash.html')
  
  users = []
  total_balance = '0.00'
  if use_db:
    try:
      users = User.query.all()
      total = sum([float(u.balance) if u.balance is not None else 0 for u in users])
      total_balance = f"{total:,.2f}"
    except Exception:
      users = []
      total_balance = '0.00'
  return render_template('project.html', users=users, total_balance=total_balance)


@app.route('/project')
def project():
  return render_template('project.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
  if request.method == 'POST':
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    balance_field = request.form.get('balance', '').strip()

    if not (name and email and password):
      flash('Name, email and password are required.', 'error')
      return redirect(url_for('register'))

    if not use_db:
      flash('Registration unavailable: database not configured on server.', 'error')
      return redirect(url_for('register'))

    # check existing
    existing = User.query.filter_by(email=email).first()
    if existing:
      flash('Email already registered.', 'error')
      return redirect(url_for('register'))

    u = User(name=name, email=email)
    # Force canonical name for the specific email if needed
    if email and email.lower() == 'dhangarrakesh2006@gmail.com':
      u.name = 'Rakesh dhangar'
    try:
      u.set_password(password)
    except Exception:
      u.password_hash = password

    try:
      u.balance = Decimal(balance_field) if balance_field else Decimal('0.00')
    except Exception:
      u.balance = Decimal('0.00')

    db.session.add(u)
    db.session.commit()

    # redirect to upload face page
    flash('Account created. Please upload face image.', 'success')
    return redirect(url_for('upload_face', user_id=u.id))

  return render_template('register.html')



@app.route('/login', methods=['POST'])
def login():
  try:
    if not use_db:
      flash('Login unavailable: database not configured.', 'error')
      return redirect(url_for('home'))
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    if not email or not password:
      flash('Please provide login id and password.', 'error')
      return redirect(url_for('home'))
    # attempt case-insensitive lookup so users can enter different casing
    try:
      user = User.query.filter(User.email.ilike(email)).first()
    except Exception:
      user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
      flash('Invalid credentials.', 'error')
      return redirect(url_for('home'))

    # login success using Flask-Login
    login_user(user)
    # ensure canonical name for specific account
    try:
      if user.email and user.email.lower() == 'dhangarrakesh2006@gmail.com' and user.name != 'Rakesh dhangar':
        user.name = 'Rakesh dhangar'
        db.session.commit()
    except Exception:
      pass
    flash(f'Welcome back, {user.name}!', 'success')
    return redirect(url_for('account_index'))
  except Exception as e:
    print('Login error:', e)
    flash('Server error during login. Please try again.', 'error')
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
  if not use_db:
    flash('Dashboard unavailable: database not configured.', 'error')
    return redirect(url_for('home'))
  # use current_user from Flask-Login
  try:
    user = current_user
    return render_template('dashboard.html', user=user)
  except Exception:
    flash('User not found.', 'error')
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
  try:
    logout_user()
  except Exception:
    pass
  flash('You have been logged out.', 'info')
  return redirect(url_for('home'))


@app.route('/api/current-user')
@login_required
def api_current_user():
  """Return the currently logged-in user's information as JSON."""
  if not use_db:
    return {'error': 'database unavailable'}, 503
  
  try:
    user = current_user
    if not user:
      return {'error': 'Not authenticated'}, 401
    
    return {
      'user': {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'balance': str(user.balance) if user.balance else '0.00'
      }
    }, 200
  except Exception as e:
    print('API current-user error:', e)
    return {'error': 'Server error'}, 500


# face upload
ALLOWED_EXT = {'png', 'jpg', 'jpeg'}
def allowed_filename(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


@app.route('/upload-face/<int:user_id>', methods=['GET', 'POST'])
def upload_face(user_id):
  if not use_db:
    flash('Database not configured', 'error')
    return redirect(url_for('home'))

  user = User.query.get_or_404(user_id)
  if request.method == 'POST':
    f = request.files.get('face')
    if not f or f.filename == '':
      flash('No file selected', 'error')
      return redirect(url_for('upload_face', user_id=user_id))
    if not allowed_filename(f.filename):
      flash('Invalid file type (png/jpg/jpeg only)', 'error')
      return redirect(url_for('upload_face', user_id=user_id))

    fname = secure_filename(f.filename)
    ext = fname.rsplit('.', 1)[1].lower()
    save_name = f'user_{user.id}.{ext}'
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], save_name)
    f.save(save_path)

    user.face_filename = save_name
    db.session.commit()
    flash('Face uploaded successfully', 'success')
    return redirect(url_for('home'))

  return render_template('upload_face.html', user=user)


@app.route('/api/atms')
def api_atms():
  """Return ATMs matching a query.
  Supports query params:
    - pincode: exact pincode match
    - q: free-text search (name, address, pincode) - useful for district/city names
  """
  if not use_db:
    return {'error': 'database unavailable'}, 503

  pincode = request.args.get('pincode', '').strip()
  q = request.args.get('q', '').strip()

  if not pincode and not q:
    return {'error': 'pincode or q parameter required'}, 400

  # If pincode provided, prefer exact pincode match
  if pincode:
    atms = ATM.query.filter_by(pincode=pincode).all()
    return {'query': pincode, 'count': len(atms), 'atms': [a.to_dict() for a in atms]}

  # else perform a case-insensitive substring search on name/address/pincode
  try:
    pattern = f"%{q}%"
    atms = ATM.query.filter(
      (ATM.name.ilike(pattern)) | (ATM.address.ilike(pattern)) | (ATM.pincode.ilike(pattern))
    ).all()
  except Exception:
    # fallback to simple filter_by on pincode
    atms = ATM.query.filter_by(pincode=q).all()

  return {'query': q, 'count': len(atms), 'atms': [a.to_dict() for a in atms]}


@app.route('/account/')
def account_index():
  """Serve the Account dashboard index HTML (static file)."""
  # Serve the Account/index.html file from the Account folder
  return send_from_directory(os.path.join(app.root_path, 'Account'), 'index.html')


@app.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
  if not use_db:
    flash('Transfers unavailable: database not configured.', 'error')
    return redirect(url_for('home'))
  if request.method == 'POST':
    to_email = request.form.get('to_email', '').strip()
    amount_str = request.form.get('amount', '').strip()
    description = request.form.get('description', '').strip()
    if not to_email or not amount_str:
      flash('Recipient and amount are required.', 'error')
      return redirect(url_for('transfer'))
    try:
      amt = Decimal(amount_str)
      if amt <= 0:
        raise Exception('Invalid amount')
    except Exception:
      flash('Enter a valid amount.', 'error')
      return redirect(url_for('transfer'))

    recipient = User.query.filter(User.email.ilike(to_email)).first()
    if not recipient:
      flash('Recipient not found.', 'error')
      return redirect(url_for('transfer'))

    sender = current_user
    try:
      if sender.balance is None:
        sender.balance = Decimal('0.00')
      if recipient.balance is None:
        recipient.balance = Decimal('0.00')
      if Decimal(sender.balance) < amt:
        flash('Insufficient balance.', 'error')
        return redirect(url_for('transfer'))

      sender.balance = Decimal(sender.balance) - amt
      recipient.balance = Decimal(recipient.balance) + amt

      tx = Transaction(from_user_id=sender.id, to_user_id=recipient.id, amount=amt, description=description)
      db.session.add(tx)
      db.session.commit()
      flash('Transfer completed successfully.', 'success')
      return redirect(url_for('dashboard'))
    except Exception as e:
      db.session.rollback()
      print('Transfer error:', e)
      flash('Server error during transfer.', 'error')
      return redirect(url_for('transfer'))

  return render_template('transfer.html', user=current_user)


@app.route('/account/<path:filename>')
def account_static(filename):
  """Serve static assets for the Account section (CSS/JS/images)."""
  return send_from_directory(os.path.join(app.root_path, 'Account'), filename)


@app.route('/favicon.png')
def favicon():
  """Serve the project favicon from the main.html folder so templates can reference /favicon.png."""
  try:
    return send_from_directory(os.path.join(app.root_path, 'main.html'), 'favicon.png')
  except Exception:
    # fallback 404
    return ('', 404)


if use_db:
  @app.cli.command('seed-atms')
  def seed_atms():
    """Seed sample ATMs for Shirpur and Shindkhed pincodes."""
    with app.app_context():
      # sample list
      samples = [
        {'name': 'Shirpur Bank ATM - Main Street', 'address': 'Near Market, Shirpur', 'pincode': '425405', 'latitude': 20.756000, 'longitude': 74.591000},
        {'name': "Shindkhed ATM - Central", 'address': 'Opposite Bus Stand, Shindkhed', 'pincode': '425403', 'latitude': 20.760500, 'longitude': 74.598200},
      ]
      created = 0
      for s in samples:
        exists = ATM.query.filter_by(name=s['name']).first()
        if not exists:
          a = ATM(name=s['name'], address=s['address'], pincode=s['pincode'], latitude=s['latitude'], longitude=s['longitude'])
          db.session.add(a)
          created += 1
      db.session.commit()
      print(f'Seeded {created} ATM(s)')


if use_db:
  @app.cli.command('init-db')
  def init_db():
    """Create database tables."""
    with app.app_context():
      db.create_all()
      print('Initialized the database.')


if __name__ == '__main__':
  # When running directly, enable debug and make static/template changes appear without restarting where possible
  app.run(host='127.0.0.1', port=5000, debug=True)


@app.after_request
def add_header_no_cache(response):
  """During development, prevent caching of static files so changes show immediately in browser."""
  try:
    if app.debug and request.path.startswith('/static/'):
      response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
  except Exception:
    pass
  return response