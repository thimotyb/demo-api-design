# M03 — step 02: specificare il retry con GitHub Spec Kit

## Obiettivo

Applicare un processo SDD strutturato allo stesso caso checkout e retry usato in M01 e M02. Il risultato è un insieme collegato di artefatti Markdown, costruito prima del codice:

- [constitution](specifiche-speckit/.specify/memory/constitution.md): principi che vincolano tutto il lavoro;
- [spec](specifiche-speckit/specs/001-payment-retry/spec.md): comportamento richiesto e criteri di accettazione;
- [plan](specifiche-speckit/specs/001-payment-retry/plan.md): approccio tecnico per una demo locale;
- [checklist](specifiche-speckit/specs/001-payment-retry/checklists/requirements.md): revisione della qualità dei requisiti;
- [tasks](specifiche-speckit/specs/001-payment-retry/tasks.md): lavoro ordinato e legato ai requisiti;
- [decision log](specifiche-speckit/specs/001-payment-retry/decisions.md): questioni che il team deve risolvere.

Il pacchetto è una fotografia didattica degli artefatti attesi. La mini demo [demo-retry](demo-retry/README.md) aggiunge uno starter Python con test mirati, così il flusso può arrivare a `implement` e `converge` in un workspace separato. Le decisioni su idempotenza API e ripetizione del checkout restano fuori da questo piccolo cambiamento.

## Spec Kit

- [Documentazione ufficiale e flusso SDD](https://github.github.com/spec-kit/)
- [Repository ufficiale GitHub](https://github.com/github/spec-kit)
- [Quickstart SDD](https://github.github.io/spec-kit/quickstart.html)
- [Metodologia Spec-Driven Development](https://github.com/github/spec-kit/blob/main/spec-driven.md)
- [Integrazioni e sintassi dei comandi](https://github.com/github/spec-kit/blob/main/docs/reference/integrations.md)

Il flusso completo documentato è: `constitution` una volta per il progetto, poi `specify → clarify → plan → checklist → tasks → analyze → implement → converge`. Ogni comando è un passo guidato dall'agente, non un comando da shell. Codex usa le skill `$speckit-*`; Claude Code usa le skill `/speckit-*`. La forma disponibile dipende dall'integrazione configurata: verificare i file installati e la guida ufficiale.

`analyze` è una verifica di sola lettura tra gli artefatti. La mini demo prosegue poi con `implement` e `converge`, ma solo sul piccolo ciclo di retry simulato: le decisioni su chiavi API, timeout e checkout ripetuto rimangono fuori scope.

## Prerequisiti

- Clone del repository demo e accesso ai file in `caso-guida/`.
- Codex CLI oppure Claude Code configurato con un modello disponibile.
- Per la riproduzione live: Python con `uv` e il CLI `specify` installabile. Il solo confronto degli artefatti versionati non richiede installazioni o rete.

## Riproduzione live in un'area temporanea

Eseguire dalla radice del clone. L'area temporanea tiene separati i file generati dal repository del corso; il caso guida originale viene copiato solo lì.

```bash
DEMO_REPO="$(pwd)"
WORK_ROOT="$(mktemp -d)"
uv tool install specify-cli
cd "$WORK_ROOT"
specify init checkout-retry --integration claude --script py
mkdir -p checkout-retry/inputs
cp "$DEMO_REPO/caso-guida/ecomm-requirements.md" checkout-retry/inputs/
cp "$DEMO_REPO/caso-guida/req-seq-payment-retry.puml" checkout-retry/inputs/
cp "$DEMO_REPO/caso-guida/req-seq-checkout-success.puml" checkout-retry/inputs/
cp "$DEMO_REPO/caso-guida/req-apis.yaml" checkout-retry/inputs/
cp "$DEMO_REPO/moduli/m01/step-01-prototipo/demo.py" checkout-retry/inputs/prototype-demo.py
cp "$DEMO_REPO/moduli/m03/step-02-speckit/demo-retry/payment_retry.py" checkout-retry/
cp "$DEMO_REPO/moduli/m03/step-02-speckit/demo-retry/test_payment_retry.py" checkout-retry/
cd checkout-retry
claude
```

La schermata di riferimento mostra proprio l'inizializzazione con Claude Code e script Python. Per provare Codex, creare un secondo workspace con `specify init checkout-retry --integration codex --script py`, copiare gli stessi input e avviare `codex`. Non inizializzare entrambe le integrazioni nello stesso workspace durante questo confronto.

In chat, invocare un passo alla volta usando la sintassi che l'integrazione ha installato:

1. **Constitution:** usare [`prompt-constitution.md`](prompt-constitution.md); chiedere che l'agente citi i file in `inputs/`, mantenga distinta evidenza e ipotesi, usi solo gateway simulati e non implementi decisioni aperte.
2. **Specify:** usare [`prompt-specify.md`](prompt-specify.md). Chiedere requisiti e scenari osservabili senza scegliere librerie o struttura tecnica.
3. **Clarify:** usare [`prompt-clarify.md`](prompt-clarify.md). Limitare questa demo ai tre scenari espliciti; registrare le altre domande senza inventare risposte.
4. **Plan:** usare [`prompt-plan.md`](prompt-plan.md), limitando il piano alla simulazione Python locale e ai comportamenti già approvati.
5. **Checklist e tasks:** eseguire i comandi, verificare che ogni requisito abbia una verifica e ogni task rimandi a un requisito. Spuntare la checklist solo dopo la review umana; gli item non pertinenti alla mini demo restano esclusi dal lavoro.
6. **Analyze:** eseguire il controllo tra `spec.md`, `plan.md` e `tasks.md`; correggere gli artefatti e ripetere finché non restano incongruenze non spiegate.
7. **Implement:** eseguire i task limitati al modulo `payment_retry.py`; i test automatici verificano i tre scenari della specifica.
8. **Converge:** chiedere all'agente di confrontare codice e test con `spec.md`, `plan.md` e `tasks.md`, correggendo le lacune che riguardano l'ambito approvato.

## Confronto con gli artefatti di riferimento

Confrontare i file generati dall'agente con [`specifiche-speckit/`](specifiche-speckit/). Registrare:

1. quali requisiti vengono dalle fonti e quali sono proposte;
2. quali ambiguità emergono durante `clarify`;
3. se `plan.md` introduce dettagli prematuri o scelte non approvate;
4. se i task sono tracciabili ai requisiti e verificabili;
5. se `analyze` trova discrepanze che la review umana aveva trascurato.

Il risultato atteso non è la corrispondenza letterale con il testo di riferimento: è la tracciabilità, con le questioni aperte visibili e senza contraddizioni nascoste. L'analisi automatica non sostituisce la review delle fonti.

## Verifica e reset

Eseguire i test prima e dopo l'implementazione seguendo [le istruzioni di demo-retry](demo-retry/README.md). Controllare manualmente che `decisions.md` non abbia decisioni aperte trasformate in requisiti. La demo non modifica il codice M01 e non invoca gateway esterni.

Per ripetere il flusso, inizializzare un nuovo workspace temporaneo. Per eliminare quello della prova, usare il percorso stampato da `mktemp` e rimuovere solo quella directory temporanea dopo aver conservato gli artefatti utili.
