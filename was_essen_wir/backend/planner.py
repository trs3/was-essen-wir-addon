"""Explainable weighted sampling; all variety penalties are soft."""
import random
from datetime import date

DEFAULTS = dict(recent3=.015, recent7=.12, recent14=.45, old30=1.8,
                never=2.4, category=.18, tag=.65, rare=1.4)
PREFERRED_GAP_DAYS = 3


def weight(dish, day, history, neighbors, params=None):
    p = DEFAULTS | (params or {})
    events = [h for h in history if h['dish_id'] == dish['id'] and h['day'] <= day]
    age = (date.fromisoformat(day) - date.fromisoformat(max(h['day'] for h in events))).days if events else None
    w, reasons = 1.0, []
    if age is None:
        w *= p['never']; reasons.append('Noch nie gekocht')
    else:
        factor = p['recent3'] if age <= 3 else p['recent7'] if age <= 7 else p['recent14'] if age <= 14 else p['old30'] if age > 30 else 1
        w *= factor; reasons.append(f'Zuletzt vor {age} Tagen')
    count = sum(0 <= (date.fromisoformat(day) - date.fromisoformat(h['day'])).days <= 30 for h in events)
    w /= 1 + count
    if len(events) < 3:
        w *= p['rare']; reasons.append('Selten gekocht')
    for other in neighbors:
        if other['category'] == dish['category']:
            w *= p['category']; reasons.append('Ähnliche Kategorie in der Nähe')
        overlap = set(other['tags']) & set(dish['tags'])
        w *= p['tag'] ** len(overlap)
    frequency = dish.get('frequency_factor', 1)
    w *= frequency
    if frequency > 1:
        reasons.append('Persönlich häufiger gewünscht')
    elif frequency < 1:
        reasons.append('Persönlich seltener gewünscht')
    return max(w, .000001), list(dict.fromkeys(reasons))


def choose(dishes, day, history, neighbors, excluded=(), rejected=(), params=None, previous=None, quick_only=False):
    # Apply the weekday rule before every fallback, so it cannot admit harder dishes.
    active = [d for d in dishes if d['active'] and (not quick_only or d.get('effort', 'normal') == 'quick')]
    candidates = [d for d in active if d['id'] not in excluded and d['id'] not in rejected and d['id'] != previous]
    # Exhausted rejections may be recycled, but the immediately previous dish stays out.
    if not candidates:
        candidates = [d for d in active if d['id'] not in excluded and d['id'] != previous]
    # A small collection can require repeating a planned dish.
    if not candidates:
        candidates = [d for d in active if d['id'] != previous]
    if not candidates:
        candidates = active
    if not candidates:
        return None
    scores = [weight(d, day, history, neighbors, params)[0] for d in candidates]
    return random.choices(candidates, weights=scores, k=1)[0]
