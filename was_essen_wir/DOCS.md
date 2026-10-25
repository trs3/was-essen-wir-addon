# Was essen wir? in Home Assistant OS

Diese lokale App (früher „Add-on“) läuft in eurer vorhandenen Home-Assistant-OS-VM auf Proxmox. Sie enthält Weboberfläche und Server. Eine zusätzliche VM wird dafür nicht benötigt. Home Assistant baut das Image bei der Installation selbst; dafür braucht die VM Internet und ausreichend freien Speicher und RAM für einen Node-/Python-Build. Auf kleinen VMs zunächst mindestens 2 GB RAM und mehrere GB freien Speicher vorsehen.

## Installation über GitHub

Im App-/Add-on-Store unter **⋮ → Repositories** die Adresse `https://github.com/trs3/was-essen-wir-addon` hinzufügen. Anschließend **Was essen wir? → Installieren → Starten → Weboberfläche öffnen** wählen und **Beim Booten starten** aktivieren. Der Supervisor baut die enthaltenen Quellen. Die lokale Kopie über Samba ist bei dieser Installationsart nicht erforderlich.

Eine bisherige Installation über deren JSON-Export sichern. In der neuen App einen Haushaltszugang anlegen und unter **Historie → Sicherung wiederherstellen** die Datei auswählen. Daten der Zielinstallation werden dabei ersetzt. Den Kalender-Link in der Zielinstallation neu erstellen.

## Alternative: lokale Installation vom Mac

1. In der bisherigen Essensplan-App unter **Historie** eine JSON-Sicherung herunterladen.
2. Das bereitgestellte ZIP entpacken. Es enthält einen Ordner **was_essen_wir**, in dem direkt `config.json`, `Dockerfile`, `run.py`, `backend/` und `frontend/` liegen.
3. In Home Assistant **Samba share** aus dem App-/Add-on-Store installieren, einen Samba-Benutzerzugang konfigurieren und starten. Im Mac-Finder **Gehe zu → Mit Server verbinden** (`⌘K`) und `smb://homeassistant.local` eingeben; alternativ die IP-Adresse der HA-VM verwenden.
4. Den entpackten Ordner **was_essen_wir** in die Freigabe **local_apps** kopieren. Bei älteren HA-Versionen heißt die Freigabe **addons**. Ergebnis: `local_apps/was_essen_wir/config.json` beziehungsweise `addons/was_essen_wir/config.json`. Nicht nur die ZIP-Datei ablegen und keine zusätzliche Ordnerebene einfügen.
5. In Home Assistant **Einstellungen → Apps → App installieren** öffnen (bei älteren Versionen **Add-ons → Add-on-Store**). Im Menü oben rechts **Nach Updates suchen** wählen und die Seite neu laden. Unter **Lokale Apps / Lokale Add-ons** erscheint **Was essen wir?**.
6. **Installieren** wählen und den Build abwarten. Anschließend **Starten**, **Beim Booten starten** aktivieren und **Weboberfläche öffnen** wählen. Bei Fehlern die App-Protokolle prüfen.
7. Alternativ direkt `http://IP-DER-HA-VM:3000` öffnen. Einen Haushaltszugang mit mindestens sechs Zeichen anlegen und unter **Historie → Sicherung wiederherstellen** die JSON-Datei vom Mac auswählen. Vorhandene Daten der Zielinstallation werden dabei ersetzt. Danach beide iPhones über diese Serveradresse verbinden.

