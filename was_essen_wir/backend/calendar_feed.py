"""Small RFC 5545 feed: local calendar dates, escaped TEXT, UTF-8 line folding."""
from datetime import date, timedelta

STATUS_LABELS = {
    'suggested': 'Vorschlag', 'confirmed': 'Bestätigt',
    'fixed': 'Fest eingeplant', 'cooked': 'Gekocht',
}
EFFORT_LABELS = {'quick': 'Geht schnell', 'normal': 'Normal', 'elaborate': 'Aufwändig'}


def escape_text(value):
    text = str(value).replace('\r\n', '\n').replace('\r', '\n')
    text = ''.join(c for c in text if c == '\n' or ord(c) >= 32 and ord(c) != 127)
    return text.replace('\\', '\\\\').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')


def fold_line(line):
    """RFC limit is 75 octets, including the continuation's leading space."""
    result, current, size = [], '', 0
    for char in line:
        length = len(char.encode('utf-8'))
        if size + length > 75:
            result.append(current)
            current, size = ' ', 1
        current += char
        size += length
    result.append(current)
    return result


def render_calendar(events, namespace, stamp, sequence, local_timezone):
    lines = [
        'BEGIN:VCALENDAR', 'VERSION:2.0',
        'PRODID:-//Was essen wir//Familienkueche//DE', 'CALSCALE:GREGORIAN',
        'X-WR-CALNAME:Was essen wir?',
        'X-WR-CALDESC:Unser gemeinsamer Abendessenplan',
        'X-WR-TIMEZONE:' + escape_text(local_timezone),
        'REFRESH-INTERVAL;VALUE=DURATION:PT1H', 'X-PUBLISHED-TTL:PT1H',
    ]
    for event in events:
        day = date.fromisoformat(event['day'])
        description = (
            f"Status: {STATUS_LABELS[event['status']]}\n"
            f"Kategorie: {event['category']}\n"
            f"Aufwand: {EFFORT_LABELS[event['effort']]}"
        )
        if event['note']:
            description += '\n\n' + event['note']
        lines.extend([
            'BEGIN:VEVENT',
            f'UID:dinner-{namespace}-{day:%Y%m%d}@was-essen-wir.local',
            'DTSTAMP:' + stamp, 'LAST-MODIFIED:' + stamp,
            f'SEQUENCE:{sequence}',
            f'DTSTART;VALUE=DATE:{day:%Y%m%d}',
            f'DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}',
            'SUMMARY:' + escape_text('Abendessen: ' + event['name']),
            'DESCRIPTION:' + escape_text(description),
            'CATEGORIES:' + escape_text(event['category']),
            'STATUS:' + ('TENTATIVE' if event['status'] == 'suggested' else 'CONFIRMED'),
            'TRANSP:TRANSPARENT', 'CLASS:PRIVATE', 'END:VEVENT',
        ])
    lines.append('END:VCALENDAR')
    return '\r\n'.join(folded for line in lines for folded in fold_line(line)) + '\r\n'
