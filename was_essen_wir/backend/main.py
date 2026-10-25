import csv
import hashlib
import hmac
import io
import json
import logging
import os
import re
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import db, planner, calendar_feed

CATEGORIES = ['Nudelgerichte','Reisgerichte','Kartoffelgerichte','Gemüsegerichte','Fleischgerichte','Fischgerichte','Suppen und Eintöpfe','Süßspeisen','Pizza und Ofengerichte','Brotzeit und kalte Küche','Sonstiges']
RULES = json.loads(Path(os.getenv('RULES_PATH', str(Path(__file__).with_name('rules.json')))).read_text())

@asynccontextmanager
async def lifespan(app):
    db.init()
    access_filter = CalendarAccessFilter()
    logging.getLogger('uvicorn.access').addFilter(access_filter)
    try:
        yield
    finally:
        logging.getLogger('uvicorn.access').removeFilter(access_filter)

app = FastAPI(title='Was essen wir?', lifespan=lifespan)


class CalendarAccessFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            args[2] = re.sub(r'/calendar/[^/]+/essen\.ics', '/calendar/[private]/essen.ics', str(args[2]))
            record.args = tuple(args)
        return True


def setting(c, key, default=None):
    r = c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
    return r['value'] if r else default


def put(c,key,value):
    c.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))


def today(c):
    return datetime.now(ZoneInfo(setting(c,'timezone',os.getenv('TZ','Europe/Berlin')))).date().isoformat()


def dates(start, days):
    try:
        d = date.fromisoformat(start)
    except ValueError:
        raise HTTPException(422,'Ungültiges Datum')
    return [(d+timedelta(days=i)).isoformat() for i in range(days)]


def dishes(c):
    result = []
    for row in c.execute('SELECT * FROM dishes ORDER BY name COLLATE NOCASE'):
        d = dict(row)
        d['tags'] = json.loads(d['tags']); d['ingredients'] = json.loads(d['ingredients'])
        stats = c.execute('SELECT MAX(day) last_cooked,COUNT(*) cooked_count FROM history WHERE dish_id=?',(d['id'],)).fetchone()
        d.update(dict(stats))
        d['days_since_cooked'] = (date.fromisoformat(today(c))-date.fromisoformat(d['last_cooked'])).days if d['last_cooked'] else None
        result.append(d)
    return result


def rows(c, table):
    return [dict(r) for r in c.execute(f'SELECT * FROM {table}')]


def check_version(row, version):
    if row is None:
        raise HTTPException(404,'Eintrag nicht gefunden')
    if row['version'] != version:
        raise HTTPException(409,'Inzwischen auf einem anderen Gerät geändert. Bitte den aktuellen Stand prüfen und eine offene Bearbeitung neu öffnen.')


def dish_exists(c, id):
    if not c.execute('SELECT 1 FROM dishes WHERE id=?',(id,)).fetchone():
        raise HTTPException(422,'Gericht nicht gefunden')


def quick_weekdays(c):
    return json.loads(setting(c, 'quick_only_weekdays', '[]'))


def suggestion_failure(c, day):
    if date.fromisoformat(day).weekday() in quick_weekdays(c):
        return 'Für diesen Wochentag sind nur Gerichte mit „Geht schnell“ vorgesehen. Bitte mindestens ein solches Gericht aktivieren oder anlegen.'
    return 'Bitte zuerst ein aktives Gericht anlegen.'