Die Schritte zum lokalen App-Verzeichnis entsprechen der [offiziellen HA-Anleitung](https://contributors.home-assistant.io/apps/first-app/). Die App ist eigenständig erreichbar; ihre Oberfläche wird mit dieser Version in einem eigenen Browserfenster geöffnet. Home-Assistant-Anmeldung und Essensplan-Passwort sind getrennt.

## Zugriff, Kalender und Optionen

Der Standardport ist **3000** auf der IP der HA-VM, nicht der Proxmox-IP. Ist er bereits belegt, im Netzwerkbereich der App einen anderen freien Host-Port für `8000/tcp` einstellen und die App neu starten. Das private Kalender-Abo anschließend in der neuen Installation unter **Historie** neu erstellen und auf den iPhones neu abonnieren. JSON überträgt den Kalender-Schlüssel und das Passwort absichtlich nicht.

Für den HTTP-Zugriff im Heimnetz bleiben die Optionen unverändert:

```yaml
public_origin: ""
cookie_secure: false
```

Für einen bereits vorhandenen HTTPS-Reverse-Proxy zum Web-Port:

```yaml
public_origin: "https://essen.example.net"
cookie_secure: true
```

Die Adresse muss exakt der Browseradresse entsprechen, gegebenenfalls inklusive Port, ohne abschließenden Schrägstrich oder Pfad. Nach Änderungen neu starten. Bei aktivem `cookie_secure` über die HTTPS-Adresse anmelden. Der Button „Weboberfläche öffnen“ führt weiterhin zur lokalen HTTP-Adresse; in diesem Fall stattdessen die HTTPS-Adresse als Lesezeichen verwenden. Eine bestehende externe Home-Assistant-/Cloud-Adresse stellt den separaten Essensplan-Port nicht automatisch bereit. Zugriff unterwegs funktioniert über ein vorhandenes VPN oder einen passend eingerichteten Reverse-Proxy. Die Zeitzone wird wie bisher in der Essensplan-Oberfläche eingestellt.

## Datenspeicherung und Sicherung

Die SQLite-Datenbank liegt im von Home Assistant verwalteten, dauerhaften App-Verzeichnis `/data/essen.sqlite3`. Neustarts und App-Updates behalten dieses Verzeichnis. Die App in Home-Assistant-Sicherungen ausdrücklich mit auswählen; sie wird während ihrer Sicherung kurz gestoppt (`backup: cold`), damit die SQLite-Dateien zusammenpassen. Zusätzlich regelmäßig JSON aus der Oberfläche exportieren. Eine Deinstallation kann die App-Daten löschen; vorher extern sichern. Der Webserver läuft nach der Vorbereitung des Verzeichnisses als Benutzer 10001 und benötigt keinen Zugriff auf Docker oder die Home-Assistant-API.

## Updates und Fehlerdiagnose

Vor Updates eine HA-Sicherung der App und einen JSON-Export erstellen. Das neue vollständige Paket in denselben lokalen App-Ordner kopieren. Im Store nach Updates suchen und das Update installieren. Für neue Paketstände muss die Version in `homeassistant/was_essen_wir/config.json` erhöht werden. Bei unveränderter Version kann die Home-Assistant-Funktion „Neu erstellen/Rebuild“ den lokalen Build wiederholen. Zum Aktualisieren nicht deinstallieren.

Erscheint die App nicht, die Ordnerstruktur prüfen, den Browser neu laden und die Supervisor-Protokolle ansehen. Schlägt der Build fehl, den Fehlertext aus den Supervisor-Protokollen prüfen; häufig fehlen Internet, RAM oder Speicher. Startfehler stehen im App-Protokoll. Bei nicht erreichbarer Weboberfläche IP, Netzwerk-Port und App-Status prüfen.

## Paket aus dem Projekt erzeugen

```sh
python3 scripts/package-homeassistant.py
```

Mit `python3 scripts/package-homeassistant.py --repository` entsteht stattdessen ein ZIP für das GitHub-Repository mit `repository.json` und README im Wurzelverzeichnis. Neue App-Stände benötigen eine höhere Version in `config.json`, damit der Store sie als Update anbietet.

Das ZIP entsteht unter `artifacts/`. Es enthält nur App-Quellen und Installationsdateien, keine Haushaltsdaten, `.env`, Datenbanken oder lokalen Abhängigkeiten. Das Vorlagenverzeichnis `homeassistant/was_essen_wir` allein ist noch kein vollständiges Installationspaket: Das Skript ergänzt darin die aktuellen Backend-/Frontend-Quellen.

Ein isolierter Container-Prüflauf ist mit `./scripts/check-docker.sh --homeassistant` möglich. Er baut aus dem ZIP und prüft Anmeldung, Kalender und Datenerhalt nach Neustart mit eigenem Test-Volume. Er ersetzt keine Installation im echten HA-Supervisor. Die hier tatsächlich ausgeführten Prüfungen stehen im Projekt unter `docs/VALIDIERUNG.md`.
