# Prompt opzionale per la dimostrazione live

Questo prompt serve a mostrare quanto contesto manchi in una richiesta di *vibe coding*. Eseguirlo in una cartella di prova separata, con Codex o Claude Code, **senza** copiare nel prompt i requisiti e il contratto del caso guida. L'output dipende dal modello e dalla sessione: il prototipo versionato in [`demo.py`](demo.py) resta il riferimento riproducibile della lezione.

> Vorrei un checkout molto semplice per un negozio online. L'utente ha un carrello, paga e riceve una conferma dell'ordine. Crea un piccolo prototipo eseguibile con un pagamento simulato.

Dopo la generazione, chiedere all'agente quali assunzioni ha fatto su prezzo, retry, richieste ripetute, stato dell'ordine e test. Confrontarle con [`ecomm-requirements.md`](../../../caso-guida/ecomm-requirements.md), [`req-seq-payment-retry.puml`](../../../caso-guida/req-seq-payment-retry.puml) e [`req-apis.yaml`](../../../caso-guida/req-apis.yaml). Non usare il codice generato live come soluzione di riferimento: salvarne soltanto il diff e le assunzioni per la discussione.