def suggest(c, day, previous=None):
    all_dishes = dishes(c)
    history = rows(c,'history'); plans = rows(c,'plans')
    target = date.fromisoformat(day)
    by_id = {d['id']:d for d in all_dishes}
    neighbors = []
    cooked_days = {h['day'] for h in history}
    effective_plans = [p for p in plans if p['day'] not in cooked_days]
    for event in history + effective_plans:
        delta = (date.fromisoformat(event['day']) - target).days
        if -2 <= delta <= 2 and delta != 0 and event['dish_id'] in by_id:
            neighbors.append(by_id[event['dish_id']])
    excluded = []
    for planned in effective_plans:
        if planned['day'] == day or planned['dish_id'] not in by_id:
            continue
        gap = abs((date.fromisoformat(planned['day'])-target).days)
        preferred = by_id[planned['dish_id']]['frequency_factor'] > 1
        # Explicitly preferred dishes may recur with two free days in between.
        if gap < (planner.PREFERRED_GAP_DAYS if preferred else 14):
            excluded.append(planned['dish_id'])
    rejected = [r[0] for r in c.execute('SELECT dish_id FROM rejections WHERE day=?',(day,))]
    chosen = planner.choose(all_dishes,day,history,neighbors,excluded,rejected,json.loads(setting(c,'weights','{}')),previous,quick_only=target.weekday() in quick_weekdays(c))
    if chosen:
        c.execute("INSERT INTO plans(day,dish_id,status) VALUES(?,?,'suggested') ON CONFLICT(day) DO UPDATE SET dish_id=excluded.dish_id,status='suggested',version=plans.version+1",(day,chosen['id']))
    return chosen


@app.middleware('http')
async def security(request: Request, call_next):
    path = request.url.path
    if path.startswith('/api/'):
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin = request.headers.get('origin')
            expected = os.getenv('PUBLIC_ORIGIN')
            if origin and origin.rstrip('/') != (expected or f'{request.url.scheme}://{request.headers.get("host")}').rstrip('/'):
                return JSONResponse({'detail':'Unzulässiger Ursprung'},403)
            if request.headers.get('x-requested-with') != 'essen-app':
                return JSONResponse({'detail':'Anfrage-Kennung fehlt'},403)
        if path not in ('/api/auth/status','/api/auth/setup','/api/auth/login','/api/health'):
            token = hashlib.sha256(request.cookies.get('session','').encode()).hexdigest()
            with db.transaction() as c:
                session = c.execute('SELECT 1 FROM sessions WHERE token=? AND expires>?',(token,time.time())).fetchone()
            if not session:
                return JSONResponse({'detail':'Bitte anmelden'},401)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    if path.startswith(('/api/', '/calendar/')):
        response.headers['Cache-Control'] = 'no-store'
    if path.startswith('/calendar/'):
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    return response


def calendar_status(c):
    token = setting(c, 'calendar_token')
    return {
        'enabled': bool(token),
        'path': f'/calendar/{token}/essen.ics' if token else None,
        'version': int(setting(c, 'calendar_version', '0')),
    }


@app.get('/api/calendar')
def get_calendar():
    with db.transaction() as c:
        return calendar_status(c)


class CalendarAction(BaseModel):
    action: Literal['enable', 'rotate', 'disable']
    version: int


@app.post('/api/calendar')
def configure_calendar(b: CalendarAction):
    with db.transaction(True) as c:
        if b.version != int(setting(c, 'calendar_version', '0')):
            raise HTTPException(409, 'Kalender-Link inzwischen geändert. Bitte die Ansicht neu öffnen.')
        if b.action == 'disable':
            c.execute("DELETE FROM settings WHERE key='calendar_token'")
        elif b.action == 'rotate' or not setting(c, 'calendar_token'):
            put(c, 'calendar_token', secrets.token_urlsafe(32))
            if not setting(c, 'calendar_namespace'):
                put(c, 'calendar_namespace', secrets.token_hex(16))
        put(c, 'calendar_version', str(b.version + 1))
        return calendar_status(c)


