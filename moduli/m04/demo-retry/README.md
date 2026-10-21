# Mini demo — dal requisito al retry verificato

Questa mini demo accompagna il flusso Spec Kit con un piccolo cambiamento Python isolato. Usa gateway sintetico, non modifica M01 e non dipende da pacchetti esterni.

## Prima di avviare Spec Kit

Dalla cartella `demo-retry/`, eseguire i test sullo starter:

```bash
python3 -m unittest -v
```

Lo starter fallisce gli scenari che richiedono un retry. Questo è il punto di partenza per il task di implementazione generato da Spec Kit.

| Test | Esito atteso sullo starter |
| --- | --- |
| Approvazione al primo tentativo | Passa |
| Transitorio seguito da approvazione | Fallisce: manca il secondo tentativo |
| Tre errori transitori | Fallisce: viene eseguito un solo tentativo e manca il suggerimento alternativo |

## Durante `implement`

Nel workspace temporaneo inizializzato con Spec Kit, copiare `payment_retry.py` e `test_payment_retry.py` da questa cartella. Prima di autorizzare l'agente a modificare il file, controllare che `tasks.md` includa:

- il massimo di tre tentativi per errore transitorio;
- l'arresto immediato dopo l'approvazione;
- un esito di fallimento con suggerimento alternativo dopo tre errori;
- nessun comportamento per le decisioni fuori ambito.

Invocare `implement` con l'integrazione configurata, rivedere il diff e rieseguire:

```bash
python3 -m unittest -v
```

I tre test devono passare. Poi invocare `converge` e verificare che l'agente confronti l'implementazione con i task e gli scenari, senza ampliare lo scope.

## Soluzione di riferimento

[`expected/payment_retry.py`](expected/payment_retry.py) è una possibile implementazione minima dei tre comportamenti. Per provarla senza alterare lo starter:

```bash
WORK_ROOT="$(mktemp -d)"
cp expected/payment_retry.py "$WORK_ROOT/payment_retry.py"
cp test_payment_retry.py "$WORK_ROOT/"
cd "$WORK_ROOT"
python3 -m unittest -v
```

**Reset:** per ripetere il confronto, creare un'altra directory temporanea. Al termine eliminare solo la directory stampata da `mktemp`; lo starter del repository resta intatto.
