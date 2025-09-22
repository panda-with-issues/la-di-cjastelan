from flask import (
    Blueprint, render_template, request, flash, g, session, redirect, url_for
)
from sqlalchemy import or_, exc
from app.database import db, Mercati, Corrispettivi
import datetime
import re
import decimal

from app.auth import login_required

bp = Blueprint('corr', __name__, url_prefix='/corr')

@bp.route('/inserisci', methods=('GET', 'POST'))
@login_required
def inserisci():
  if (session.get('to_insert')):
    session.pop('to_insert')
    
  # Va castato a list perché scalars ritorna un iteratore che consuma i dati quando ci iteri sopra, quindi non posso
  # iterarci due volte senza rifare la query
  mercati = list(db.session.scalars(db.select(Mercati).where(or_(Mercati.is_attuale==True, Mercati.is_evento==True))))
  mercati_nomi = set([ mercato.nome for mercato in mercati ])
  mercati_dict = [ { 'mercato': mercato.nome, 'giorno': mercato.giorno } for mercato in mercati ]

  if request.method == 'POST':
    for key, val in request.form.items():
      session[key] = val
    
    error, corrispettivo = validate_input(request, mercati_nomi)

    if error is None:
      cassa_sballata = False

      # alert se cassa > 3
      if corrispettivo.cassa not in [ f'Cassa {i}' for i in range(1, 4) ]:
        cassa_sballata = True
        to_insert = { column.key: getattr(corrispettivo, column.key) for column in corrispettivo.__mapper__.columns }
        session['to_insert'] = to_insert
        return render_template('corr/inserisci.html',
                               confirmation=True, corrispettivo=corrispettivo,
                               cassa_sballata=cassa_sballata,
                               mercati=mercati_dict, mercati_nomi=mercati_nomi)
      
      try:
        db.session.add(corrispettivo)
        db.session.commit()

        user = session['username']
        session.clear()
        inserted = { column.key: getattr(corrispettivo, column.key) for column in corrispettivo.__mapper__.columns }
        inserted['data'] = datetime.datetime.strftime(inserted['data'], '%d-%m-%y')
        inserted['ts'] = datetime.datetime.strftime(inserted['ts'], '%d-%m-%y %H:%M')
        session['inserted'] = inserted
        session['username'] = user
        return redirect(url_for('corr.success'))
      
      except exc.IntegrityError as e:
        db.session.rollback()
        e = e._message()
        if 'UNIQUE' in e and 'Corrispettivi.data' in e and 'Corrispettivi.mercato' in e:
          error = f'Esiste già un corrispettivo per il mercato {corrispettivo.mercato} svoltosi il {corrispettivo.data}'
        else:
          error = f'Qualcosa è andato storto: {e}'

      except exc.SQLAlchemyError as e:
        db.session.rollback()
        error = str(e)

    flash(error)
 
  return render_template('corr/inserisci.html',
                         confirmation=False, today=datetime.date.today(),
                         mercati=mercati_dict, mercati_nomi=mercati_nomi)