@app.api_route('/calendar/{token}/essen.ics', methods=['GET', 'HEAD'])
def calendar_subscription(token: str, request: Request):
    with db.transaction() as c:
        current = setting(c, 'calendar_token', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token) or not current or not hmac.compare_digest(token.encode(), current.encode()):
            raise HTTPException(404, 'Kalender-Link nicht verfügbar')
        known = {d['id']: d for d in dishes(c)}
        schedule = {p['day']: p for p in rows(c, 'plans') if p['dish_id'] is not None}
        for event in rows(c, 'history'):
            schedule[event['day']] = event | {'status': 'cooked'}
        events = [known[p['dish_id']] | {'day': day, 'status': p['status']} for day, p in sorted(schedule.items()) if p['dish_id'] in known]
        body = calendar_feed.render_calendar(
            events, setting(c, 'calendar_namespace'), setting(c, 'modified_at'),
            int(setting(c, 'revision', '0')), setting(c, 'timezone', os.getenv('TZ', 'Europe/Berlin')),
        )
    headers = {
        'Content-Disposition': 'inline; filename="was-essen-wir.ics"',
        'ETag': '"' + hashlib.sha256(body.encode()).hexdigest() + '"',
    }
    if request.headers.get('if-none-match') == headers['ETag']:
        return Response(status_code=304, headers=headers)
    return Response(body, media_type='text/calendar; charset=utf-8', headers=headers)


class Password(BaseModel):
    password: str = Field(min_length=6,max_length=256)


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()


def session(c,response):
    raw = secrets.token_urlsafe(40)
    c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
    c.execute('INSERT INTO sessions VALUES(?,?)',(hashlib.sha256(raw.encode()).hexdigest(),time.time()+30*86400))
    response.set_cookie('session',raw,max_age=30*86400,httponly=True,secure=os.getenv('COOKIE_SECURE','false').lower()=='true',samesite='strict',path='/')


@app.get('/api/health')
def health():
    return {'status':'ok'}


@app.get('/api/auth/status')
def auth_status(request:Request):
    with db.transaction() as c:
        token = hashlib.sha256(request.cookies.get('session','').encode()).hexdigest()
        return {'setup':setting(c,'password_hash') is None,'authenticated':bool(c.execute('SELECT 1 FROM sessions WHERE token=? AND expires>?',(token,time.time())).fetchone())}


@app.post('/api/auth/setup')
def setup(body:Password,response:Response):
    with db.transaction(True) as c:
        if setting(c,'password_hash'):
            raise HTTPException(409,'Haushalt bereits eingerichtet')
        salt = secrets.token_hex(16)
        put(c,'salt',salt); put(c,'password_hash',password_hash(body.password,salt)); session(c,response)
    return {'ok':True}


@app.post('/api/auth/login')
def login(body:Password,response:Response,request:Request):
    failure = False
    with db.transaction(True) as c:
        ip = request.client.host if request.client else 'local'
        a = c.execute('SELECT * FROM attempts WHERE ip=?',(ip,)).fetchone()
        if a and a['count'] >= 8 and a['until'] > time.time():
            raise HTTPException(429,'Zu viele Versuche. Bitte in 15 Minuten erneut versuchen.')
        stored = setting(c,'password_hash')
        if not stored or not hmac.compare_digest(stored,password_hash(body.password,setting(c,'salt'))):
            count = a['count']+1 if a and a['until'] > time.time() else 1
            c.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)',(ip,count,time.time()+900)); failure=True
        else:
            c.execute('DELETE FROM attempts WHERE ip=?',(ip,)); session(c,response)
    if failure:
        raise HTTPException(401,'Passwort oder PIN stimmt nicht')
    return {'ok':True}


@app.post('/api/auth/logout')
def logout(request:Request,response:Response):
    with db.transaction(True) as c:
        c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(request.cookies.get('session','').encode()).hexdigest(),))
    response.delete_cookie('session'); return {'ok':True}


