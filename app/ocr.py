import easyocr
import re
from datetime import datetime
import cv2
import numpy as np
from flask import Blueprint, request
from torch.cuda import OutOfMemoryError
from app.auth import login_required

reader = easyocr.Reader(['it'])
bp = Blueprint('ocr', __name__, url_prefix='/ocr')

@bp.post('/')
@login_required
def ocr():
  if 'image' not in request.files:
    return {
      'message': 'Nessuna immagine inviata'
    }, 400
  
  f = request.files['image']

  if f.filename != 'tmp-photo.jpeg' or f.mimetype != 'image/jpeg':
    return {
      'message': 'Formato immagine non supportato'
    }, 400

  try:
    img = cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_COLOR)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    img = gain_and_bias_correction(img, 3)
    img, fallback = crop_roi(img)

    parsed = None
    if img is not None:
      parsed = read_img(img)
      if len(parsed) < 6:
        parsed2 = read_img(fallback)
        parsed |= parsed2
    else:
      parsed = read_img(fallback)

    if len(parsed) == 0:
      return {
        'message': 'Impossibile leggere lo scontrino. Prova a scattare una foto migliore, con luminosità uniforme e su sfondo scuro.'
      }, 500
    
    return parsed
  
  except OutOfMemoryError:
    return {
      'message': 'La GPU ha esaurito la memoria. Riprova tra qualche minuto.'
    }, 500
  
  except Exception as e:
    return {
      'message': f"Errore durante l'elaborazione dell'immagine. Dettagli: <em>{e}</em>"
    }, 500

def parse_ocr_result(lst):
  j = 1
  res = {}
  current_rep = None
  l = len(lst)
  while j <= l:
    i = j-1
    word = lst[i].lower()
    # sistemiamo gli spazi, in modo che ce ne sia solo uno tra una parola e l'altra
    word = ' '.join(word.split())
    nxt = None
    if j != l:
      nxt = lst[j]
    
    if is_like(word, 'reparto totale'):
      if nxt:
        n = parse_float(nxt)
        res['totale'] = n
        j += 1
        continue

    elif is_like(word, 'reparto'):
      # potrebbe essere 'reparto totale'
      if nxt and is_like(' '.join(nxt.lower().split()), 'totale'):
        if j+1 < l:
          nxt = lst[j+1]
          n = parse_float(nxt)
          res['totale'] = n
          j += 2
          continue
      else:
        n = get_rep(word, nxt)
        if n > 0:
          current_rep = n
          j += 1
          continue
        elif current_rep:
          # non è stato riconosciuto il numero del reparto. Se è stato letto almeno un reparto,
          # proviamo a indovinare che il reparto corrente è il successivo all'ultimo letto
          current_rep += 1
          j += 1
          continue 

    elif is_like(word, 'quantita'):
      if nxt:
        n = parse_int(nxt)
        if current_rep and n > 0:
          res[f'quantita{current_rep}'] = n
          j += 1
          continue

    elif is_like(word, 'totale'):
      if nxt:
        n = parse_float(nxt)
        if current_rep and n > 0:
          res[f'reparto{current_rep}'] = n
          j += 1
          continue

    elif is_like(word, 'pezzi'):
      if nxt:
        n = parse_int(nxt)
        if n > 0:
          res['quantita_totale'] = n
          j += 1
          continue

    is_date = False
    # cerca un pattern "<due cifre>-<due cifre>-<almeno quattro cifre>"
    # che potrebbe indicare una data
    match = re.match(r"\b\d{2}-\d{2}-\d{4,}\b", word)
    if match:
      # se ho matchato anche l'orario, prendo solo la parte con la data
      match = match.group(0)[:10]
      try:
        date = datetime.strptime(match, '%d-%m-%Y')
        res['data'] = date.strftime('%Y-%m-%d')
        is_date = True
      except ValueError:
        pass

    if not is_date:    
        # proviamo il pattern "<due cifre> <due cifre> <almeno quattro cifre>"
        match = re.match(r"\b\d{2}\s\d{2}\s\d{4,}\b", word)
        if match:
          match = match.group(0)[:10]
          try:
            date = datetime.strptime(match, '%d %m %Y')
            res['data'] = date.strftime('%Y-%m-%d')
            is_date = True
          except ValueError:
            pass

    if not is_date:
        # proviamo il pattern "<due cifre>-<due cifre> <almeno quattro cifre>"
        match = re.match(r"\b\d{2}-\d{2}\s\d{4,}\b", word)
        if match:
          match = match.group(0)[:10]
          try:
            date = datetime.strptime(match, '%d-%m %Y')
            res['data'] = date.strftime('%Y-%m-%d')
            is_date = True
          except ValueError:
            pass
              
    if not is_date:
        # infine il pattern "<due cifre> <due cifre>-<almeno quattro cifre>"
        match = re.match(r"\b\d{2}-\d{2}-\d{4,}\b", word)
        if match:
          match = match.group(0)[:10]
          try:
            date = datetime.strptime(match, '%d %m-%Y')
            res['data'] = date.strftime('%Y-%m-%d')
          except ValueError:
            pass

    j += 1
  return res

def is_like(word, target):
  match = 0
  l = min(len(word), len(target))
  for i in range(l):
    if word[i] == target[i]:
      match += 1
  return match / len(target) >= 0.6

