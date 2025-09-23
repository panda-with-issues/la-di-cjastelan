import easyocr
import re
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
from flask import (
    Blueprint, render_template, request, flash, jsonify, session
)
from torch.cuda import OutOfMemoryError
from app.auth import login_required

reader = easyocr.Reader(['it'])
bp = Blueprint('ocr', __name__, url_prefix='/ocr')

@bp.route('/')
@login_required
def ocr():
  result = ''
  if 'ocr_result' in session.keys():
    result = session.pop('ocr_result')
    import json
    result = f'{result}\n\n {json.dumps(parse_ocr_result(result))}'
  return render_template('ocr.html', result=result)

def parse_ocr_result(lst):
  i = 0
  res = {}
  current_rep = None
  while i < len(lst):
    word = lst[i].lower()

    if is_like(word, 'reparto totale'):
      i += 1
      word = lst[i]
      n = parse_float(word)
      res['totale'] = n

    elif is_like(word, 'reparto'):
      if is_like(lst[i+1].lower(), 'totale'):
        i += 2
        word = lst[i]
        n = parse_float(word)
        res['totale'] = n
      else:
        rep_n = check_rep(word, lst[i+1])
        if rep_n > 0:
          current_rep = rep_n

    elif is_like(word, 'quantita'):
      i += 1
      word = lst[i]
      n = parse_int(word)
      res[f'quantita{current_rep}'] = n

    elif is_like(word, 'totale'):
      i += 1
      word = lst[i]
      n = parse_float(word)
      res[f'reparto{current_rep}'] = n

    elif is_like(word, 'pezzi'):
      i += 1
      word = lst[i]
      n = parse_int(word)
      res['quantita_totale'] = n
    
    # cerca un pattern "<due cifre>-<due cifre>-<quattro cifre>"
    # che potrebbe indicare una data
    match = re.match(r"\b\d{2}-\d{2}-\d{4}\b", word)
    if match:
      try:
        date = datetime.strptime(match.group(0), '%d-%m-%Y')
        res['data'] = date.strftime('%Y-%m-%d')
      except ValueError:
        pass

    i += 1
  
  print(res)
  return res

def is_like(word, target):
  p = 0
  l = min(len(word), len(target))
  for i in range(l):
    if word[i] == target[i]:
      p += 1
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
      session['ocr_result'] = result
      return jsonify({
        'status': 'ok',
      })
    except OutOfMemoryError:
      return jsonify({
        'message': 'Immagine troppo grande: la GPU ha esaurito la memoria. La qualità della foto sarà automaticamente ridotta per il prossimo tentativo. Riprova.'
      }), 500
    except Exception as e:
      return jsonify({
        'message': f"Errore durante l'elaborazione dell'immagine. Dettagli: <em>{e}</em>"
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
