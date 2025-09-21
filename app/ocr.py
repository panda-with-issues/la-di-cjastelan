import easyocr
import re
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
from flask import (
    Blueprint, render_template, request, flash, jsonify, session, abort
)
from torch.cuda import OutOfMemoryError
from app.auth import login_required

reader = easyocr.Reader(['it'])
bp = Blueprint('ocr', __name__, url_prefix='/ocr')

@bp.route('/', methods=('GET', 'POST'))
@login_required
def ocr():
  result = ''
  error = None
  if request.method == 'POST':
    if 'file' not in request.files:
      error = 'File non caricato'
    else:
      # If the user does not select a file, the browser submits an
      # empty file without a filename.
      file = request.files['file']
      if file.filename == '':
        error = 'File non valido'

      if not error:
        image = Image.open(file.stream)
        image = np.array(image.convert('L'))
        result = reader.readtext(image, detail=0)
  # if 'image' in session.keys():
  #   img = session.pop('image')
  #   result = reader.readtext(img, detail=0)
  if 'result' in session.keys():
    result = session.pop('result')
    result = f'{result}\n\n' + parse_result(result)

  if error:
    flash(error)

  return render_template('ocr.html', result=result)

def parse_result(lst):
  i = 0
  res = ''
  while i < len(lst):
    word = lst[i].lower()

    if is_like(word, 'reparto totale'):
      res += 'Totale: '
      i += 1
      word = lst[i]
      n = parse_float(word)
      res += f'{n}\n\n'

    elif is_like(word, 'reparto'):
      if is_like(lst[i+1].lower(), 'totale'):
        res += 'Totale: '
        i += 2
        word = lst[i]
        n = parse_float(word)
        res += f'{n}\n\n'
      else:
        res += 'Reparto '
        rep = check_rep(word, lst[i+1])
        res += f'{rep}:\n\n'

    elif is_like(word, "quantita"):
      res += 'quantità: '
      i += 1
      word = lst[i]
      n = parse_int(word)
      res += f'{n}\n\n'

    elif is_like(word, 'totale'):
      res += 'totale: '
      i += 1
      word = lst[i]
      n = parse_float(word)
      res += f'{n}\n\n'

    elif is_like(word, 'pezzi'):
      res += '\nn. pezzi: '
      i += 1
      word = lst[i]
      n = parse_int(word)
      res += f'{n}\n\n'
    
    # cerca un pattern "<due cifre>-<due cifre>-<quattro cifre>"
    # che potrebbe indicare una data
    match = re.match(r"\b\d{2}-\d{2}-\d{4}\b", word)
    if match:
      try:
        date = datetime.strptime(match.group(0), '%d-%m-%Y')
        res += f'{date}'
      except ValueError:
        pass

    i += 1
  
  return res

def is_like(word, target):
  p = 0
  l = min(len(word), len(target))
  for i in range(l):
    if word[i] == target[i]:
      p += 1
  print(f'word: {word}, target: {target}, ratio: {p/len(target)}')
  return p / len(target) >= 0.7

def check_rep(word, next):
  rep = 0
  try:
    rep = int(word[-1])
  except ValueError:
    try:
      rep = int(next)
    except ValueError:
      pass
  
  if rep > 5:
    rep = 0
  
  return rep

def parse_int(word):
  try:
    n = int(word)
    return n
  except ValueError:
    return 0

def parse_float(word):
  word = word.replace(' ', '').replace(',', '.')
  try:
    n = float(word)
    return n
  except ValueError:
    return 0


@bp.route('cattura', methods=('GET', 'POST'))
@login_required
def cattura():
  if request.method == 'POST':
    if 'image' not in request.files:
      return jsonify({
        'message': 'Nessuna immagine inviata'
      }), 400
    
    blob = request.files['image']

    if blob.filename != 'tmp-img.png' or blob.mimetype != 'image/png':
      return jsonify({
        'message': 'Formato immagine non supportato'
      }), 400

    try:
      img = cv2.imdecode(np.frombuffer(blob.read(), np.uint8), cv2.IMREAD_COLOR)
      result = reader.readtext(img, detail=0)
      session['result'] = result
      return jsonify({
        'status': 'ok',
      })
    except OutOfMemoryError:
      return jsonify({
        'message': 'Immagine troppo grande: la GPU ha esaurito la memoria. Riprova più tardi.'
      }), 500
    except Exception as e:
      return jsonify({
        'message': f"Errore durante l'elaborazione dell'immagine. Dettagli: {e}"
      }), 500
    
  return render_template('cattura.html')

      # codice per salvare l'immagine sul server
      
      # import os
      # from flask import current_app
      # fname = os.path.join(current_app.instance_path, 'uploads', datetime.strftime(datetime.now(), '%y-%m-%d_%H:%M:%S.png'))
      # try:
      #   with open(fname, "wb") as f:
      #     f.write(decoded)
      #     #session['image'] = fname
      #   return jsonify({
      #     'status': 'ok',
      #     'filename': fname
      #   })
      # except Exception as e:
      #   return jsonify({
      #     'status': 'fail',
      #     'message': e
      #   })
