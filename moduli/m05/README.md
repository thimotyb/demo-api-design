# M05 — Contratto OpenAPI

**Stato: demo API/Postman implementata per mock locale; lo step include anche i comandi Spectral per OWASP Top 10, URL Style Guidelines e Documentation.**

**Obiettivo previsto:** Ridurre e verificare il contratto della fetta verticale, applicare regole di API Governance, documentare esempi OpenAPI da servire come risposte fisse in uno stub e costruire test funzionali riproducibili dal caso guida in [caso-guida](../../caso-guida/README.md).

| Step | Input previsto | Output previsto |
| --- | --- | --- |
| [step-01-contratto](step-01-contratto/README.md) | Requisiti, diagrammi e contratto OAS ridotto derivato | [Playbook Postman](step-01-contratto/postman/checkout-sequence-playbooks.postman_collection.json), mock Prism locale, verifica Newman e istruzioni per i ruleset Spectral |

Lo step prepara un profilo OAS dalla fetta del contratto `caso-guida/req-apis.yaml`, aggiunge esempi nominati per richieste e risposte, rende obbligatoria `Idempotency-Key` per i playbook di retry e genera la collection dalla mappa `scenarios/postman-playbooks.yaml`. Il generatore verifica che ogni path/metodo del profilo esista nel contratto sorgente, che le risposte abbiano esempi e che ogni `operationId`/esempio usato dal playbook esista nella specifica.

**Scenari inclusi:** checkout autorizzato; due errori transitori e successiva autorizzazione; esaurimento dei tre tentativi; rifiuto definitivo senza richiesta di ordine; consultazione tracking. I retry ripetono `POST /payments` con la stessa chiave come richiesto dal contratto. Prism seleziona le risposte fisse tramite `Prefer`; pertanto il playbook mostra il flusso HTTP ma non verifica il comportamento stateful di un backend, la deduplicazione idempotente o il contatore interno delle chiamate al gateway.

Bruno CLI e Schemathesis restano possibili estensioni; JMeter è riservato al carico. Nessuna credenziale o transazione reale è usata: il bearer token è una fixture locale destinata a Prism.
