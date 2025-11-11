from flask import (
    Blueprint, render_template, request, g, session, redirect, url_for, abort
)
from sqlalchemy import or_, exc
from app.database import db, Mercati, Corrispettivi
from markupsafe import Markup
import datetime
import re
import decimal

from app.auth import login_required

bp = Blueprint('corr', __name__, url_prefix='/corr')

@bp.route('/', methods=('GET', 'POST'))
@login_required
def inserisci():
  # Va castato a list perché scalars ritorna un iteratore che consuma i dati quando ci iteri sopra, quindi non posso
  # iterarci due volte senza rifare la query
  mercati = list(db.session.scalars(db.select(Mercati).where(or_(Mercati.is_attuale==True, Mercati.is_evento==True))))
  mercati_nomi = set([ mercato.nome for mercato in mercati ])
  mercati_dict = [ { 'mercato': mercato.nome, 'giorno': mercato.giorno } for mercato in mercati ]

  error = {}
  if request.method == 'POST':
    for key, val in request.form.items():
      session[key] = val
          
    error, corrispettivo = validate_input(request, mercati_nomi)

    if not error:
      try:
        db.session.add(corrispettivo)
        db.session.commit()

        user = session['username']
        session.clear()

        inserted = { column.key: getattr(corrispettivo, column.key) for column in corrispettivo.__mapper__.columns }
        inserted['data'] = datetime.datetime.strftime(inserted['data'], '%d-%m-%Y')
        inserted['ts'] = datetime.datetime.strftime(inserted['ts'], '%d-%m-%Y %H:%M')

        session['inserted'] = inserted
        session['username'] = user
        return redirect(url_for('corr.success'))
      
      except exc.IntegrityError as e:
        db.session.rollback()
        e = e._message()
        if 'UNIQUE' in e and 'Corrispettivi.data' in e and 'Corrispettivi.mercato' in e:
          error['message'] = f'Esiste già un corrispettivo per il mercato {corrispettivo.mercato} svoltosi il\
          {datetime.datetime.strftime(corrispettivo.data, "%d-%m-%Y")}.'
        else:
          error['message'] = Markup(f'Errore di integrità nel database.<br>Dettagli errore: <em>{e}</em>.')

      except exc.SQLAlchemyError as e:
        db.session.rollback()
        error['message'] = Markup(f'Errore nel database.<br>Dettagli errore: <em>{e}</em>.')
 
  return render_template('corr/inserisci.html',
                         today = datetime.date.today(),
                         mercati = mercati_dict,
                         mercati_nomi = mercati_nomi,
                         error = error)

