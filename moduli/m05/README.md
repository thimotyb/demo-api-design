# M05 — Contratto OpenAPI

**Stato: demo API/Postman implementata per mock locale; include anche i comandi Spectral per OWASP Top 10, URL Style Guidelines e Documentation.**

**Obiettivo:** Ridurre e verificare il contratto della fetta verticale, applicare regole di API Governance, documentare esempi OpenAPI da servire come risposte fisse in uno stub e costruire test funzionali riproducibili dal caso guida in [caso-guida](../../caso-guida/README.md).

Il modulo prepara un profilo OAS dalla fetta del contratto `caso-guida/req-apis.yaml`, aggiunge esempi nominati per richieste e risposte, rende obbligatoria `Idempotency-Key` per i playbook di retry e genera la collection dalla mappa `scenarios/postman-playbooks.yaml`. Il generatore verifica che ogni path/metodo del profilo esista nel contratto sorgente, che le risposte abbiano esempi e che ogni `operationId`/esempio usato dal playbook esista nella specifica.

**Scenari inclusi:** checkout autorizzato; due errori transitori e successiva autorizzazione; esaurimento dei tre tentativi; rifiuto definitivo senza richiesta di ordine; consultazione tracking. I retry ripetono `POST /payments` con la stessa chiave come richiesto dal contratto. Prism seleziona le risposte fisse tramite `Prefer`; pertanto il playbook mostra il flusso HTTP ma non verifica il comportamento stateful di un backend, la deduplicazione idempotente o il contatore interno delle chiamate al gateway.

Bruno CLI e Schemathesis restano possibili estensioni; JMeter è riservato al carico. Nessuna credenziale o transazione reale è usata: il bearer token è una fixture locale destinata a Prism.

## Materiali

- Input: requisiti, sequence diagram e contratto sorgente [`req-apis.yaml`](../../caso-guida/req-apis.yaml).
- Contratto demo: [`openapi/checkout-api.yaml`](openapi/checkout-api.yaml), profilo derivato con esempi nominati.
- Mappa scenario/diagramma/operazioni: [`scenarios/postman-playbooks.yaml`](scenarios/postman-playbooks.yaml).
- Collection generata: [`postman/checkout-sequence-playbooks.postman_collection.json`](postman/checkout-sequence-playbooks.postman_collection.json).

### Esecuzione

Prerequisiti: Node.js 20 o successivo, Python 3.10 o successivo, `pip`, `curl`. Dalla cartella di questo modulo:

```bash
python3 -m pip install -r requirements.txt
npm install
npm run generate
npm run test:playbooks
```

`npm run test:playbooks` avvia Prism sul loopback, esegue la collection con Newman e arresta il mock anche in caso di errore. In alternativa, importa il JSON della collection in Postman e avvia il mock separatamente con `npx prism mock openapi/checkout-api.yaml --host 127.0.0.1 --port 4010`.

Prism resta in ascolto su `127.0.0.1`; il bearer token e i dati sono fixture didattiche. Le dipendenze npm sono strumenti di sviluppo: controllare gli advisory transitive prima di usarle con collection non fidate o di esporre il mock in rete.

Per rigenerare il file Postman dopo aver cambiato la specifica o lo YAML dei playbook, eseguire `npm run generate`. La collection non va modificata a mano: la sorgente degli scenari è `scenarios/postman-playbooks.yaml`, mentre payload e risposte provengono dagli esempi nominati in OpenAPI.

### Verifica API Governance con Spectral

La cartella [`spectral/`](spectral/README.md), accanto a `openapi/` e `postman/`, contiene i ruleset, i comandi e la procedura per esportare i file ufficiali da API Stylebook. I tre controlli coprono OWASP Top 10, URL Style Guidelines e Documentation.

### Confini della copertura

- Il sequence diagram checkout include `createShipment`, ma l'OAS sorgente espone solo `GET /orders/{orderId}/shipment`: la collection non inventa un `POST` e segnala il gap.
- Il diagramma di retry descrive chiamate interne Web Application → Gateway. La collection rappresenta i tentativi al confine `POST /payments`; con risposte Prism fissate e stateless non prova il retry interno, il contatore effettivo, né la deduplicazione server-side della `Idempotency-Key`.
- Il ramo fallito termina senza `POST /orders`. Il contratto non espone una query per verificare l'assenza persistita dell'ordine; per questo serve un test d'integrazione sul backend quando disponibile.

### Tracciabilità sequence diagram → operazioni

| Diagramma | Passo osservabile | Operazione del profilo OAS | Playbook / limite |
| --- | --- | --- | --- |
| `req-seq-checkout-success.puml` | `authorize(amount, token)` | `POST /payments` | Fixture `authorized`; importo e customer sono esempi del contratto |
| `req-seq-checkout-success.puml` | `placeOrder(cartSnapshot, paymentId)` | `POST /orders` | Usa il `paymentId` estratto dalla risposta precedente |
| `req-seq-checkout-success.puml` | `createShipment(orderId)` | Nessuna operazione corrispondente | Gap OAS esplicito; il playbook non inventa un endpoint POST |
| `req-seq-payment-retry.puml` | Autorizzazione con retry fino a tre tentativi | `POST /payments` ripetuta con `Idempotency-Key` costante | Prism restituisce esempi prescritti; la collection non misura retry interni né idempotenza server-side |
| `req-seq-order-tracking.puml` | `getOrder(orderId)` | `GET /orders/{orderId}` | Estrae `orderId` e `trackingCode` dal fixture |
| `req-seq-order-tracking.puml` | `getShipment(trackingCode)` | `GET /orders/{orderId}/shipment` | Il contratto sceglie `orderId`; la richiesta interna al Carrier API resta fuori dall'API pubblica |

Questa matrice rende visibile dove la specifica copre la sequenza e dove serve un contratto aggiornato o un test d'integrazione. I valori del mock sono fissi per ripetere la demo; non rappresentano persistenza o comportamento del servizio reale.

Riferimento comune: [caso guida](../../caso-guida/README.md).
