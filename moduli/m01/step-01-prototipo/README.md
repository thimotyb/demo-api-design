# Step 01 — Un checkout che sembra funzionare

Eseguire dalla radice del repository:

```bash
python3 moduli/m01/step-01-prototipo/demo.py
```

Lo script è un prototipo didattico, non un servizio da pubblicare. Contiene un carrello fittizio con un articolo da **20 EUR**; il gateway simulato produce risposte prestabilite. L'output mostra quattro scenari: successo, errore transitorio, ripetizione della stessa richiesta e prezzo alterato a **1 EUR**. Il risultato esatto è in [`expected/observations.json`](expected/observations.json).

Per mostrare la fase di generazione assistita, il docente può usare il [prompt vago](prompt-vago.md) in una cartella separata; la prova valutata resta questa versione fissata nel repository.

1. Prima di leggere il codice, identificare quali scenari darebbero fiducia a un utente occasionale.
2. Eseguire lo script e annotare numero di tentativi, numero di ordini e importo autorizzato.
3. Leggere `demo.py` e trovare la riga che spiega ciascuna osservazione.
4. Confrontare con i file in [`caso-guida/`](../../../caso-guida/README.md). Quali aspettative sono esplicite nelle fonti? Quali non lo sono?

**Reset:** rilanciare il comando; non esiste stato persistente. Proseguire con [step 02](../step-02-analisi/README.md).