def validate_input(req, mercati):
  corrispettivo = Corrispettivi(ts=datetime.datetime.now(), inserito_da=g.user.username)
  error = {}
  
  # data
  try:
    data = datetime.datetime.strptime(request.form['data'], '%Y-%m-%d').date()
    if (data > corrispettivo.ts.date()):
      error['data'] = 'La data non può essere successiva a oggi.'
  except:
    error['data'] = 'La data inserita non è valida.'

  corrispettivo.data = data

  # mercati
  mercato = request.form['mercato']
  if mercato not in mercati:
    error['mercato'] = 'Mercato non valido.'

  corrispettivo.mercato = mercato

  # giorno_mercato
  giorno_mercato = request.form['giorno_mercato']
  weekdays = [ 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica' ]
  if giorno_mercato not in weekdays:
    error['giorno_mercato'] = 'Giorno della settimana non valido.'

  corrispettivo.giorno_mercato = giorno_mercato

  # controlliamo che la data inserita corrisponda al giorno del mercato inserito
  if (weekdays[corrispettivo.data.weekday()] != corrispettivo.giorno_mercato):
    error['data'] = error['data'] if 'data' in error else ''
    error['giorno_mercato'] = error['giorno_mercato'] if 'giorno_mercato' in error else ''
    error['data-giorno'] = f'Il {datetime.datetime.strftime(corrispettivo.data, "%d-%m-%y")} non era {corrispettivo.giorno_mercato.lower()}.'
  
  # controlliamo che il mercato sia attuale. Dovrebbe essere già garantito dalla query su 'mercati'
  mercato = db.session.scalar(db.select(Mercati).where(Mercati.nome == mercato and Mercati.giorno == giorno_mercato))
  assert mercato
  assert bool(mercato.is_attuale) ^ mercato.is_evento

  # cassa
  cassa = request.form['cassa']
  if not re.fullmatch(r'Cassa [1-3]', cassa):
    error['cassa'] = 'La cassa non è valida.'

  corrispettivo.cassa = cassa

  # reparti
  reparti = [ k for k in request.form if 'reparto' in k ]
  somma_reparti = 0
  for i, reparto in enumerate(reparti):
    try:
      tot = decimal.Decimal(request.form[reparto] if request.form[reparto] != '' else 0)
      if tot.as_tuple().exponent < -2:
        error[f'reparto{i+1}'] = f'Il totale del Reparto {i+1} non può avere più di due cifre decimali.'

      if tot < 0:
        error[f'reparto{i+1}'] = f'Il totale del Reparto {i+1} non può essere negativo.'

      setattr(corrispettivo, reparto, tot)
   
      somma_reparti += tot

    except:
      error[f'reparto{i+1}'] = f'Valore invalido per il totale del Reparto {i+1}.'

  # quantità
  quantitas = [ k for k in request.form if 'quantita' in k and 'totale' not in k ]
  somma_quantita = 0
  for i, quantita in enumerate(quantitas):
    try:
      tot = int(request.form[quantita]) if request.form[quantita] != '' else 0

      if tot < 0:
        error[f'quantita{i+1}'] = f'La quantità del Reparto {i+1} non può essere negativa.'

      setattr(corrispettivo, quantita, tot)
   
      somma_quantita += tot

    except:
      error[f'quantita{i+1}'] = f'Valore invalido per la quantità del Reparto {i+1}.'
  
  # totale reparti
  try:
    rep_totale = decimal.Decimal(request.form['totale'])
    if rep_totale.as_tuple().exponent < -2:
      error['totale'] = 'Il totale non può avere più di due cifre decimali.'
    
    if rep_totale < 0:
      error['totale'] = 'Il totale non può essere negativo.'
    
    if somma_reparti != rep_totale:
      error['reparto1'] = error['reparto1'] if 'reparto1' in error else ''
      error['reparto2'] = error['reparto2'] if 'reparto2' in error else ''
      error['reparto3'] = error['reparto3'] if 'reparto3' in error else ''
      error['reparto4'] = error['reparto4'] if 'reparto4' in error else ''
      error['reparto5'] = error['reparto5'] if 'reparto5' in error else ''
      error['totale'] = 'La somma dei reparti non coincide col totale.'
  
  except Exception as e:
    error['totale'] = 'Valore invalido per il totale.'

  # n. pezzi
  try:
    q_totale = int(request.form['quantita_totale'])
    
    if q_totale < 0:
      error['q_totale'] = 'Il n. pezzi non può essere negativo.'
    
    if somma_quantita != q_totale:
      error['quantita1'] = error['quantita1'] if 'quantita1' in error else ''
      error['quantita2'] = error['quantita2'] if 'quantita2' in error else ''
      error['quantita3'] = error['quantita3'] if 'quantita3' in error else ''
      error['quantita4'] = error['quantita4'] if 'quantita4' in error else ''
      error['quantita5'] = error['quantita5'] if 'quantita5' in error else ''
      error['quantita_totale'] = 'La somma delle quantità dei reparti non coincide col n. pezzi.'
  
  except:
    error['quantita_totale'] = 'Valore invalido per il totale.'

  # resta da controllare se esiste già uno scontrino con i cinque reparti uguali e dare un warning
  # perché potrebbe trattarsi di un duplicato

  return error, corrispettivo

@bp.route('/success')
@login_required
def success():
  inserted = session.get('inserted')
  if not inserted:
    abort(400, description="La sessione è scaduta o non si stava inserendo nessun corrispettivo.")
  
  session.pop('inserted')
  return render_template('corr/success.html', inserted=inserted)

@bp.post('/ocr')
@login_required
def ocr():
  for name, val in request.form.items():
    session[name] = val
  return render_template('ocr.html')

# if (session.get('to_insert')):
#    session.pop('to_insert')
# cassa_sballata = False

# # alert se cassa > 3
# if corrispettivo.cassa not in [ f'Cassa {i}' for i in range(1, 4) ]:
#   cassa_sballata = True
#   to_insert = { column.key: getattr(corrispettivo, column.key) for column in corrispettivo.__mapper__.columns }
#   session['to_insert'] = to_insert
#   return render_template('corr/inserisci.html',
#                          confirmation=True, corrispettivo=corrispettivo,
#                          cassa_sballata=cassa_sballata,
#                          mercati=mercati_dict, mercati_nomi=mercati_nomi)

# @bp.route('/insert')
# @login_required
# def insert():
#   c = session.pop('to_insert')
#   corrispettivo = Corrispettivi(
#     data = datetime.datetime.strptime(c['data'], '%a, %d %b %Y %H:%M:%S %Z').date(),
#     mercato = c['mercato'],
#     ts = c['ts'],
#     inserito_da = c['inserito_da'],
#     giorno_mercato=c['giorno_mercato'],
#     cassa = c['cassa'],
#     reparto1 = c['reparto1'],
#     reparto2 = c['reparto2'],
#     reparto3 = c['reparto3'],
#     reparto4 = c['reparto4'],
#     reparto5 = c['reparto5']
#   )

#   try:
#     db.session.add(corrispettivo)
#     db.session.commit()

#     user = session['username']
#     session.clear()
#     inserted = { column.key: getattr(corrispettivo, column.key) for column in corrispettivo.__mapper__.columns }
#     inserted['data'] = datetime.datetime.strftime(inserted['data'], '%d-%m-%y')
#     inserted['ts'] = datetime.datetime.strftime(inserted['ts'], '%d-%m-%y %H:%M')
#     session['inserted'] = inserted
#     session['username'] = user
#     return redirect(url_for('corr.success'))
  
#   except exc.IntegrityError as e:
#     db.session.rollback()
#     e = e._message()
#     if 'UNIQUE' in e and 'Corrispettivi.data' in e and 'Corrispettivi.mercato' in e:
#       flash(f'Esiste già un corrispettivo per il mercato {corrispettivo.mercato} svoltosi il {corrispettivo.data}')
#     else:
#       flash(f'Qualcosa è andato storto: {e}')
#     return redirect(url_for('corr.inserisci'))

#   except exc.SQLAlchemyError as e:
#     db.session.rollback()
#     flash(str(e))
#     return redirect(url_for('corr.inserisci'))