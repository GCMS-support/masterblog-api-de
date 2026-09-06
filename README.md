# Masterblog API

Eine vollständige Flask-REST-API mit getrenntem Demo-Frontend. Das Projekt entstand für die Masterschool-Aufgabe **Masterblog API DE** und enthält alle Pflicht- und Bonusfunktionen.

## Funktionsumfang

- Beiträge auflisten sowie einzelne Beiträge abrufen
- Beiträge anlegen, teilweise aktualisieren und löschen
- Pflichtfelder und Datumsformat validieren
- Suche ohne Beachtung der Groß-/Kleinschreibung
- Sortierung nach Titel, Inhalt, Autor oder Datum
- Erweiterte Felder **author** und **date**
- Persistenter, atomarer JSON-Speicher in `backend/posts.json`
- Verständliche JSON-Fehler bei ungültigen Anfragen oder Speicherproblemen
- Interaktive Swagger-UI unter `/api/docs/`
- Responsive Demo-Oberfläche mit Suche, Sortierung, Autor und Datum
- Automatisierte Tests mit temporärem Speicher

## Installation und Start

```bash
python3 -m pip install -r requirements.txt
python3 backend/backend_app.py
```

Das Backend läuft auf **Port 5002**. Die API-Basis-URL ist `http://127.0.0.1:5002/api`; die Swagger-Dokumentation ist unter `http://127.0.0.1:5002/api/docs/` erreichbar.

Für das getrennte Frontend in einem zweiten Terminal:

```bash
python3 frontend/frontend_app.py
```

Das Frontend läuft auf **Port 5001**. Bei einer entfernten Codio-Umgebung muss im Frontend die von Codio bereitgestellte API-URL eingetragen werden.

## Endpunkte

| Methode | Pfad | Zweck |
| --- | --- | --- |
| GET | `/api/posts` | Liste, optional mit `search`, `sort` und `direction` |
| POST | `/api/posts` | Beitrag erstellen |
| GET | `/api/posts/search` | Suche über `search`, `title` oder `content` |
| GET | `/api/posts/<id>` | Einzelnen Beitrag abrufen |
| PUT | `/api/posts/<id>` | Einzelne Felder eines Beitrags ändern |
| DELETE | `/api/posts/<id>` | Beitrag löschen |
| GET | `/api/docs/` | Swagger-UI öffnen |

Ein neuer Beitrag benötigt `title` und `content`. `author` wird ohne Angabe zu `Anonymous`, `date` zum heutigen Datum im Format `YYYY-MM-DD`.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Die Tests verändern `backend/posts.json` nicht: Jeder Test nutzt eine eigene temporäre JSON-Datei.

## Projektstruktur

```text
backend/
  backend_app.py          Flask-API
  posts.json              persistente Beispieldaten
  static/masterblog.json  OpenAPI-/Swagger-Spezifikation
frontend/
  frontend_app.py         Demo-Webserver
  templates/index.html    Benutzeroberfläche
  static/main.js          API-Integration
  static/styles.css       responsives Layout
tests/
  test_backend.py         API- und Frontend-Smoke-Tests
```