@app.get('/api/state')
def state():
    with db.transaction(True) as c:
        day = today(c)
        suggestion_notice = None
        if not c.execute('SELECT 1 FROM plans WHERE day=?',(day,)).fetchone() and not c.execute('SELECT 1 FROM history WHERE day=?',(day,)).fetchone():
            if not suggest(c,day) and date.fromisoformat(day).weekday() in quick_weekdays(c):
                suggestion_notice = suggestion_failure(c,day)
        return {'today':day,'dishes':dishes(c),'plans':rows(c,'plans'),'history':rows(c,'history'),'categories':CATEGORIES,'timezone':setting(c,'timezone',os.getenv('TZ','Europe/Berlin')),'weights':planner.DEFAULTS | json.loads(setting(c,'weights','{}')),'revision':int(setting(c,'revision','0'))+int(c.total_changes>0),'suggestion_notice':suggestion_notice}


@app.get('/api/classify')
def classify(name:str=''):
    matches = [r for r in RULES if any(w in name.lower() for w in r['words'])]
    return {'category':matches[-1]['category'] if matches else 'Sonstiges','tags':list(dict.fromkeys(t for r in matches for t in r['tags']))}


class Ingredient(BaseModel):
    name: str = Field(min_length=1,max_length=150)
    amount: float = Field(default=1,gt=0,le=100000)
    unit: str = Field(default='Stück',max_length=30)

class Dish(BaseModel):
    name: str = Field(min_length=1,max_length=150)
    category: str = 'Sonstiges'
    effort: Literal['quick','normal','elaborate'] = 'normal'
    frequency_factor: Literal[0.5,0.75,1,1.5,2] = 1
    tags: list[str] = Field(default_factory=list,max_length=30)
    ingredients: list[Ingredient] = Field(default_factory=list,max_length=100)
    note: str = Field(default='',max_length=10000)
    favorite: bool = False
    active: bool = True
    version: int = 1


def save_dish(c,b,id=None):
    if b.category not in CATEGORIES or not b.name.strip():
        raise HTTPException(422,'Name oder Kategorie ungültig')
    previous = c.execute('SELECT * FROM dishes WHERE id=?',(id,)).fetchone() if id is not None else None
    if id is not None:
        check_version(previous,b.version)
    effort = previous['effort'] if previous and 'effort' not in b.model_fields_set else b.effort
    frequency = previous['frequency_factor'] if previous and 'frequency_factor' not in b.model_fields_set else b.frequency_factor
    values = (b.name.strip(),b.category,json.dumps(list(dict.fromkeys(t.strip() for t in b.tags if t.strip()))),json.dumps([i.model_dump() for i in b.ingredients]),b.note,b.favorite,b.active,effort,frequency)
    if id is None:
        return c.execute('INSERT INTO dishes(name,category,tags,ingredients,note,favorite,active,effort,frequency_factor) VALUES(?,?,?,?,?,?,?,?,?)',values).lastrowid
    c.execute('UPDATE dishes SET name=?,category=?,tags=?,ingredients=?,note=?,favorite=?,active=?,effort=?,frequency_factor=?,version=version+1 WHERE id=?',values+(id,)); return id


@app.post('/api/dishes')
def create_dish(b:Dish):
    with db.transaction(True) as c:
        return {'id':save_dish(c,b)}

@app.put('/api/dishes/{id}')
def edit_dish(id:int,b:Dish):
    with db.transaction(True) as c:
        return {'id':save_dish(c,b,id)}

@app.delete('/api/dishes/{id}')
def delete_dish(id:int,version:int):
    with db.transaction(True) as c:
        check_version(c.execute('SELECT * FROM dishes WHERE id=?',(id,)).fetchone(),version)
        if c.execute('SELECT 1 FROM history WHERE dish_id=? UNION SELECT 1 FROM plans WHERE dish_id=?',(id,id)).fetchone():
            c.execute('UPDATE dishes SET active=0,version=version+1 WHERE id=?',(id,)); return {'deactivated':True}
        c.execute('DELETE FROM rejections WHERE dish_id=?',(id,)); c.execute('DELETE FROM dishes WHERE id=?',(id,))
    return {'ok':True}


class PlanAction(BaseModel):
    version: int = 0
    action: str
    dish_id: int | None = None

