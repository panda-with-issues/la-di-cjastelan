import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, abort
)
from app.database import db, Utenti

bp = Blueprint('auth', __name__, url_prefix='/auth')

def login_required(view):
  @functools.wraps(view)
  def wrapped_view(**kwargs):
    if g.user is None:
      return redirect(url_for('auth.login'))
    return view(**kwargs)

  return wrapped_view

def admin_required(view):
  @functools.wraps(view)
  def wrapped_view(**kwargs):
    if not g.user.is_admin:
      abort(403)
    return view(**kwargs)
  
  return wrapped_view

@bp.before_app_request
def load_logged_user():
  username = session.get('username')

  if username is None:
    g.user = None
  else:
    g.user = db.session.execute(
      db.select(Utenti).where(Utenti.username==username)
    ).scalar_one_or_none()

@bp.route('/login', methods=('GET', 'POST'))
def login():
  error = None
  if request.method == 'POST':
    username = request.form['username'].strip()
    password = request.form['password']
    
    user = db.session.execute(
      db.select(Utenti).where(Utenti.username == username)
    ).scalar_one_or_none()

    if user is None:
      error = "L'utente non esiste"
    elif password != user.password:
      error = 'Password sbagliata'

    if error is None:
      session.clear()
      session['username'] = user.username
      if user.is_admin:
        return redirect(url_for('index'))
      return redirect(url_for('corr.inserisci'))
    
    flash(error)

  return render_template('login.html', error=error)

@bp.route('/logout')
def logout():
  session.clear()
  return redirect(url_for('auth.login'))