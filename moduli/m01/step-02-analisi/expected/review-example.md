# Esempio di revisione M01

Il caso felice produce un ordine `PAID` da 20 EUR, ma non prova retry, validazione del prezzo, unicità dell'ordine o corrispondenza completa con OpenAPI.

| Osservazione | Evidenza | Fonte e classificazione | Prossima verifica |
| --- | --- | --- | --- |
| Errore transitorio non ritentato | `transient.gateway_attempts = 1`; in `demo.py` c'è una sola chiamata a `authorize` | **Difetto rispetto alla sequenza**: `req-seq-payment-retry.puml` prescrive fino a tre tentativi per errori transitori | Test con gateway che fallisce una volta e poi approva: attendere due chiamate ed esito positivo |
| Stessa richiesta, due ordini | `repeated.orders = 2`, ID `ord-1` e `ord-2` | **Rischio e decisione aperta**: `req-apis.yaml` descrive `Idempotency-Key` su `POST /payments`, non definisce da sola l'idempotenza dell'intero checkout o di `POST /orders` | Definire ambito e durata della chiave, comportamento su payload diverso e test di ripetizione della richiesta |
| Prezzo alterato accettato | `altered_price.gateway_amount_eur = 1`; `checkout` usa `unit_price_eur` dalla richiesta | **Difetto rispetto al caso d'uso**: `ecomm-requirements.md` richiede pricing validation prima della creazione dell'ordine; valore 20 EUR è solo una fixture sintetica | Test con prezzo client diverso dal prezzo autorevole: rifiuto o ricalcolo documentato |

**Priorità per M03:** esplicitare l'invariante dell'importo e il comportamento della ripetizione dell'intero checkout; mantenere il retry già previsto dalle fonti. Solo dopo chiedere all'agente un piano di implementazione. La review deve citare prove e file, non dichiarare il sistema “sicuro” perché uno scenario passa.