@app.put('/api/plans/{day}')
def plan_action(day:str,b:PlanAction):
    dates(day,1)
    same_dish=False
    with db.transaction(True) as c:
        row = c.execute('SELECT * FROM plans WHERE day=?',(day,)).fetchone()
        if row: check_version(row,b.version)
        elif b.version != 0: raise HTTPException(409,'Plan inzwischen geändert')
        if b.action == 'replace':
            if row and row['dish_id']:
                c.execute('INSERT OR IGNORE INTO rejections VALUES(?,?)',(day,row['dish_id']))
            chosen=suggest(c,day,row['dish_id'] if row else None)
            if not chosen: raise HTTPException(422,suggestion_failure(c,day))
            same_dish=bool(row and chosen['id']==row['dish_id'])
        elif b.action in ('fixed','confirmed','empty'):
            id = None if b.action=='empty' else b.dish_id or (row['dish_id'] if row else None)
            if b.action != 'empty': dish_exists(c,id)
            c.execute('INSERT INTO plans(day,dish_id,status) VALUES(?,?,?) ON CONFLICT(day) DO UPDATE SET dish_id=excluded.dish_id,status=excluded.status,version=plans.version+1',(day,id,b.action))
        else: raise HTTPException(422,'Unbekannte Aktion')
    return {'ok':True,'same_dish':same_dish}

class Period(BaseModel):
    start: date
    days: int = Field(default=7,ge=1,le=14)

@app.post('/api/plan')
def plan_period(b:Period):
    unfilled=[]
    with db.transaction(True) as c:
        for day in dates(b.start.isoformat(),b.days):
            if not c.execute('SELECT 1 FROM plans WHERE day=?',(day,)).fetchone() and not c.execute('SELECT 1 FROM history WHERE day=?',(day,)).fetchone():
                if not suggest(c,day):
                    unfilled.append({'day':day,'reason':suggestion_failure(c,day)})
    return {'ok':True,'unfilled':unfilled}


class Cook(BaseModel):
    day: date
    dish_id: int
    version: int = 0
    plan_version: int = 0

@app.post('/api/cook')
def cook(b:Cook):
    day = b.day.isoformat()
    with db.transaction(True) as c:
        if day > today(c): raise HTTPException(422,'Zukünftige Tage können noch nicht als gekocht erfasst werden')
        dish_exists(c,b.dish_id)
        old = c.execute('SELECT * FROM history WHERE day=?',(day,)).fetchone()
        if old: check_version(old,b.version)
        elif b.version: raise HTTPException(409,'Kochhistorie inzwischen geändert')
        planned = c.execute('SELECT * FROM plans WHERE day=?',(day,)).fetchone()
        if planned: check_version(planned,b.plan_version)
        elif b.plan_version: raise HTTPException(409,'Plan inzwischen geändert')
        c.execute('INSERT INTO history(day,dish_id) VALUES(?,?) ON CONFLICT(day) DO UPDATE SET dish_id=excluded.dish_id,version=history.version+1',(day,b.dish_id))
        conflicts=[]; replaced=[]; unfilled=[]
        preferred = c.execute('SELECT frequency_factor FROM dishes WHERE id=?',(b.dish_id,)).fetchone()[0] > 1
        for row in list(c.execute('SELECT * FROM plans WHERE day>? AND day<=? AND dish_id=? ORDER BY day',(day,(b.day+timedelta(days=14)).isoformat(),b.dish_id))):
            if preferred and (date.fromisoformat(row['day'])-b.day).days >= planner.PREFERRED_GAP_DAYS:
                continue
            if row['status']=='suggested':
                if suggest(c,row['day'],b.dish_id):
                    replaced.append(row['day'])
                else:
                    c.execute('DELETE FROM plans WHERE day=?',(row['day'],))
                    unfilled.append({'day':row['day'],'reason':suggestion_failure(c,row['day'])})
            else: conflicts.append(dict(row))
    return {'conflicts':conflicts,'replaced':replaced,'unfilled':unfilled}

