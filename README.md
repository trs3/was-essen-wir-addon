# Was essen wir? für Home Assistant OS

Gemeinsamer Familien-Essensplan mit Gerichten, Kochhistorie, Einkaufsliste und privatem Apple-Kalender-Abo. Die Anwendung läuft lokal in Home Assistant OS, beispielsweise in einer VM auf Proxmox. Im Betrieb ist keine Cloud-Anbindung nötig.

## Installieren

[![Repository in Home Assistant hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Ftrs3%2Fwas-essen-wir-addon)

Alternativ in **Einstellungen → Apps → App installieren → ⋮ → Repositories** (bei älteren HA-Versionen **Add-ons → Add-on-Store**) diese Adresse hinzufügen:

```text
https://github.com/trs3/was-essen-wir-addon
```

Danach **Was essen wir? → Installieren → Starten**. Den Image-Build abwarten; die VM benötigt dafür Internet, ausreichend RAM und mehrere GB freien Speicher. **Beim Booten starten** aktivieren und **Weboberfläche öffnen** wählen. Direkter Aufruf: `http://IP-DER-HA-VM:3000`.

Beim ersten Öffnen ein gemeinsames Haushalts-Passwort mit mindestens sechs Zeichen setzen. Beide iPhones verwenden dieselbe Serveradresse. Eine bestehende Installation lässt sich über **Historie → JSON-Sicherung herunterladen** und anschließend **Sicherung wiederherstellen** übertragen. Die Sicherung enthält eure privaten Daten und gehört nicht in dieses Repository. In der Zielinstallation einen neuen Kalender-Link erstellen.

## Daten und Updates

Die Daten liegen im dauerhaften privaten App-Verzeichnis `/data`. Bei Home-Assistant-Backups diese App mit auswählen; sie wird während der Sicherung kurz gestoppt. Vor Updates zusätzlich einen JSON-Export herunterladen. Änderungen mit neuer App-Version werden über den Store installiert.

Der Essensplan öffnet ein eigenes Browserfenster und verwendet seinen eigenen Haushaltszugang. Eine bestehende externe Home-Assistant-/Cloud-Adresse stellt den separaten Web-Port nicht automatisch bereit. Für unterwegs ein vorhandenes VPN oder einen HTTPS-Reverse-Proxy verwenden.

Weitere Informationen zu Port, HTTPS, Sicherungen und Fehlerdiagnose: [App-Dokumentation](was_essen_wir/DOCS.md).

## Stand der Prüfung

Das Paket wurde unter Docker Desktop auf Linux arm64 gebaut. Anmeldung, Kalender-Abo und Datenerhalt nach Container-Neustart wurden mit einem isolierten Test-Volume geprüft. Ein Start im echten Home-Assistant-Supervisor sowie ein amd64-Prüflauf stehen noch aus.
