import os
from flask import Flask, render_template, request
from app.auth import login_required, admin_required
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
  @admin_required
  def index():
    return render_template('index.html')

  @app.errorhandler(403)
  def forbidden(e):
    return render_template('error.html', url=request.referrer), 403
  
  return app