class HistoryEdit(BaseModel):
    day: date
    dish_id: int
    version: int

@app.put('/api/history/{id}')
def edit_history(id:int,b:HistoryEdit):
    with db.transaction(True) as c:
        check_version(c.execute('SELECT * FROM history WHERE id=?',(id,)).fetchone(),b.version)
        if b.day.isoformat()>today(c): raise HTTPException(422,'Datum liegt in der Zukunft')
        dish_exists(c,b.dish_id)
        if c.execute('SELECT 1 FROM history WHERE day=? AND id!=?',(b.day.isoformat(),id)).fetchone(): raise HTTPException(409,'An diesem Tag ist bereits ein Kochereignis gespeichert')
        c.execute('UPDATE history SET day=?,dish_id=?,version=version+1 WHERE id=?',(b.day.isoformat(),b.dish_id,id))
    return {'ok':True}

@app.delete('/api/history/{id}')
def delete_history(id:int,version:int):
    with db.transaction(True) as c:
        check_version(c.execute('SELECT * FROM history WHERE id=?',(id,)).fetchone(),version)
        c.execute('DELETE FROM history WHERE id=?',(id,))
    return {'ok':True}


UNITS = {'g':('g',1),'kg':('g',1000),'ml':('ml',1),'l':('ml',1000),'stück':('Stück',1),'stk':('Stück',1)}

def shopping_items(c,start,days):
    items={}; end=dates(start,days)[-1]
    for row in c.execute('SELECT d.ingredients FROM plans p JOIN dishes d ON d.id=p.dish_id WHERE p.day BETWEEN ? AND ?',(start,end)):
        for i in json.loads(row[0]):
            unit,factor=UNITS.get(i['unit'].lower().strip(),(i['unit'].strip(),1))
            key=hashlib.sha256((i['name'].strip().casefold()+'|'+unit).encode()).hexdigest()[:24]
            if key not in items: items[key]={'key':key,'name':i['name'],'amount':0,'unit':unit,'done':False,'manual':False,'version':0}
            items[key]['amount'] += i['amount']*factor
    for row in rows(c,'shopping'):
        if row['manual']: items[row['key']]=row
        elif row['key'] in items: items[row['key']].update(done=row['done'],version=row['version'])
    return list(items.values())

@app.get('/api/shopping')
def shopping(start:date,days:int=7):
    if not 1<=days<=14: raise HTTPException(422,'Ungültiger Zeitraum')
    with db.transaction() as c: return shopping_items(c,start.isoformat(),days)

class ShoppingItem(BaseModel):
    key: str = Field(max_length=100)
    name: str = Field(min_length=1,max_length=150)
    done: bool=False
    manual: bool=False
    version: int=0

@app.post('/api/shopping')
def update_shopping(b:ShoppingItem):
    with db.transaction(True) as c:
        row=c.execute('SELECT * FROM shopping WHERE key=?',(b.key,)).fetchone()
        if row: check_version(row,b.version)
        elif b.version: raise HTTPException(409,'Einkaufsliste inzwischen geändert')
        c.execute('INSERT INTO shopping(key,name,done,manual) VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET done=excluded.done,name=excluded.name,version=shopping.version+1',(b.key,b.name,b.done,b.manual))
    return {'ok':True}

@app.delete('/api/shopping/{key}')
def delete_shopping(key:str,version:int):
    with db.transaction(True) as c:
        check_version(c.execute('SELECT * FROM shopping WHERE key=?',(key,)).fetchone(),version)
        c.execute('DELETE FROM shopping WHERE key=?',(key,))
    return {'ok':True}

class Settings(BaseModel):
    timezone:str
    weights:dict[str,float]
    revision:int
    quick_only_weekdays:list[Annotated[int,Field(strict=True,ge=0,le=6)]] = Field(default_factory=list,max_length=7)

