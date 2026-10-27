# Demo — un trace OpenTelemetry da GraphQL a REST in Jaeger

La demo mostra che una richiesta GraphQL diventa un solo trace che attraversa due servizi: l'API GraphQL e l'API REST di [M01](../../m01/README.md), che l'API GraphQL chiama con `httpx`. Il codice di M01 non viene modificato: `opentelemetry-instrument` aggiunge gli span dall'esterno.

| File | Funzione |
| --- | --- |
| [`docker-compose.yml`](docker-compose.yml) | Jaeger all-in-one: interfaccia web su `16686`, ricezione OTLP/HTTP su `4318` |
| [`run.sh`](run.sh) | Avvia Jaeger e le due API (`checkout-rest`, `checkout-graphql`) con l'auto-instrumentation |
| [`scenario.sh`](scenario.sh) | Tre richieste GraphQL: lettura di un ordine, pagamento rifiutato, guasto transitorio con retry |
| [`test_tracing.py`](test_tracing.py) | Verifica senza Docker che il trace attraversi le due API |

## Avvio

```bash
./run.sh            # in un terminale: Jaeger e le due API (REST_PORT e GRAPHQL_PORT cambiano le porte 8000 e 8001)
./scenario.sh       # in un altro terminale
```

Aprire <http://localhost:16686>, scegliere il servizio `checkout-graphql` e cercare i trace. In quello della prima richiesta si vedono lo span del server GraphQL, tre chiamate `httpx` (ordine, cliente, spedizione) e sotto ciascuna lo span del server `checkout-rest`. Nel trace del pagamento rifiutato la chiamata `httpx` verso `/v1/payments` è marcata come errore (risposta `402`). Il guasto transitorio con `tok_flaky` si presenta solo la prima volta dopo l'avvio dell'API REST.

Con `OTEL_PYTHON_LOG_CORRELATION=true` i log dello standard `logging` riportano `trace_id` e `span_id`: lo stesso `trace_id` compare nei log di `checkout-graphql` e di `checkout-rest`, e permette di passare dal trace ai log.

## Verifica senza Docker

```bash
cd ../../m01 && python -m pytest ../m04/demo-tracing
```

Il test avvia l'API REST in un vero server uvicorn, strumenta le due API e raccoglie gli span in memoria. Controlla che le chiamate REST abbiano lo stesso `trace_id` della richiesta GraphQL e come genitore uno span client `httpx`, e che un rifiuto `402` marchi lo span client come errore.

## Limiti

- Gli span arrivano a Jaeger con un esportatore OTLP in batch: possono comparire dopo qualche secondo.
- L'interfaccia di Jaeger non è coperta dal test. La demo è stata provata a mano con Jaeger 1.62.0 in Docker: due servizi, quattro trace, errori sullo span client dei pagamenti con risposta `402`.
- Il campionamento è quello predefinito (tutto): in produzione si campiona.
- Nessun dato sensibile negli attributi degli span; l'auto-instrumentation registra metodo, URL e status, non il corpo delle richieste.
- Le metriche e il collector OpenTelemetry non sono coperti.
