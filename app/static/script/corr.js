'use strict'

const MAX_DIMENSION_PX = 3000

const mercatoInput = document.getElementById('mercato')
const giornoInput = document.getElementById('giorno_mercato')
const dataInput = document.getElementById('data')
const totaleInput = document.getElementById('totale')
const quantTotInput = document.getElementById('quantita_totale')
const errDialog = document.getElementById('error-dialog')
const errMsg = document.getElementById('error-message')
const loading = document.getElementById('loading')
const ocr = document.getElementById('ocr')

const inputs = document.querySelectorAll('input, select')
const reps = Array.from(inputs).filter(el => el.name.includes('reparto'))
const quants = Array.from(inputs).filter(el => el.name.includes('quantita'))

// const confirmationArticle = document.querySelector('.confirmation')

const defaultChildren = [ ...giornoInput.children ]
defaultChildren.forEach(opt => {
  opt.selected = false
})

// evidenziamo nell'interfaccia gli errori segnalati dal server
const errors = Object.keys(serverError)
if (errors.length) {
  errDialog.showModal()
  inputs.forEach(el => {
    if (errors.includes(el.name)) {
      el.classList.add('input-error')
    }
  })
}

errDialog.addEventListener('close', e => {
  if (!errMsg.hidden) {
    errMsg.hidden = true
  }
})

inputs.forEach(el => {
  el.addEventListener('change', e => {
    if (el.classList.contains('input-error')) {
      if (serverError?.totale === 'La somma dei reparti non coincide col totale.'
        && (el.name.includes('reparto') || el.name === 'totale')) {
        reps
          .filter(el => serverError[el.name] === '')
          .forEach(el => el.classList.remove('input-error'))
        totaleInput.classList.remove('input-error')

      } else if (serverError?.quantita_totale === 'La somma delle quantità dei reparti non coincide col n. pezzi.'
        && (el.name.includes('quantita') || el.name === 'quantita_totale')) {
        quants
          .filter(el => serverError[el.name] === '')
          .forEach(el => el.classList.remove('input-error'))
        quantTotInput.classList.remove('input-error')

      } else if (errors.includes('data-giorno') && (el.name === 'data' || el.name === 'giorno_mercato')) {
        dataInput.classList.remove('input-error')
        giornoInput.classList.remove('input-error')
      }

      el.classList.remove('input-error')
    }

    // rimuoviamo l'evidenziazione dell'OCR se l'utente corregge il valore
    if (el.classList.contains('ocr-input')) {
      el.classList.remove('ocr-input')
    }

    // imponiamo le due cifre decimali
    if (el.name.includes('reparto') || el.name === 'totale') {
      el.value = parseFloat(el.value).toFixed(2)
    }
  })

  if (el.value && (el.name.includes('reparto') || el.name === 'totale')) {
    el.value = parseFloat(el.value).toFixed(2)
  }
})

// gestiamo dinamicamente l'elenco dei giorni in base al mercato selezionato
mercatoInput.addEventListener('change', filter_giorni)
mercatoInput.addEventListener('change', removeBlank, {once: true})

if (session?.mercato) {
  mercatoInput.dispatchEvent(new Event('change'))
  mercatoInput.firstChild.selected = false
  for (const opt of giornoInput.children) {
    if (opt.value === session.giorno_mercato) {
      opt.selected = true
    }
  }
}

function filter_giorni (e) {
  giornoInput.replaceChildren(...defaultChildren)

  const mercato = e.target.value

  const giorni = [ 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica' ]
  const idxs = []
  mercati.forEach(m => {
    if (m.mercato === mercato) {
      idxs.push(giorni.indexOf(m.giorno))
    }
  })
  idxs.sort()

  const newChildren = []
  idxs.forEach(idx => {
    newChildren.push(defaultChildren[idx])
  })
  giornoInput.replaceChildren(...newChildren)
  giornoInput.firstChild.selected = true
}

function removeBlank (e) {
  [ ...e.target.children ].forEach(child => {
    if (child.value === '') {
      e.target.removeChild(child)
    }
  })
}

// AJAX per l'OCR
ocr.addEventListener('change', async e => {
  let file = e.target.files[0]
  if (!file || !file.type.startsWith('image/')) {
    errDialog.showModal()
    errMsg.hidden = false
    errMsg.innerText = 'Foto non acquisita correttamente. Riprova.'
    return
  }

  loading.showModal()

  try {
    const img = await loadImageFromFile(file)
    const { width, height } = img
    const largest = Math.max(width, height)

    // ridimensiona se necessario
    if (largest > MAX_DIMENSION_PX) {
      let w, h
      if (width > height) {
        w = MAX_DIMENSION_PX
        h = height * (w / width)
      } else {
        h = MAX_DIMENSION_PX
        w = width * (h / height)
      }

      const canvas = document.createElement('canvas')
      canvas.width = w
      canvas.height = h
      canvas.getContext('2d').drawImage(img, 0, 0, w, h)

      file = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg'))
    }

    // manda la richiesta
    const fd = new FormData()
    fd.append('image', file, 'tmp-photo.jpeg')
    try {
      const res = await fetch(ocrEndpoint, {
        method: 'POST',
        body: fd
      })

      if (!res.ok) {
        loading.close()
        errDialog.showModal()
        errMsg.hidden = false
        
        try {
          const payload = await res.json()
          errMsg.innerHTML = payload.message
          return
        } catch (jsonError) {
          console.log(res)
          throw new Error(`${res.status} - ${res.statusText}`)
        }
      }

      const payload = await res.json()
      const read = Object.keys(payload)
      inputs.forEach(el => {
        if (read.includes(el.name)) {
          el.classList.add('ocr-input')
          if (el.name.includes('reparto') || el.name === 'totale') {
            el.value = parseFloat(payload[el.name]).toFixed(2)
          } else {
            el.value = payload[el.name]
          }
        }
      })
      loading.close()

    } catch (error) {
      loading.close()
      errDialog.showModal()
      errMsg.hidden = false
      errMsg.innerHTML = `Qualcosa è andato storto.<br>Dettagli errore: <em>${error}</em>`
    }
  } catch (error) {
    console.log(error)
    loading.close()
    errDialog.showModal()
    errMsg.hidden = false
    errMsg.innerText = 'Non è stato possibile caricare l\'immagine'
  }
})

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = e => {
      const img = document.createElement('img')
      img.onload = () => resolve(img)
      img.onerror = reject
      img.src = e.target.result
    }
    reader.onerror = reject
    reader.readAsDataURL(file);
  })
}

// if (confirmationArticle) {
//   setTimeout(() => {
//     confirmationArticle.classList.add('confirmation-active')
//     const descendants = confirmationArticle.querySelectorAll('*')
//     for (const el of descendants) {
//       if (el.classList.contains('hidden')) {
//         el.classList.add('visible')
//       }
//     }
//   }, 100)
// }