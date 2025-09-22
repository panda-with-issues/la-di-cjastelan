import os
from flask import Flask, render_template, request, g, redirect, url_for
from werkzeug.exceptions import HTTPException
from app.auth import login_required
from . import database, auth, corr, mercati, ocr

def create_app():
  # create and configure the app
  app = Flask(__name__, instance_relative_config=True)
  
  app.config.from_pyfile('config.py', silent=True)

  # ensure the instance folder exists
  try:
    os.makedirs(app.instance_path)
  except OSError:
    pass

  db = database.init_db(app)

  app.register_blueprint(auth.bp)
  app.register_blueprint(corr.bp)
  app.register_blueprint(mercati.bp)
  app.register_blueprint(ocr.bp)
  
  @app.route('/')
  @login_required
  def index():
    if not g.user.is_admin:
      return redirect(url_for('corr.inserisci'))
    return render_template('index.html')

  @app.errorhandler(HTTPException)
  def error_handler(e):
    return render_template(
      'error.html',
      error_code = e.code,
      error_name = e.name,
      error_description = e.description,
      url=request.referrer), e.code
  
  return app