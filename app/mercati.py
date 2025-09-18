from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for
)
from app.database import db, Mercati
from app.auth import login_required, admin_required
from sqlalchemy import exc

bp = Blueprint('mercati', __name__, url_prefix='/mercati')

@bp.route('/visualizza', methods=('GET', 'POST'))
@login_required
@admin_required
def visualizza():
  # va castato a list perché lazy iterator e se viene letto dopo il commit, è invalido.
  # se invece lo materializziamo subito castandolo, non dà problemi
  mercati = list(db.session.scalars(db.select(Mercati).order_by(Mercati.nome)))

  new_nome = None
  new_giorno = None
  inserted = session.get('inserted')
  if inserted:
    new_nome = inserted[0]
    new_giorno = inserted[1]
    session.pop('inserted')

  if request.method == 'POST':
    user = session['username']
    mode = session.get('add_mode')
    edit_id = session.get('edit_id')
    session.clear()
    session['username'] = user
    if mode:
      session['add_mode'] = mode
    if edit_id:
      session['edit_id'] = edit_id
    for key, val in request.form.items():
      session[key] = val
    
    error, validated = validate_input(request.form)

    if not error:
      try:
        if 'edit_id' in session:
          old = db.session.get(Mercati, {'nome': session['edit_id'][0], 'giorno': session['edit_id'][1]})
          old.nome = validated.nome
          old.giorno = validated.giorno
          old.is_attuale = validated.is_attuale
          old.is_evento = validated.is_evento

          db.session.commit()
          return redirect(url_for('mercati.edit_mode', nome=1, giorno=1))
        
        # stiamo aggiungendo un nuovo mercato
        db.session.add(validated)
        db.session.commit()
        session['inserted'] = (validated.nome, validated.giorno)
        return redirect(url_for('mercati.add_mode'))

      except exc.IntegrityError as e:
        db.session.rollback()
        if 'UNIQUE' in e._message():
          error = f'Esiste già il mercato "{validated.nome}" che si tiene il {validated.giorno.lower()}'
      
      except exc.SQLAlchemyError as e:
        db.session.rollback()
        error = str(e)
    
    flash(error)
    
  return render_template('mercati.html', mercati=mercati, new_nome=new_nome, new_giorno=new_giorno)

@bp.route('/visualizza/add-mode')
@login_required
@admin_required
def add_mode():
  if session.get('edit_id'):
    session.pop('edit_id')

  add_mode = session.get('add_mode')
  if add_mode:
    user = session['username']
    inserted = session.get('inserted')
    session.clear()
    session['username'] = user
    if inserted:
      session['inserted'] = inserted
  else:
    session['add_mode'] = True
  return redirect(url_for('mercati.visualizza'))

def validate_input(form):
  nome = form['nome'].capitalize()
  if not nome:
    return "Inserisci un nome per il mercato", None
  
  giorno = form['giorno']
  if giorno not in ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']:
    return "Giorno non valido", None
  
  is_attuale = bool(form.get('is_attuale'))
  is_evento = bool(form.get('is_evento'))

  if is_evento and is_attuale:
    return "Se il mercato è un evento, deseleziona la casella \"attuale\"", None
  
  if is_evento:
    is_attuale = None
  
  if is_attuale == False: # dobbiamo escludere il caso None
    nome += '_old'
  
  if is_attuale == True and nome.endswith('_old'):
    nome = nome[:-4]
  
  mercato = Mercati(
    nome=nome,
    giorno=giorno,
    is_attuale=is_attuale,
    is_evento=is_evento)
  
  return None, mercato

@bp.route('edit/<nome>/<giorno>')
@login_required
@admin_required
def edit_mode(nome, giorno):
  if session.get('add_mode'):
    session.pop('add_mode')
  
  if session.get('edit_id'):
    user = session['username']
    session.clear()
    session['username'] = user
  else:
    session['edit_id'] = (nome, giorno)
  return redirect(url_for('mercati.visualizza'))