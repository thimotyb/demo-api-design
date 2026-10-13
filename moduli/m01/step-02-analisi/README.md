# Step 02 — Dalle osservazioni ai criteri professionali

Consultare [`review-template.md`](review-template.md) e compilarne una copia personale. Per ogni osservazione dello step 01 indicare: evidenza riproducibile, fonte pertinente, classificazione (*difetto rispetto alla fonte*, *rischio da decidere* o *fuori ambito*) e prossimo controllo.

Usare almeno questi riferimenti:

- [`ecomm-requirements.md`](../../../caso-guida/ecomm-requirements.md): checkout, pricing validation e flusso di pagamento;
- [`req-seq-payment-retry.puml`](../../../caso-guida/req-seq-payment-retry.puml): fino a tre tentativi in caso di errore transitorio;
- [`req-apis.yaml`](../../../caso-guida/req-apis.yaml): `POST /payments` e parametro `Idempotency-Key`.

Confrontare poi con [`expected/review-example.md`](expected/review-example.md). L'esempio mostra una revisione possibile, non la soluzione unica. Una buona analisi distingue ciò che il testo richiede da ciò che sarebbe ragionevole aggiungere alla specifica.

**Reset:** nessuno; lo step è documentale. L'output dello studente può essere conservato fuori dal repository o in una branch personale.
