# 1.4.0

- In der Historie öffnet „Ändern“ die Erfassung. „Nichts“ unter „Als gekocht speichern“ markiert einen Tag als „Nichts gekocht“, auch zur Korrektur vorhandener Kochereignisse.
- Die ursprüngliche Planung bleibt unter „Eigentlich war geplant: …“ sichtbar; „Nichts gekocht“ zählt nicht für die Kochstatistik.
- Schema-Version 4 speichert die ursprüngliche Gerichtsauswahl freier Tage. Vollständige JSON-Sicherungen erhalten diese Angabe; ältere Sicherungen bleiben wiederherstellbar.
- Erneut eingeplante Gerichte werden nach dem Kochen in einem gelb-orangen App-Dialog mit Kochtag und Abstand zum nächsten Termin angezeigt. „Neuen Vorschlag machen“ ersetzt den Termin, „Passt“ behält ihn.
- Lieblingsgerichte stehen in der Gerichtsauswahl zuerst und werden mit einem Herz markiert; beide Gruppen sind alphabetisch sortiert.
- Tageskarte mit „Selbst wählen“, Haken zum Einplanen und grünem „Gekocht“-Button.
- Erklärungstexte gestrafft, neuer Wochenplan-Spruch und Planungshinweis direkt unter dem Planungsbutton.
- Einzeiliger Button „Neues Gericht hinzufügen“ in der Gerichteübersicht.

Vor dem Update eine Sicherung erstellen. Bestehende Daten werden beim Start automatisch migriert. Zum Aktualisieren die App nicht deinstallieren.

# 1.3.0

- Historie zeigt zunächst sieben Tage; ältere Einträge lassen sich auf- und zuklappen sowie in Schritten von 30 Tagen nachladen.
- Statistiken stehen neben den vergangenen Tagen, auf kleinen Bildschirmen darunter.
- Eigene Einstellungen-Ansicht für Haushalt, Darstellung, Kalender und Datensicherung, auf jeder Seite rechts oben erreichbar.
- Mehr Abstand zwischen Einstellungsbutton und Seitennamen; Datenblock ohne große Lücke unter dem Kalenderblock.
- Bei abweichend gekochten Gerichten steht „Geplant: …“ mit dem Kochstatus in einer gemeinsamen Zeile. Textelemente haben mehr Abstand.
- Verständlichere Rückfrage zu bereits eingeplanten Gerichten nach einer Kochbestätigung.
- Farbige Aufwand-Auswahl passend zu den Gerichtskarten.
- Fehler behoben: Bei nicht als Lieblingsgericht markierten Gerichten wird keine „0“ mehr angezeigt.

Bestehende Daten und Einstellungen bleiben bei einem Update erhalten. Vorher eine Sicherung erstellen; zum Aktualisieren nicht deinstallieren.

# 1.2.0

- Neue helle und dunkle Farbgestaltung: Vorschläge blau, eingeplante Gerichte grün, vergangene ungekochte Planungen orange und Gekochtes lila.
- Einheitliche Statusbezeichnung „Eingeplant“, passende Farblegenden und kontrastreichere rahmenlose Buttons und Navigation.
- Kompaktere Wochenplankarten mit Datum unter dem Wochentag, Status rechts oben und den Aktionen ↻, „Selbst wählen“ und ✓. Bereits eingeplante Gerichte benötigen keine erneute Bestätigung.
- „Tag freilassen“ liegt im Auswahlfenster unter „Einplanen“; Datum und Planungsbutton stehen gemeinsam oben.
- Tageskarte mit vorhandenen Notizen und Zutaten, stabilen Aktionsabständen und ohne Vorschlags-/Planungsaktionen nach dem Kochen.
- Erfolgsmeldungen schweben über der Seite und verschwinden nach fünf Sekunden ohne Layoutverschiebung.
- Gerichtskarten mit Tags oben, farbiger Aufwand-Kennzeichnung mit Symbolen und sichtbarer Inaktiv-Markierung.
- Gerichtsname als live aktualisierte Dialogüberschrift, höhere Dropdowns und auswählbares Lieblingsgericht-Herz neben dem Schließen-Button.
- Historienbuttons mit gemeinsamen Abständen, Haken für Kochbestätigung und Papierkorb zum Löschen.
- „Statistiken“ im Chart-Stil mit Ranglisten, Häufigkeitsbalken und mehr Abstand zwischen den Abschnitten.

Bestehende Daten und Einstellungen bleiben bei einem Update erhalten. Vorher eine Sicherung erstellen; zum Aktualisieren nicht deinstallieren.

# 1.1.1

- Darstellungsfehler bei freien Tagen in der Historie und im Wochenplan behoben: Statuszeilen bleiben linksbündig und erhalten keine übergroßen Innenabstände.

# 1.1.0

- Historie als durchgehende Tagesliste mit gespeicherten Vorschlägen und tatsächlichen Kochereignissen.
- Vorgeschlagene Gerichte direkt als gekocht erfassen oder ein anderes Gericht für den jeweiligen Tag auswählen.
- Zunächst 30 Tage anzeigen und ältere Tage nachladen; Statistik zählt nur tatsächliche Kochereignisse.
- Wochenplan mit größerem Wochentag und Datum, Button „Neuer Vorschlag“ und ohne Einleitungsblock.
- Kompaktes Gerichteformular mit eingeklappten Notizen und Zutaten sowie dauerhaft sichtbaren Speichern-/Abbrechen-Buttons.
- Hilfetexte bei Aufwand, Vorschlagshäufigkeit, Tags und Zutaten per Maus, Tastatur oder Antippen.

Bestehende Daten und Einstellungen bleiben bei einem Update erhalten. Vor dem Update eine Sicherung erstellen; die App zum Aktualisieren nicht deinstallieren.

# 1.0.0

- Erstes lokales Home-Assistant-OS-Paket mit eigenem Web-Port und Kalender-Abo.
- Dauerhafte SQLite-Daten und gestoppte Sicherung durch Home Assistant.
- Konfigurierbare externe Adresse und sichere Cookies für HTTPS-Proxys.