@app.put('/api/settings')
def settings(b:Settings):
    try: ZoneInfo(b.timezone)
    except Exception: raise HTTPException(422,'Unbekannte Zeitzone')
    if set(b.weights)!=set(planner.DEFAULTS) or any(not .000001<=v<=100 for v in b.weights.values()): raise HTTPException(422,'Gewichtungen müssen zwischen 0,000001 und 100 liegen')
    with db.transaction(True) as c:
        if b.revision!=int(setting(c,'settings_version','0')): raise HTTPException(409,'Einstellungen inzwischen geändert')
        put(c,'timezone',b.timezone); put(c,'weights',json.dumps(b.weights)); put(c,'settings_version',str(b.revision+1))
        if 'quick_only_weekdays' in b.model_fields_set:
            put(c,'quick_only_weekdays',json.dumps(sorted(set(b.quick_only_weekdays))))
    return {'ok':True}

@app.get('/api/settings')
def get_settings():
    with db.transaction() as c: return {'timezone':setting(c,'timezone',os.getenv('TZ','Europe/Berlin')),'weights':planner.DEFAULTS | json.loads(setting(c,'weights','{}')),'revision':int(setting(c,'settings_version','0')),'quick_only_weekdays':quick_weekdays(c)}

@app.get('/api/export')
def export():
    with db.transaction() as c:
        data={'format':'was-essen-wir','version':1,'dishes':dishes(c),'plans':rows(c,'plans'),'history':rows(c,'history'),'rejections':rows(c,'rejections'),'shopping':rows(c,'shopping'),'settings':{'timezone':setting(c,'timezone',os.getenv('TZ','Europe/Berlin')),'weights':json.loads(setting(c,'weights','{}')),'quick_only_weekdays':quick_weekdays(c)}}
    return JSONResponse(data,headers={'Content-Disposition':'attachment; filename="was-essen-wir-backup.json"'})

class ImportData(BaseModel):
    data:dict
    mode:str='merge'

@app.post('/api/import')
def import_data(b:ImportData):
    data=b.data
    if not isinstance(data.get('dishes',[]),list) or not isinstance(data.get('history',[]),list): raise HTTPException(422,'Gerichte und Historie müssen Listen sein')
    if b.mode not in ('merge','restore'): raise HTTPException(422,'Ungültiger Importmodus')
    try:
        parsed=[(d,Dish.model_validate(d)) for d in data.get('dishes',[])]
        if len(parsed)>10000: raise ValueError('Zu viele Gerichte')
        with db.transaction(True) as c:
            if b.mode=='restore':
                if data.get('format')!='was-essen-wir' or data.get('version')!=1: raise ValueError('Unbekanntes Sicherungsformat')
                for table in ('rejections','plans','history','shopping','dishes'): c.execute(f'DELETE FROM {table}')
            mapping={}
            for original,d in parsed:
                new=save_dish(c,d)
                if 'id' in original: mapping[original['id']]=new
            for h in data.get('history',[]):
                day=date.fromisoformat(h['day']).isoformat()
                if day>today(c): raise ValueError('Kochdatum liegt in der Zukunft')
                id=mapping.get(h['dish_id'])
                if id is None: raise ValueError('Unbekanntes Gericht in Historie')
                c.execute('INSERT INTO history(day,dish_id) VALUES(?,?) ON CONFLICT(day) DO UPDATE SET dish_id=excluded.dish_id,version=history.version+1',(day,id))
            if b.mode=='restore':
                for p in data.get('plans',[]):
                    day=date.fromisoformat(p['day']).isoformat(); id=mapping[p['dish_id']] if p['dish_id'] is not None else None
                    if p['status'] not in ('suggested','confirmed','fixed','empty') or (p['status']=='empty')!=(id is None): raise ValueError('Ungültiger Planstatus')
                    c.execute('INSERT INTO plans(day,dish_id,status) VALUES(?,?,?)',(day,id,p['status']))
                for r in data.get('rejections',[]): c.execute('INSERT INTO rejections VALUES(?,?)',(date.fromisoformat(r['day']).isoformat(),mapping[r['dish_id']]))
                for s in data.get('shopping',[]):
                    si=ShoppingItem.model_validate(s)
                    c.execute('INSERT INTO shopping(key,name,done,manual) VALUES(?,?,?,?)',(si.key,si.name,si.done,si.manual))
                config=data.get('settings',{}); tz=config.get('timezone','Europe/Berlin'); ZoneInfo(tz)
                weights=config.get('weights',{})
                if any(k not in planner.DEFAULTS or not .000001<=float(v)<=100 for k,v in weights.items()): raise ValueError('Ungültige Gewichtungen')
                restored=Settings(timezone=tz,weights=weights,revision=0,quick_only_weekdays=config.get('quick_only_weekdays',[]))
                put(c,'timezone',tz); put(c,'weights',json.dumps(weights))
                put(c,'quick_only_weekdays',json.dumps(sorted(set(restored.quick_only_weekdays))))
                put(c,'settings_version',str(int(setting(c,'settings_version','0'))+1))
                # Invalidate editors opened against the dataset before restoration.
                generation=int(time.time()*1000)
                for table in ('dishes','plans','history','shopping'):
                    c.execute(f'UPDATE {table} SET version=?',(generation,))
    except (ValueError,KeyError,TypeError,sqlite3.IntegrityError) as e: raise HTTPException(422,f'Import ungültig: {e}')
    return {'imported':len(parsed)}

