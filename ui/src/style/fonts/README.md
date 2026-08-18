# Font vendorizzati

Cinque file, nessuno dei quali e' ancora qui:

```
barlow-semi-condensed-400.woff2
barlow-semi-condensed-500.woff2
barlow-semi-condensed-600.woff2
ibm-plex-mono-400.woff2
ibm-plex-mono-500.woff2
```

## Perche' nel repository e non installati nel sistema

Il ciclo di verifica visiva di SPEC §11.7 fa uno screenshot e lo giudica. Se i
font vengono dal sistema, lo stesso componente rende in modo diverso su una
macchina diversa, e il giudizio non e' riproducibile. Con i woff2 nel repo il
rendering dipende solo dal repo.

## Da dove prenderli

Aprire e copiare gli URL `woff2` dalla risposta:

```
https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500
```

Oppure dai repository upstream:

- `https://github.com/googlefonts/barlow`
- `https://github.com/IBM/plex/releases`

Gli URL di `fonts.gstatic.com` cambiano a ogni revisione, per questo non sono
fissati qui.

## Licenza

Entrambe le famiglie sono **SIL Open Font License 1.1**. La copia in un
progetto e' esplicitamente consentita. Depositare il testo della licenza in
questa directory come `OFL.txt` insieme ai file.

## Finche' mancano

`npm run shot` esce con codice diverso da zero e la galleria lo dichiara in
rosso: uno screenshot preso con i font di ripiego non deve poter passare per
una verifica riuscita.
