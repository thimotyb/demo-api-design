# M01 — Dal prototipo al software professionale

## Obiettivo

Mostrare che un checkout capace di restituire una conferma nel caso felice può comunque essere inadatto al lavoro professionale. Gli studenti confrontano **comportamento osservato**, [requisiti originali](../../caso-guida/ecomm-requirements.md), [sequenza di retry](../../caso-guida/req-seq-payment-retry.puml) e [contratto API](../../caso-guida/req-apis.yaml), poi decidono quali lacune sono difetti rispetto alle fonti e quali richiedono una nuova decisione di prodotto.

**Durata indicativa:** 25–35 minuti. **Prerequisito:** Python 3.10+; nessun pacchetto aggiuntivo. **Dati:** solo fixture sintetiche; il gateway non chiama servizi esterni.

## Traccia per il docente

1. Mostrare il [prompt volutamente vago](step-01-prototipo/prompt-vago.md); facoltativamente eseguirlo live in una cartella di prova. Spiegare che il [prototipo fornito](step-01-prototipo/demo.py) è una *simulazione didattica* dell'output che una richiesta così incompleta potrebbe produrre, non il risultato attribuito a uno specifico modello.
2. Eseguire [step 01](step-01-prototipo/README.md). Il caso felice restituisce un ordine `PAID`; chiedere all'aula se basta per accettare la modifica.
3. Osservare le tre prove: autorizzazione transitoria non ritentata, richiesta ripetuta che crea due ordini, prezzo di riga alterato accettato senza confronto con catalogo/snapshot validato.
4. Aprire [step 02](step-02-analisi/README.md), far compilare la checklist individualmente o in coppia e confrontarla con la [revisione di riferimento](step-02-analisi/expected/review-example.md).
5. Chiudere con una domanda di progettazione per M03: quali comportamenti devono diventare criteri di accettazione prima di chiedere all'AI di cambiare il codice?

## Esecuzione

Dalla radice del repository:

```bash
python3 moduli/m01/step-01-prototipo/demo.py
python3 scripts/check_m01.py
```

Il primo comando stampa JSON deterministico. Il secondo confronta gli scenari con il risultato atteso e segnala la presenza delle lacune. **Reset:** il prototipo usa solo memoria di processo; basta rilanciare i comandi. Non vengono creati file né chiamate di rete.

## Criteri di riuscita della lezione

- Distinguere l'esito apparentemente corretto del caso felice dai casi mancanti.
- Collegare il retry mancato alla sequenza sorgente e la validazione prezzi al caso d'uso checkout.
- Trattare il doppio ordine come rischio osservato e decisione da formalizzare: il contratto specifica una chiave di idempotenza per `POST /payments`, ma non disciplina da solo la ripetizione dell'intero checkout.
- Proporre almeno un test che fallirebbe oggi e una verifica utile per il modulo successivo.

**Limite intenzionale:** M01 non implementa la soluzione; i moduli successivi introdurranno specifica, contratto, codice e test in modo progressivo.
