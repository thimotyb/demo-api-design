# M04 — Progettazione e PlantUML

**Stato: demo eseguibile.** Il laboratorio parte dai requisiti architetturali del checkout e produce due viste logiche con AI, poi le revisiona rispetto alle sequenze e al contratto OpenAPI del caso guida.

| Cartella | Input | Risultato |
| --- | --- | --- |
| [demo-retry](demo-retry/README.md) | Requisito di retry sui pagamenti | Mini demo Python con test: lo starter fallisce due test, la soluzione di riferimento li supera |
| [architecture](architecture/README.md) | Requisiti, sequenze e OpenAPI | Requisiti architetturali versionati, diagramma componenti, vista ArchiMate business/applicazione/tecnologia e matrice di tracciabilità |

La cartella contiene la fonte `architecture-requirements.md`, i sorgenti `.puml` e i rendering SVG. Il diagramma architetturale esplicita le API del contratto e separa le chiamate interne; la vista ArchiMate collega processi, servizi e componenti. Le allocazioni sono una proposta logica: i requisiti non fissano microservizi, runtime, database o deployment.

Per rigenerare le viste, installare Java e PlantUML, entrare in `architecture/` ed eseguire:

```bash
plantuml -tsvg architecture-view.puml archimate-view.puml
```

Sintassi: [supporto ArchiMate di PlantUML](https://plantuml.com/archimate-diagram).
