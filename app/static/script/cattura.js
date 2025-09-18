'use strict'

const video = document.getElementById('video')
const scatta = document.getElementById('scatta')
const preview = document.getElementById('preview')
const hq = document.getElementById('hq')
const flash = document.getElementById('flash')
const cover = document.getElementById('cover')
const foto = document.getElementById('foto')
const cancella = document.getElementById('cancella')
const invia = document.getElementById('invia')
const audio = document.querySelector('audio')
const btnWrapper = document.querySelector('.btn-wrapper')
const wave = document.querySelector('.wave')

let stream = null
let imgReady = false

getStream()

function getStream () {
  navigator.mediaDevices.getUserMedia({
    video: {
      width: { ideal: 10_000},
      height: { ideal: 10_000},
      facingMode: 'environment'
    }
  })
  .then(s => {
    stream = s
    video.srcObject = s
  })
  .catch(err => {
    console.log(`Succede se non c'è fotocamera compatibile oppure nega i permessiErrore di acquisizione dalla fotocamera. Dettagli errore: ${err}`)
  })
}

video.addEventListener('loadedmetadata', e => {
  hq.width = video.videoWidth
  hq.height = video.videoHeight

  preview.width = window.innerWidth
  preview.height = video.videoHeight * window.innerWidth / video.videoWidth
})

scatta.addEventListener('click', e => {
  flash.hidden = false
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      flash.hidden = true
    })
  })
  cover.hidden = false

  audio.play()

  scatta.hidden = true

  setTimeout(takePicture, 0)

  const previewCtx = preview.getContext('2d')
  previewCtx.drawImage(video, 0, 0, preview.width, preview.height)
  foto.src = preview.toDataURL('image/jpeg', 0.8)
  foto.hidden = false
  requestAnimationFrame(() => {
    foto.classList.add('shrink')
  })

  btnWrapper.classList.remove('hidden')
})

function takePicture () {
  const hqCtx = hq.getContext('2d')
  hqCtx.drawImage(video, 0, 0, hq.width, hq.height)
  imgReady = true
  invia.disabled = false
  invia.classList.remove('disabled')
  // icona FontAwesome tick col cerchio
  invia.innerHTML = '<i class="fa-regular fa-circle-check"></i>'

  const videoTrack = stream.getVideoTracks()[0]
  videoTrack.stop()
  stream.removeTrack(videoTrack)
}

cancella.addEventListener('click', () => {
  getStream()
  btnWrapper.classList.add('hidden')
  cover.hidden = true
  foto.hidden = true
  foto.classList.remove('shrink')
  scatta.hidden = false
  imgReady = false
  invia.disabled = true
  invia.classList.add('disabled')
  // icona FontAwesome spinner
  invia.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>'
})

invia.addEventListener('click', async () => {
  if (imgReady) {
    loading.classList.remove('hidden')
    try {
      const res = await fetch('/ocr/cattura', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          'image': hq.toDataURL('image/png')
        })
      })

      if (!res.ok) {
        throw new Error(`Richiesta fallita. Codice errore ${res.status}`);
      }
  
      const payload = await res.json()
      if (res.status !== 'ok') {
        // gestire l'errore
      }
      window.location.replace('/ocr')
    } catch (err) {
      console.log(err)
    }
  } else {
    
  }
})