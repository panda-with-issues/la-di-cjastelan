'use strict'

const mercatoInput = document.getElementById('mercato')
const giornoInput = document.getElementById('giorno_mercato')
const errDialog = document.getElementById('error-dialog')

const inputs = document.querySelectorAll('input, select')

// const confirmationArticle = document.querySelector('.confirmation')
const defaultChildren = [ ...giornoInput.children ]
defaultChildren.forEach(opt => {
  opt.selected = false
})

const errors = Object.keys(serverError)
if (errors.length) {
  errDialog.showModal()
  inputs.forEach(el => {
    if (errors.includes(el.name)) {
      el.classList.add('input-error')
    }
  })
}

inputs.forEach(el => {
  if (el.name.includes('reparto') || el.name === 'totale') {
    el.value = parseFloat(el.value).toFixed(2)
  }

  el.addEventListener('change', e => {
    if (el.classList.contains('input-error')) {
      el.classList.remove('input-error')
    }

    if (el.classList.contains('ocr-input')) {
      el.classList.remove('ocr-input')
    }

    if (el.name.includes('reparto') || el.name === 'totale') {
      el.value = parseFloat(el.value).toFixed(2)
    }
  })
})

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