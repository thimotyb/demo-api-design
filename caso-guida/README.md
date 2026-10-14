# Caso guida: checkout e pagamento

| File | Uso |
| --- | --- |
| [`ecomm-requirements.md`](ecomm-requirements.md) | Casi d'uso, entità e sequenze in forma testuale |
| [`req-seq-checkout-success.puml`](req-seq-checkout-success.puml) | Sequenza di checkout riuscito |
| [`req-seq-payment-retry.puml`](req-seq-payment-retry.puml) | Fino a tre tentativi di autorizzazione per errori transitori |
| [`req-apis.yaml`](req-apis.yaml) | Contratto OpenAPI 3.0.3; `POST /payments` e parametro `Idempotency-Key` |
| Altri `req-*.puml` | Contesto di dominio, casi d'uso e tracking |

**Confine della demo:** si considera solo checkout, autorizzazione, esito e retry. Il gateway è sempre simulato; i prodotti e gli importi usati negli script sono fixture sintetiche introdotte per la lezione, non dati presenti nei requisiti originali. Nel passaggio M01 → moduli successivi il team dovrà decidere e documentare il comportamento di retry dell'intero checkout, la validazione del prezzo e il rapporto tra `Idempotency-Key` dei pagamenti e unicità dell'ordine.
