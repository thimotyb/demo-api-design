# M04 — architecture

## Obiettivo

Ricavare una vista dei componenti e una vista ArchiMate a tre livelli dai requisiti e confrontarle con le sequenze PlantUML e con il contratto OpenAPI. Gli artefatti sono proposte didattiche, non documentazione di un sistema già costruito.

## Sorgenti e risultati

- `architecture-requirements.md`: requisiti con ID stabili, qualità, vincoli e decisioni aperte.
- `architecture-view.puml` → `architecture-view.svg`: componenti, dipendenze, API OAS e chiamate interne.
- `archimate-view.puml` → `archimate-view.svg`: processi business, servizi/componenti applicativi e tecnologia.
- Requisiti originali: `../../../caso-guida/ecomm-requirements.md`, sequenze `../../../caso-guida/req-seq-*.puml`, contratto `../../../caso-guida/req-apis.yaml`.

## Flusso della demo

1. Leggere gli input e identificare responsabilità, dipendenze esterne e ordine delle interazioni.
2. Chiedere a Codex o Claude Code di proporre prima gli ID dei requisiti; far revisionare il testo prima dei diagrammi.
3. Generare i due sorgenti `.puml` preservando gli ID e distinguendo endpoint OAS da messaggi interni.
4. Confrontare componenti e relazioni con la matrice sottostante e le sequenze originali.
5. Renderizzare i diagrammi, correggere errori di sintassi e verificare che le etichette restino leggibili.
6. Registrare le decisioni che richiedono un proprietario; non trasformare assunzioni in vincoli approvati.

### Prompt riutilizzabile

> Leggi `architecture-requirements.md`, `../../../caso-guida/req-seq-checkout-success.puml`, `../../../caso-guida/req-seq-payment-retry.puml` e `../../../caso-guida/req-apis.yaml`. Proponi un diagramma di componenti e una vista ArchiMate con livelli Business giallo, Application azzurro e Technology verde. Mantieni gli ID AR/QI/VIN; indica a quali ID risponde ogni elemento e relazione. Usa come API pubbliche solo i path e i metodi esistenti nell'OAS. Etichetta `Cart.total()` e `createShipment(orderId)` come chiamate interne: non inventare endpoint per rappresentarle. Marca runtime, persistenza e deployment come decisioni aperte. Prima elenca incongruenze o ambiguità; poi crea i sorgenti `.puml` e verifica il rendering.

## Matrice di tracciabilità

| Requisito | Elementi / relazioni architetturali | API o sequenza di verifica |
| --- | --- | --- |
| AR-01, QI-01 | BP-01; AS-01; Checkout Orchestrator → Cart, Payment, Order, Shipment | Sequenza `req-seq-checkout-success.puml`; `POST /payments`, `POST /orders`; `Cart.total()` resta interno |
| AR-02, QI-02 | BP-02; AS-03; Payment Service → Payment Gateway | `POST /payments`, header `Idempotency-Key`; sequenza `req-seq-payment-retry.puml` |
| AR-03 | BP-01; AS-04; Order Service; relazione di creazione dopo autorizzazione | `POST /orders`; risposta `PAID` nella sequenza di successo |
| AR-04 | BP-01; Shipment Service invocato dopo `POST /orders` | `createShipment(orderId)` è nel diagramma di sequenza ma non ha un endpoint OAS |
| AR-05 | BP-03; AS-05/AS-06; Shipment Service → Carrier API | `GET /orders/{orderId}/shipment`, `GET /orders/{orderId}`, `GET /customers/{customerId}/orders` |
| AR-06, QI-03 | VIN-02 e legenda; identificazione distinta delle API contrattuali e interazioni interne | Ogni metodo/path elencato è verificabile in `req-apis.yaml` |
| AR-07 | Payment Gateway e Carrier API nel confine esterno; simulatori sostituibili | Requisiti dominio e sequenza; provider reale fuori dallo scope demo |
| VIN-01 | TS-04 indica scelte non definite, senza fissare tecnologia o deployment | Decisioni aperte in `architecture-requirements.md` |

## Rendering e controllo

Con Java, Graphviz e PlantUML installati. I rendering versionati sono stati generati con PlantUML 1.2026.8:

```bash
plantuml -version
plantuml -tsvg architecture-view.puml archimate-view.puml
```

Controllare che entrambi gli SVG esistano e non contengano una pagina di errore PlantUML. Aprire i rendering a dimensione naturale, verificare etichette e colori e confrontarli con la matrice. Le figure del sito sono copie dei rendering in `site/assets/`.

## Reset

La modifica ai sorgenti si annulla ripristinando i tre input versione: `architecture-requirements.md`, `architecture-view.puml` e `archimate-view.puml`. I file SVG si rigenerano dal sorgente con il comando sopra.

## Decisioni ancora aperte

Le viste non scelgono microservizi rispetto a moduli in un'applicazione unica, motore di persistenza, protocolli interni, deployment, SLA, autenticazione di produzione o strategia di consistenza. `req-apis.yaml` non definisce l'operazione che crea la spedizione: questa resta una chiamata interna ipotizzata dalla sequenza, da precisare prima dell'implementazione.
