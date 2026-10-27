# Demo — cache HTTP, lavoro lento con `202 Accepted` e load test

Piccola API FastAPI autonoma (dati e job in memoria) che accompagna il modulo M05. Non dipende da M01 né da M02.

| File | Cosa mostra |
| --- | --- |
| [`app/main.py`](app/main.py) | `ETag` e `Cache-Control` su `GET /products/{id}`, risposta `304 Not Modified` a un `If-None-Match` valido; `POST /reports` che risponde `202 Accepted` con `Location` e `Retry-After`, e `GET /reports/{id}` da interrogare |
| [`test_caching.py`](test_caching.py) | L'ETag cambia solo se cambia la risorsa; `304` senza corpo; `If-None-Match` in forma debole, in elenco e `*` |
| [`test_jobs.py`](test_jobs.py) | `202` subito, polling fino a `done`, l'API resta reattiva mentre il report è in corso |
| [`loadtest/locustfile.py`](loadtest/locustfile.py) | Due tipi di utente su `GET /products/1`: uno scarica sempre, l'altro rivalida con l'ETag |
| [`loadtest/run_load.sh`](loadtest/run_load.sh) | Avvia l'API, esegue Locust senza interfaccia e stampa tempi e dimensione del corpo |

## Esecuzione

```bash
./run_all.sh                    # ambiente virtuale, dipendenze e test (11)
./loadtest/run_load.sh          # load test: PORT, USERS e DURATION cambiano porta (8020), utenti (20) e durata (10s)
```

## Cosa aspettarsi dal load test

Su una macchina locale i tempi dei due tipi di utente sono praticamente uguali (circa 7 ms di mediana): la risposta è piccola, l'API non fa lavoro e client e server sono sullo stesso computer. Cambia la dimensione del corpo: l'utente che rivalida riceve `304` senza corpo, quello che scarica ogni volta riceve 72 byte. Il guadagno di una cache HTTP si vede quando il corpo è grande o la rete è lenta, o quando il server esegue una query costosa che il `304` permette di saltare: questa demo non misura nessuno dei due casi.

## Limiti

- I job di `POST /reports` vivono in un `asyncio.Task` nello stesso processo: si perdono al riavvio e con più worker un'altra istanza non vede il job. Un'API reale usa una coda con un processo worker (per esempio Redis) e un database per lo stato.
- Non c'è cancellazione, scadenza dei job né limite sul numero di job in corso.
- La cache è quella del client o di un proxy: il server non conserva nulla. Nessuna cache condivisa (Redis) è inclusa.
- I numeri del load test dipendono dalla macchina: confrontare le due righe tra loro, non leggerli come capacità di un'API reale.
