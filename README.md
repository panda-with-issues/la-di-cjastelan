# Installazione

Per installare il progetto e le sue dipendenze, eseguire all'interno del repository

```
pip install app
```

Occorrerà anche installare la giusta distribuzione di `torch` e `torchvision` per la propria scheda grafica seguendo le istruzioni a [questo link](https://pytorch.org/get-started/locally/).

Per avviare l'app, eseguire dalla root directory del repository:

```
flask run --debug
```

Per testare l'app su telefono, eseguire il tunneling inoltrando la porta 5000. Per accedere con privilegi da admin, usare come username `Dario` e password `pw`. Per accedere come utente normale, usare come username `Yuuki` e come password sempre `pw`.

# Relazioni

Le relazioni sul lavoro effettuato sono state redatte su dei notebook Jupyter. Per visualizzarli occorre installare:

```
pip install notebook
```

Se si vuole eseguire il codice all'interno dei notebook (non dovrebbe essercene bisogno), occorre installare anche Pandas, Matplotlib e Seaborn

```
pip install pandas matplotlib seaborn
```

Tutti i DataFrame sono salvati in file `.pickle` che vengono trasmessi a parte, nel caso in cui si volessero fare operazioni sopra. Anche le immagini del test set sono trasmesse a parte e, se si vuole eseguire il codice all'interno del notebook, occorre piazzare i pickle nella cartella `instance/ocr-pickles` e le immagini nella cartella `instance/test-set`.

La relazione riguardo il progetto d'esame è tutta dentro il file `relazione_iot.ipynb`. La relazione che spiega in modo consuntivo cosa è stato sviluppato è nel file `relazione_integrazione.ipynb`.