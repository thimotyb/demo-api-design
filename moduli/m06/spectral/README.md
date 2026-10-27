# Spectral — M06

Questa cartella raccoglie gli export ufficiali di API Stylebook e i comandi per controllare manualmente la specifica [`../../m07/openapi/checkout-api.yaml`](../../m07/openapi/checkout-api.yaml) con tre ruleset:

- OWASP Top 10;
- URL Style Guidelines;
- Documentation.

## Preparazione

Da questa cartella installare le dipendenze (Node.js 20 o successivo):

```bash
npm install
```

La versione della CLI è fissata in `package.json` e `package-lock.json`. Gli export dei ruleset sono salvati in `rulesets/exported/`, ciascuno con il proprio `.spectral.json` e con le eventuali funzioni ausiliarie.

## Esportare i ruleset da API Stylebook

Gli export originali dei tre style guide sono già salvati in `rulesets/exported/`. Per ripetere il prelievo o aggiornare i file:

1. Aprire lo style guide in [API Stylebook](https://apistylebook.stoplight.io/): [OWASP Top 10](https://apistylebook.stoplight.io/docs/owasp-top-10), [URL Style Guidelines](https://apistylebook.stoplight.io/docs/url-guidelines) o [Documentation](https://apistylebook.stoplight.io/docs/documentation).
2. Nel menu in alto a destra scegliere **Export → Spectral File(s)**. Il browser scarica uno ZIP.
3. Estrarre tutto il contenuto dello ZIP nella cartella omonima sotto `rulesets/exported/`, sovrascrivendo i file precedenti. Conservare `.spectral.json` e la cartella `functions/` quando presenti: il ruleset li usa con percorsi relativi.
4. Il file principale si chiama `.spectral.json`; dalla cartella `spectral/` si può eseguire il singolo export così:

```bash
npx spectral lint ../../m07/openapi/checkout-api.yaml --ruleset rulesets/exported/owasp-top-10/.spectral.json
npx spectral lint ../../m07/openapi/checkout-api.yaml --ruleset rulesets/exported/url-style-guidelines/.spectral.json
npx spectral lint ../../m07/openapi/checkout-api.yaml --ruleset rulesets/exported/documentation/.spectral.json
```

Gli export sono stati scaricati il 7 ottobre 2026. Per aggiornare la demo in modo riproducibile, riscaricare i file con la stessa procedura e verificare il diff prima di sostituirli.

## Avviare i tre controlli

Dalla cartella `spectral/`:

```bash
./lint.sh
```

Lo script esegue tutti e tre gli export anche quando un ruleset trova errori; termina con codice `1` se almeno una verifica contiene errori. Baseline verificata sul contratto demo: OWASP Top 10 segnala 60 errori e 42 avvisi; URL Style Guidelines 2 errori, 3 avvisi e 1 informazione; Documentation 42 avvisi e nessun errore. Le segnalazioni sono materiale di analisi: valutarle rispetto al contratto e agli scenari, senza modificare API o regole solo per ottenere un esito senza findings.

Oppure eseguire i controlli separatamente:

```bash
npx spectral lint ../../m07/openapi/checkout-api.yaml --ruleset rulesets/exported/owasp-top-10/.spectral.json
npx spectral lint ../../m07/openapi/checkout-api.yaml --ruleset rulesets/exported/url-style-guidelines/.spectral.json
npx spectral lint ../../m07/openapi/checkout-api.yaml --ruleset rulesets/exported/documentation/.spectral.json
```
