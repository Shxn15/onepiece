# Grand Line Deal-Scanner (One Piece)

Windows-Programm im One-Piece-Look, das alle One-Piece-Produkte auf Cardmarket nach Angeboten unter Marktwert durchsucht. Mit Filtern für Preis, Rabatt, Foil, Einzelkarten/Sealed, Kategorien (Leader, DON!!, Alt Art, Manga, SP, Promos, Displays …) und einem Klick zu den Live-Angeboten, gefiltert nach Land des Verkäufers, Sprache und Zustand.

## EXE bekommen (über GitHub, wie bei deinem Mod)

1. Neues Repo anlegen (z. B. `op-deal-scanner`) und alle Dateien hochladen, inkl. Ordner `.github/workflows`.
2. Tab **Actions** öffnen → der Build „EXE bauen“ startet automatisch (sonst „Run workflow“).
3. Nach ca. 2 Minuten den fertigen Lauf öffnen → unten bei **Artifacts** `OPDealScanner` herunterladen → ZIP entpacken → `OPDealScanner.exe` starten.

Windows zeigt beim ersten Start evtl. „Der Computer wurde durch Windows geschützt“, weil die EXE nicht signiert ist: **Weitere Informationen → Trotzdem ausführen**.

## Ohne EXE starten

Python von python.org installieren (Häkchen „Add Python to PATH“), dann im Ordner: `python op_deal_scanner.py`

## Bedienung

- Links die Filter einstellen, die Tabelle aktualisiert sich sofort.
- Oben die **Kategorien** anklicken (mehrere möglich). „Alle“ hebt die Auswahl auf.
- Rechts im **Wanted-Steckbrief** stehen die Details der gewählten Karte. Dort stellst du **Land des Verkäufers**, Sprache und Mindestzustand ein.
- **Doppelklick**, Enter oder „Live-Angebote öffnen“ öffnet die aktuellen Angebote auf Cardmarket mit diesen Filtern.
- Gold markiert = mindestens 50 % unter Marktwert.
- Deine Einstellungen bleiben beim nächsten Start erhalten.

## Kategorien und Länder anpassen

Über „Kategorien & Länder bearbeiten“ öffnet sich `%APPDATA%\OPDealScanner\einstellungen.json`. Eine Kategorie ist eine Liste von Suchwörtern (reguläre Ausdrücke) für den Produktnamen, z. B.

```json
"Leader": ["\\bleader\\b"],
"Ruffy": ["luffy"]
```

Speichern, dann im Programm auf „Neu laden“ klicken. Die Kategorien erkennt der Scanner am Produktnamen von Cardmarket, weil die Preisliste keine Seltenheit enthält. Wenn eine Kategorie (vor allem Leader) zu wenig findet, schau dir an, wie Cardmarket diese Karten benennt, und ergänze das Suchwort.
- Die Daten werden einmal pro Tag geladen und zwischengespeichert. „Neu laden“ holt sie erneut.

## Woher die Preise kommen

Cardmarket stellt täglich eine öffentliche Preisliste bereit (günstigstes Angebot, Trend, Durchschnitte). Als Marktwert nutzt der Scanner den kleineren Wert aus Trend und 7-Tage-Schnitt, damit kurzzeitig hochgetriebene Trends keine falschen Deals erzeugen.

**Live-Angebote**: Die Tabelle zeigt den Tagesstand. Die echten, aktuellen Angebote siehst du per Doppelklick direkt auf Cardmarket. Ein automatisches Mitlesen der Angebotsseiten ist nicht eingebaut, weil Cardmarket das in den Nutzungsbedingungen untersagt und es zur Kontosperre führen kann.

Das günstigste Angebot kann eine andere Sprache, ein schlechterer Zustand oder ein Verkäufer mit hohem Versand sein. Vor dem Kauf auf der Seite prüfen.