class CSVData(BaseModel):
    text:str=Field(max_length=2000000)

@app.post('/api/import/csv')
def import_csv(b:CSVData):
    try:
        try:
            dialect=csv.Sniffer().sniff(b.text[:4096],delimiters=',;\t')
        except csv.Error:
            dialect=csv.excel
        reader=csv.DictReader(io.StringIO(b.text.lstrip('\ufeff')),dialect=dialect)
        if not reader.fieldnames or not ({'Name','name'} & set(reader.fieldnames)): raise ValueError('Spalte Name fehlt')
        entries=[]
        for r in reader:
            name=r.get('name') or r.get('Name') or ''
            guess=classify(name)
            raw_effort=(r.get('effort') or r.get('Aufwand') or 'normal').strip().casefold()
            effort={'geht schnell':'quick','normal':'normal','aufwändig':'elaborate','aufwendig':'elaborate'}.get(raw_effort,raw_effort)
            raw_frequency=(r.get('frequency_factor') or r.get('Häufigkeit') or '1').strip().casefold()
            frequency_labels={'seltener':0.5,'etwas seltener':0.75,'normal':1,'etwas häufiger':1.5,'häufiger':2}
            frequency=frequency_labels[raw_frequency] if raw_frequency in frequency_labels else float(raw_frequency.replace(',','.'))
            entries.append(Dish(name=name,category=r.get('category') or r.get('Kategorie') or guess['category'],effort=effort,frequency_factor=frequency,tags=[t.strip() for t in (r.get('tags') or r.get('Tags') or '').split('|') if t.strip()],note=r.get('note') or r.get('Notiz') or ''))
        with db.transaction(True) as c:
            for d in entries: save_dish(c,d)
    except (ValueError,csv.Error) as e: raise HTTPException(422,f'CSV ungültig: {e}')
    return {'imported':len(entries)}

STATIC=Path(os.getenv('STATIC_DIR',str(Path(__file__).parents[1]/'frontend'/'dist')))
if STATIC.exists():
    app.mount('/assets',StaticFiles(directory=STATIC/'assets'),name='assets')
    @app.get('/{path:path}')
    def frontend(path:str):
        if path.startswith(('api/','calendar/')): raise HTTPException(404)
        candidate=(STATIC/path).resolve()
        if candidate.is_relative_to(STATIC.resolve()) and candidate.is_file(): return FileResponse(candidate,headers={'Cache-Control':'no-cache'})
        return FileResponse(STATIC/'index.html',headers={'Cache-Control':'no-cache'})