def validate_input(req, mercati):
  corrispettivo = Corrispettivi(ts=datetime.datetime.now(), inserito_da=g.user.username)
  
  # data
  try:
    data = datetime.datetime.strptime(request.form['data'], '%Y-%m-%d').date()
  except:
    return 'La data inserita non è valida', corrispettivo
  
  if (data > corrispettivo.ts.date()):
    return 'La data non può essere successiva a oggi', corrispettivo
  corrispettivo.data = data

  # mercati
  mercato = request.form['mercato']

  if mercato not in mercati:
    return 'Mercato non valido', corrispettivo
  corrispettivo.mercato = mercato

  # giorno_mercato
  giorno_mercato = request.form['giorno_mercato']
  weekdays = [ 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica' ]
  if giorno_mercato not in weekdays:
    return 'Giorno della settimana non valido', corrispettivo
  corrispettivo.giorno_mercato = giorno_mercato

  # controlliamo che la data inserita corrisponda al giorno del mercato inserito
  if (weekdays[corrispettivo.data.weekday()] != corrispettivo.giorno_mercato):
    return f'Il {datetime.datetime.strftime(corrispettivo.data, "%d-%m-%y")} non era {corrispettivo.giorno_mercato.lower()}', corrispettivo
  
  # controlliamo che il mercato sia attuale. Dovrebbe essere già garantito dalla query su `mercati`
  mercato = db.session.scalar(db.select(Mercati).where(Mercati.nome == mercato and Mercati.giorno == giorno_mercato))
  assert mercato
  assert bool(mercato.is_attuale) ^ mercato.is_evento

  # cassa
  cassa = request.form['cassa']
  if not re.fullmatch(r"Cassa [1-9]", cassa):
    return 'La cassa non è valida', corrispettivo
  corrispettivo.cassa = cassa

  # reparti
  reparti = [ reparto for reparto in request.form.keys() if 'reparto' in reparto ]
  somma = 0
  for i, rep in enumerate(reparti):
    try:
      reparto = decimal.Decimal(request.form[rep] if request.form[rep] != '' else 0)
    except:
      return f'Valore invalido per il reparto {i+1}', corrispettivo
    
    if reparto.as_tuple().exponent < -2:
     return f'Reparto {i+1} ha più di due cifre decimali', corrispettivo
    
    if reparto < 0:
      return f'Reparto {i+1} non può essere negativo', corrispettivo
    
    setattr(corrispettivo, rep, reparto)
    
    somma += reparto
  
  # totale
  try:
    totale = decimal.Decimal(request.form['totale'])
  except:
    return 'Valore invalido per il totale', corrispettivo
  
  if totale.as_tuple().exponent < -2:
    return f'Totale ha più di due cifre decimali', corrispettivo
  
  if totale < 0:
    return f'Totale non può essere negativo', corrispettivo
  
  if somma != totale:
    return 'La somma dei reparti non coincide col totale', corrispettivo

  # resta da controllare se esiste già uno scontrino con i cinque reparti uguali e dare un warning
  # perché potrebbe trattarsi di un duplicato

  return None, corrispettivo

@bp.route('inserisci/success')
@login_required
def success():
  inserted = session.pop('inserted')
  return render_template('corr/success.html', inserted=inserted)

@bp.route('inserisci/insert')
@login_required
def insert():
  c = session.pop('to_insert')
  corrispettivo = Corrispettivi(
    data = datetime.datetime.strptime(c['data'], '%a, %d %b %Y %H:%M:%S %Z').date(),
    mercato = c['mercato'],
    ts = c['ts'],
    inserito_da = c['inserito_da'],
    giorno_mercato=c['giorno_mercato'],
    cassa = c['cassa'],
    reparto1 = c['reparto1'],
    reparto2 = c['reparto2'],
    reparto3 = c['reparto3'],
    reparto4 = c['reparto4'],
    reparto5 = c['reparto5']
  )

  try:
    db.session.add(corrispettivo)
    db.session.commit()

    user = session['username']
    session.clear()
    inserted = { column.key: getattr(corrispettivo, column.key) for column in corrispettivo.__mapper__.columns }
    inserted['data'] = datetime.datetime.strftime(inserted['data'], '%d-%m-%y')
    inserted['ts'] = datetime.datetime.strftime(inserted['ts'], '%d-%m-%y %H:%M')
    session['inserted'] = inserted
    session['username'] = user
    return redirect(url_for('corr.success'))
  
  except exc.IntegrityError as e:
    db.session.rollback()
    e = e._message()
    if 'UNIQUE' in e and 'Corrispettivi.data' in e and 'Corrispettivi.mercato' in e:
      flash(f'Esiste già un corrispettivo per il mercato {corrispettivo.mercato} svoltosi il {corrispettivo.data}')
    else:
      flash(f'Qualcosa è andato storto: {e}')
    return redirect(url_for('corr.inserisci'))

  except exc.SQLAlchemyError as e:
    db.session.rollback()
    flash(str(e))
    return redirect(url_for('corr.inserisci'))