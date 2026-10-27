# Requisiti architetturali — checkout e pagamento

Questa fonte raccoglie requisiti e assunzioni per le viste di M06. È limitata alla fetta checkout, autorizzazione del pagamento e avvio spedizione del [caso guida](../../../caso-guida/README.md). I diagrammi sono proposte logiche da revisionare: non descrivono un sistema già implementato.

## Obiettivo e confini

Il cliente conferma il checkout; l'applicazione calcola il totale del carrello, chiede l'autorizzazione del pagamento, crea l'ordine solo dopo l'esito positivo e avvia la spedizione. Il cliente può inoltre consultare ordine e tracking. Il gateway di pagamento e il sistema del corriere sono esterni e simulati nei laboratori.

## Requisiti stabili

| ID | Requisito | Evidenza sorgente |
| --- | --- | --- |
| AR-01 | Il checkout coordina totale del carrello, autorizzazione, creazione dell'ordine e richiesta di avvio spedizione nell'ordine previsto dalla sequenza di successo. | `caso-guida/req-seq-checkout-success.puml` |
| AR-02 | Un errore transitorio di autorizzazione può essere ritentato fino a tre volte; al successo il ciclo termina, dopo tre fallimenti il cliente riceve un esito di errore. La chiave di idempotenza è usata quando si ripete una richiesta, secondo il contratto API. | `caso-guida/req-seq-payment-retry.puml`, `caso-guida/req-apis.yaml` |
| AR-03 | La creazione dell'ordine usa il riferimento al pagamento autorizzato; l'ordine della sequenza di successo è restituito come `PAID`. | `caso-guida/req-seq-checkout-success.puml`, `caso-guida/req-apis.yaml` |
| AR-04 | Dopo il piazzamento dell'ordine, la sequenza di successo richiede la creazione della spedizione e restituisce un codice di tracking al cliente. | `caso-guida/req-seq-checkout-success.puml` |
| AR-05 | La consultazione dello stato dell'ordine e dei dettagli di spedizione usa le operazioni definite nel contratto; l'aggiornamento di tracking proviene dal sistema esterno del corriere. | `caso-guida/req-seq-order-tracking.puml`, `caso-guida/req-apis.yaml`, `caso-guida/ecomm-requirements.md` |
| AR-06 | Le interfacce HTTP mostrate come API pubbliche devono corrispondere a operazioni presenti in `caso-guida/req-apis.yaml`. I messaggi interni delle sequenze non diventano endpoint HTTP per supposizione. | `caso-guida/req-apis.yaml` e diagrammi di sequenza |
| AR-07 | Gateway di pagamento e API del corriere restano dipendenze esterne; la loro sostituzione o simulazione non cambia il flusso applicativo presentato al cliente. | `caso-guida/ecomm-requirements.md` |

## Attributi di qualità e vincoli

- **QI-01 — coerenza del flusso:** mantenere l'ordine di AR-01 e impedire che l'ordine venga piazzato prima dell'autorizzazione (AR-03).
- **QI-02 — resilienza controllata:** limitare i retry come in AR-02 e usare la chiave di idempotenza prevista dal contratto.
- **QI-03 — tracciabilità:** collegare ogni componente e relazione architetturale a uno o più ID in questa tabella e, per gli endpoint, al path OAS.
- **VIN-01 — perimetro:** le viste sono logiche. Linguaggio/runtime, protocollo interno, database, cloud, deployment, SLA e strategia di consistenza non sono definiti dai requisiti sorgente e rimangono decisioni aperte.
- **VIN-02 — API:** sono endpoint contrattuali solo quelli elencati nella matrice nel README dello step. `Cart.total()` e `createShipment(orderId)` sono interazioni interne tratte dalla sequenza, non endpoint presenti nell'OAS.

## Decisioni aperte

1. Il sistema è distribuito in servizi indipendenti o in moduli di un'applicazione unica?
2. Quale componente persiste ordini, pagamenti e spedizioni e quale strategia garantisce coerenza tra queste scritture?
3. Chi crea materialmente la spedizione e con quale interfaccia interna? L'OAS attuale espone la lettura del tracking, non un endpoint di creazione spedizione.
4. Quali autenticazione, autorizzazione, timeout e soglie di disponibilità sono richiesti in produzione?
5. Quali chiamate esterne possono essere ripetute in sicurezza oltre all'autorizzazione del pagamento?

Non assumere risposte a queste domande nelle viste; identificarle come punti da decidere nel progetto reale.