# ottiene il numero del reparto che si sta leggendo
# controllando sia la parola stessa ('reparto n') sia la successiva
# (in caso di situazioni tipo 'reparto' 'n'). Se fallisce, ritorna 0
def get_rep(word, nxt):
  rep = 0
  try:
    rep = int(word[-1])
  except ValueError:
    if nxt:
      try:
        rep = int(nxt)
      except ValueError:
        pass
  
  if rep > 5:
    rep = 0
  
  return rep

def parse_int(word):
  word = word.replace(' ', '')
  # i leading 0 sono quasi sicuramente 8
  if len(word) > 1 and word[0] == '0':
    word = '8' + word[1:]
  try:
    n = int(word)
    return n
  except ValueError:
    return 0

def parse_float(word):
  word = word.replace(' ', '').replace(',', '.')
  # il leading 0 non seguito da virgola è quasi sicuramente un 8
  if len(word) > 1 and word[0] == '0' and word[1] != '.':
    word = '8' + word[1:]
  try:
    n = float(word)
    return n
  except ValueError:
    return 0

def read_img(img):
  h, w = img.shape[:2]
  if w > h:
    # l'immagine è orizzontale
    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
      
  result = reader.readtext(img, detail=0)
  parsed = parse_ocr_result(result)
  read = len(parsed)
  if read < 6:
    # risultato non soddisfacente, capovolgiamo l'immagine
    img = cv2.rotate(img, cv2.ROTATE_180)
    result = reader.readtext(img, detail=0)
    parsed2 = parse_ocr_result(result)
    if len(parsed2) > read:
      parsed = parsed2
  
  print(result)
  print(parsed)
  return parsed

def distance(x, y):
  return np.sqrt(((x[0] - y[0]) ** 2) + ((x[1] - y[1]) ** 2))

def scale_img(img, new_max):
  h, w = img.shape[:2]
  ratio = None
  new_width = None
  new_height = None
  if (h > w):
    new_height = new_max
    new_width = int(w * new_height / h)
    ratio = h / new_height
  else:
    new_width = new_max
    new_height = int(h * new_width / w)
    ratio = w / new_width
    
  shrinked = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
  return shrinked, new_width, new_height, ratio

def crop_roi(img):
  shrinked, w, _, ratio = scale_img(img, 500)
  gray = cv2.cvtColor(shrinked, cv2.COLOR_BGR2GRAY)
  gray = cv2.GaussianBlur(gray, (5, 5), 0)
  _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
      
  contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)    
  cnt = max(contours, key=cv2.contourArea)

  # rettangolo di delimitazione di fallback
  x, y, rw, rh = (int(val * ratio) for val in cv2.boundingRect(cnt))
  fallback = img[y:y+rh, x:x+rw]
  
  peri = cv2.arcLength(cnt, True)
  epsilon = 0.01 * peri
  approx = cv2.approxPolyDP(cnt, epsilon, True)
      
  # ordino sulle y
  pts = sorted(approx, key=lambda p: p[0][1])
  pts = np.array(pts).reshape(len(pts), 2)

  if len(pts) < 4:
    return None, fallback

  if len(pts) > 4:
    selected = np.zeros((4, 2), dtype='int32')
    selected[0] = pts[0]
    i = 1
    while distance(selected[0], pts[i]) < w/3:
      i += 1
    selected[1] = pts[i]

    selected[3] = pts[-1]
    i = -2
    while distance(selected[3], pts[i]) < w/3:
      i -= 1
    selected[2] = pts[i]
    pts = selected

  # ordiniamo i punti da top-left a bottom-right in senso orario
  # li ho già ordinati per y, basta guardare la x
  roi = np.zeros((4, 2), dtype='float32')
  if pts[0][0] < pts[1][0]:
    roi[0], roi[1] = pts[0], pts[1]
  else:
    roi[0], roi[1] = pts[1], pts[0]
  if pts[2][0] < pts[3][0]:
    roi[2], roi[3] = pts[3], pts[2]
  else:
    roi[2], roi[3] = pts[2], pts[3]

  # proiettiamo i punti e applichiamo la distorsione
  roi *= ratio
  tl, tr, br, bl = roi
  
  widthA = distance(br, bl)
  widthB = distance(tr, tl)
  
  heightA = distance(tr, br)
  heightB = distance(tl, bl)

  maxWidth = max(int(widthA), int(widthB))
  maxHeight = max(int(heightA), int(heightB))

  dst = np.array([
    [0, 0],
    [maxWidth - 1, 0],
    [maxWidth - 1, maxHeight - 1],
    [0, maxHeight - 1]
    ], dtype = "float32"
  )
  
  M = cv2.getPerspectiveTransform(roi, dst)
  warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))
  return warped, fallback

def gain_and_bias_correction(img, threshold):
  gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
  hist = cv2.calcHist([gray], [0], None, [256], [0,256])
  hist_size = len(hist)

  # calcola l'istogramma delle frequenze cumulate
  accumulator = []
  accumulator.append(float(hist[0][0]))
  for i in range(1, hist_size):
    accumulator.append(accumulator[i -1] + float(hist[i][0]))

  n_px = accumulator[-1]
  clip_thresh = n_px * (threshold / 100) / 2

  minimum_gray = 0
  while accumulator[minimum_gray] < clip_thresh:
    minimum_gray += 1

  maximum_gray = hist_size -1
  while accumulator[maximum_gray] >= (n_px - clip_thresh):
    maximum_gray -= 1

  alpha = 255 / (maximum_gray - minimum_gray)
  beta = -minimum_gray * alpha

  img = img * alpha + beta
  img[img < 0] = 0
  img[img > 255] = 255
  return img.astype(np.uint8)

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