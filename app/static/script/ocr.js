'use strict'

const video = document.getElementById('video')

const helpBtn = document.getElementById('help-btn')
const help = document.getElementById('help')

const scatta = document.getElementById('scatta')
const preview = document.getElementById('preview')
const hq = document.getElementById('hq')
const flash = document.getElementById('flash')

const foto = document.getElementById('foto')
const cancella = document.getElementById('cancella')
const invia = document.getElementById('invia')
const audio = document.querySelector('audio')
const btnWrapper = document.querySelector('.btn-wrapper')

const errDialog = document.getElementById('error')
const errDescription = document.getElementById('error-description')
const errBtn = document.getElementById('error-btn')

let stream
let imageCapture

let imgReady = false
let blob
let previewSrc

// TODO: Sistemare la roba della memoria

let resolution = {
  width: { ideal: 10_000 },
  height: { ideal: 10_000 },
}

getStream(resolution)

function getStream (resolution) {
  navigator.mediaDevices.getUserMedia({
    video: {
      ...resolution,
      facingMode: 'environment'
    }
  })
  .then(s => {
    stream = s
    video.srcObject = s

    if ('ImageCapture' in window) {
      const track = s.getVideoTracks()[0]
      imageCapture = new ImageCapture(track)
    }
  })
  .catch(error => {
    errDialog.showModal()
    errDescription.innerHTML =
      `Non sono stati concessi i permessi per usare la fotocamera o non è stata trovata una fotocamera compatibile.<br>
      Dettagli errore: <em>${error}</em>`
  })
}

video.addEventListener('loadedmetadata', e => {
  hq.width = video.videoWidth
  hq.height = video.videoHeight

  preview.width = window.innerWidth
  preview.height = video.videoHeight * window.innerWidth / video.videoWidth
})

helpBtn.addEventListener('click', () => {
  help.showModal()
})

scatta.addEventListener('click', async e => {
  flash.hidden = false
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      flash.hidden = true
    })
  })

  audio.play()

  scatta.hidden = true

  if (imageCapture) {
    await takePicture()
  } else {
    takePictureFallback()
  }

  foto.src = previewSrc
  foto.hidden = false

  btnWrapper.classList.remove('hidden')
})

foto.addEventListener('load', () => {
  foto.classList.add('shrink')
  // antipattern ma usato consapevolmente perché non voglio che l'utente interagisca con la preview
  if (blob) {
    URL.revokeObjectURL(previewSrc)
  }
})

async function takePicture () {
  try {
    blob = await imageCapture.takePhoto()
    previewSrc = URL.createObjectURL(blob)

    stopCamera()

    abilitateSend()
  } catch (error) {
    errDialog.showModal()
    errDescription.innerHTML = `Errore nell'acquisizione dell'immagine.<br>Dettagli errore: <em>${error}</em>.`
  }
  
}

function takePictureFallback () {
  const previewCtx = preview.getContext('2d')
  previewCtx.drawImage(video, 0, 0, preview.width, preview.height)
  previewSrc = preview.toDataURL('image/jpeg')

  const hqCtx = hq.getContext('2d')
  hqCtx.drawImage(video, 0, 0, hq.width, hq.height)
  imgReady = true
  
  stopCamera()

  abilitateSend()
}

function stopCamera () {
  const videoTrack = stream.getVideoTracks()[0]
  videoTrack.stop()
  stream.removeTrack(videoTrack)
}

function abilitateSend () {
  invia.disabled = false
  invia.classList.remove('disabled')
  // icona FontAwesome tick col cerchio
  invia.innerHTML = '<i class="fa-regular fa-circle-check"></i>'
}

cancella.addEventListener('click', reinitUI)

function reinitUI () {
  getStream(resolution)
  btnWrapper.classList.add('hidden')
  foto.hidden = true
  foto.classList.remove('shrink')
  foto.src = null
  previewSrc = null
  scatta.hidden = false
  imgReady = false
  blob = null
  invia.disabled = true
  invia.classList.add('disabled')
  // icona FontAwesome spinner
  invia.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>'
}

invia.addEventListener('click', async () => {
  if (blob || imgReady) {
    loading.showModal()
    
    if (!blob) {
      blob = await new Promise(resolve => hq.toBlob(resolve, 'image/jpeg'))
    }
    
    const fd = new FormData()
    fd.append('image', blob, 'tmp-img.jpeg')
    
    if (imageCapture) {
      fd.append('imageCapure', true)
    }
    fd.append('start', Date.now() / 1000)

    try {
      const res = await fetch(ocrEndpoint, {
        method: 'POST',
        body: fd
      })
    
      if (!res.ok) {
        loading.close()
        errDialog.showModal()
        
        try {
          const payload = await res.json()
          errDescription.innerHTML = payload.message
          
          if (payload.message.includes('esaurito la memoria')) {
            resolution = {
              width: { ideal: 2048 },
              height: { ideal: 2048 }
            }
          }
        } catch (jsonError) {
          console.log(res)
          throw new Error(`${res.status} - ${res.statusText}`)
        }
      } else if (!res.redirected) {
        throw new Error(`Risposta del server non valida. Risposta HTTP: ${res.status} - ${res.statusText}`)
      } else {
        window.location.replace(res.url)
      }
    } catch (error) {
      errDescription.innerHTML = `Qualcosa è andato storto.<br>Dettagli errore: <em>${error}</em>`
    }
  } else {
    errDialog.showModal()
    errDescription.textContent = 'Nessuna foto da leggere o la foto non è ancora pronta. Riprova tra poco.'
  }
})

errBtn.addEventListener('click', () => {
  errDialog.close()
  reinitUI()
})