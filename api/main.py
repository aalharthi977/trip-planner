import os, sqlite3, json
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
import bcrypt as _bcrypt

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-please")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
DB_PATH = os.getenv("DB_PATH", "/data/trips.db")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

app = FastAPI(title="Masar API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"], expose_headers=["*"])

# ── DB ────────────────────────────────────────────────────
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try: yield conn
    finally: conn.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        lang TEXT DEFAULT 'en',
        theme TEXT DEFAULT 'dark',
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        destination TEXT DEFAULT '',
        start_date TEXT DEFAULT '',
        end_date TEXT DEFAULT '',
        budget REAL DEFAULT 0,
        currency TEXT DEFAULT 'EUR',
        notes TEXT DEFAULT '',
        color TEXT DEFAULT 'blue',
        status TEXT DEFAULT 'planning',
        is_public INTEGER DEFAULT 0,
        position INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS days (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
        num INTEGER DEFAULT 1,
        title TEXT NOT NULL,
        tagline TEXT DEFAULT '',
        region TEXT DEFAULT 'cities',
        drive TEXT DEFAULT '',
        dont_miss TEXT DEFAULT '',
        position INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS attractions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_id INTEGER NOT NULL REFERENCES days(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        meta TEXT DEFAULT '',
        cost TEXT DEFAULT '',
        cost_type TEXT DEFAULT 'free',
        maps_url TEXT DEFAULT '',
        icon TEXT DEFAULT 'map',
        position INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_id INTEGER NOT NULL REFERENCES days(id) ON DELETE CASCADE,
        text TEXT NOT NULL,
        position INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS callouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_id INTEGER NOT NULL REFERENCES days(id) ON DELETE CASCADE,
        type TEXT DEFAULT 'info',
        icon TEXT DEFAULT 'info',
        text TEXT NOT NULL,
        position INTEGER DEFAULT 0
    );
    """)
    # Add missing columns if upgrading
    try: conn.execute("ALTER TABLE trips ADD COLUMN is_public INTEGER DEFAULT 0")
    except: pass
    try: conn.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'dark'")
    except: pass
    conn.commit()
    conn.close()

# ── AUTH ─────────────────────────────────────────────────
def verify_password(plain, hashed):
    try: return _bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except: return False

def hash_password(pw):
    return _bcrypt.hashpw(pw.encode()[:72], _bcrypt.gensalt()).decode()

def create_token(data: dict):
    exp = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {**data, "exp": exp}
    if "sub" in payload: payload["sub"] = str(payload["sub"])
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    exc = HTTPException(status_code=401, detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None: raise exc
        user_id = int(user_id)
    except (JWTError, ValueError, TypeError): raise exc
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    finally: conn.close()
    if row is None: raise exc
    return dict(row)

def get_optional_user(token: Optional[str] = Depends(oauth2_optional)):
    if not token: return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try: row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        finally: conn.close()
        return dict(row) if row else None
    except: return None

# ── SCHEMAS ───────────────────────────────────────────────
class UserRegister(BaseModel):
    username: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    lang: str
    theme: str

class LangUpdate(BaseModel):
    lang: str

class ThemeUpdate(BaseModel):
    theme: str

class TripIn(BaseModel):
    title: str
    destination: str = ""
    start_date: str = ""
    end_date: str = ""
    budget: float = 0
    currency: str = "EUR"
    notes: str = ""
    color: str = "blue"
    status: str = "planning"
    is_public: bool = False

class DayIn(BaseModel):
    num: int = 1
    title: str
    tagline: str = ""
    region: str = "cities"
    drive: str = ""
    dont_miss: str = ""
    position: int = 0

class AttrIn(BaseModel):
    name: str
    meta: str = ""
    cost: str = ""
    cost_type: str = "free"
    maps_url: str = ""
    icon: str = "map"
    position: int = 0

class NoteIn(BaseModel):
    text: str
    position: int = 0

class CalloutIn(BaseModel):
    type: str = "info"
    icon: str = "info"
    text: str
    position: int = 0

class ReorderIn(BaseModel):
    ids: List[int]

# ── HELPERS ───────────────────────────────────────────────
def get_full_days(trip_id, db):
    days = [dict(r) for r in db.execute(
        "SELECT * FROM days WHERE trip_id=? ORDER BY position, num", (trip_id,)).fetchall()]
    for day in days:
        day["attractions"] = [dict(r) for r in db.execute(
            "SELECT * FROM attractions WHERE day_id=? ORDER BY position", (day["id"],)).fetchall()]
        day["notes"] = [dict(r) for r in db.execute(
            "SELECT * FROM notes WHERE day_id=? ORDER BY position", (day["id"],)).fetchall()]
        day["callouts"] = [dict(r) for r in db.execute(
            "SELECT * FROM callouts WHERE day_id=? ORDER BY position", (day["id"],)).fetchall()]
    return days

def check_trip_owner(trip_id, user_id, db):
    row = db.execute("SELECT id FROM trips WHERE id=? AND user_id=?", (trip_id, user_id)).fetchone()
    if not row: raise HTTPException(404, "Trip not found")

# ── AUTH ROUTES ───────────────────────────────────────────
@app.post("/api/auth/register", response_model=TokenOut)
def register(body: UserRegister, db=Depends(get_db)):
    if db.execute("SELECT id FROM users WHERE username=?", (body.username,)).fetchone():
        raise HTTPException(400, "Username already taken")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    cur = db.execute("INSERT INTO users (username, hashed_password) VALUES (?,?)",
        (body.username.strip(), hash_password(body.password)))
    db.commit()
    token = create_token({"sub": cur.lastrowid})
    return TokenOut(access_token=token, user_id=cur.lastrowid, username=body.username, lang="en", theme="dark")

@app.post("/api/auth/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    row = db.execute("SELECT * FROM users WHERE username=?", (form.username,)).fetchone()
    if not row or not verify_password(form.password, row["hashed_password"]):
        raise HTTPException(401, "Incorrect username or password")
    token = create_token({"sub": row["id"]})
    return TokenOut(access_token=token, user_id=row["id"], username=row["username"],
        lang=row["lang"], theme=row["theme"] or "dark")

@app.patch("/api/auth/lang")
def update_lang(body: LangUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("UPDATE users SET lang=? WHERE id=?", (body.lang, user["id"]))
    db.commit(); return {"ok": True}

@app.patch("/api/auth/theme")
def update_theme(body: ThemeUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("UPDATE users SET theme=? WHERE id=?", (body.theme, user["id"]))
    db.commit(); return {"ok": True}

@app.get("/api/auth/me")
def me(user=Depends(get_current_user)):
    return {"id": user["id"], "username": user["username"], "lang": user["lang"], "theme": user.get("theme","dark")}

# ── PUBLIC ROUTES (no auth) ───────────────────────────────
@app.get("/api/public/trips")
def public_trips(db=Depends(get_db)):
    rows = db.execute("""
        SELECT t.*, u.username,
          (SELECT COUNT(*) FROM days WHERE trip_id=t.id) as day_count
        FROM trips t JOIN users u ON t.user_id=u.id
        WHERE t.is_public=1
        ORDER BY t.updated_at DESC
    """).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/public/trips/{trip_id}")
def public_trip_detail(trip_id: int, db=Depends(get_db)):
    row = db.execute("""
        SELECT t.*, u.username FROM trips t JOIN users u ON t.user_id=u.id
        WHERE t.id=? AND t.is_public=1
    """, (trip_id,)).fetchone()
    if not row: raise HTTPException(404, "Trip not found or not public")
    trip = dict(row)
    trip["days"] = get_full_days(trip_id, db)
    return trip

# ── TRIP ROUTES ───────────────────────────────────────────
@app.get("/api/trips")
def list_trips(user=Depends(get_current_user), db=Depends(get_db)):
    rows = db.execute("""
        SELECT t.*, (SELECT COUNT(*) FROM days WHERE trip_id=t.id) as day_count
        FROM trips t WHERE user_id=? ORDER BY position, created_at DESC
    """, (user["id"],)).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/trips", status_code=201)
def create_trip(body: TripIn, user=Depends(get_current_user), db=Depends(get_db)):
    pos = db.execute("SELECT COALESCE(MAX(position),0)+1 FROM trips WHERE user_id=?",
        (user["id"],)).fetchone()[0]
    cur = db.execute("""INSERT INTO trips
        (user_id,title,destination,start_date,end_date,budget,currency,notes,color,status,is_public,position)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user["id"], body.title, body.destination, body.start_date, body.end_date,
         body.budget, body.currency, body.notes, body.color, body.status, 1 if body.is_public else 0, pos))
    db.commit()
    row = db.execute("SELECT *,(SELECT COUNT(*) FROM days WHERE trip_id=?) as day_count FROM trips WHERE id=?",
        (cur.lastrowid, cur.lastrowid)).fetchone()
    return dict(row)

@app.get("/api/trips/{trip_id}")
def get_trip(trip_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    row = db.execute("SELECT * FROM trips WHERE id=? AND user_id=?", (trip_id, user["id"])).fetchone()
    if not row: raise HTTPException(404)
    return dict(row)

@app.put("/api/trips/{trip_id}")
def update_trip(trip_id: int, body: TripIn, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    db.execute("""UPDATE trips SET title=?,destination=?,start_date=?,end_date=?,
        budget=?,currency=?,notes=?,color=?,status=?,is_public=?,updated_at=datetime('now') WHERE id=?""",
        (body.title, body.destination, body.start_date, body.end_date,
         body.budget, body.currency, body.notes, body.color, body.status,
         1 if body.is_public else 0, trip_id))
    db.commit()
    return dict(db.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone())

@app.delete("/api/trips/{trip_id}", status_code=204)
def delete_trip(trip_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    db.execute("DELETE FROM trips WHERE id=? AND user_id=?", (trip_id, user["id"]))
    db.commit()

@app.post("/api/trips/reorder")
def reorder_trips(body: ReorderIn, user=Depends(get_current_user), db=Depends(get_db)):
    for pos, tid in enumerate(body.ids):
        db.execute("UPDATE trips SET position=? WHERE id=? AND user_id=?", (pos, tid, user["id"]))
    db.commit(); return {"ok": True}

# ── DAY ROUTES ────────────────────────────────────────────
@app.get("/api/trips/{trip_id}/days")
def list_days(trip_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    return get_full_days(trip_id, db)

@app.post("/api/trips/{trip_id}/days", status_code=201)
def create_day(trip_id: int, body: DayIn, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    pos = db.execute("SELECT COALESCE(MAX(position),0)+1 FROM days WHERE trip_id=?", (trip_id,)).fetchone()[0]
    cur = db.execute("INSERT INTO days (trip_id,num,title,tagline,region,drive,dont_miss,position) VALUES (?,?,?,?,?,?,?,?)",
        (trip_id, body.num, body.title, body.tagline, body.region, body.drive, body.dont_miss, pos))
    db.commit()
    day = dict(db.execute("SELECT * FROM days WHERE id=?", (cur.lastrowid,)).fetchone())
    day["attractions"]=[]; day["notes"]=[]; day["callouts"]=[]
    return day

@app.put("/api/trips/{trip_id}/days/{day_id}")
def update_day(trip_id: int, day_id: int, body: DayIn, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    db.execute("UPDATE days SET num=?,title=?,tagline=?,region=?,drive=?,dont_miss=?,position=? WHERE id=? AND trip_id=?",
        (body.num, body.title, body.tagline, body.region, body.drive, body.dont_miss, body.position, day_id, trip_id))
    db.commit(); return {"ok": True}

@app.delete("/api/trips/{trip_id}/days/{day_id}", status_code=204)
def delete_day(trip_id: int, day_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    db.execute("DELETE FROM days WHERE id=? AND trip_id=?", (day_id, trip_id))
    db.commit()

@app.post("/api/trips/{trip_id}/days/reorder")
def reorder_days(trip_id: int, body: ReorderIn, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    for pos, did in enumerate(body.ids):
        db.execute("UPDATE days SET position=? WHERE id=? AND trip_id=?", (pos, did, trip_id))
    db.commit(); return {"ok": True}

# ── ATTRACTION ROUTES ─────────────────────────────────────
def check_day(day_id, trip_id, db):
    row = db.execute("SELECT id FROM days WHERE id=? AND trip_id=?", (day_id, trip_id)).fetchone()
    if not row: raise HTTPException(404, "Day not found")

@app.post("/api/trips/{trip_id}/days/{day_id}/attractions", status_code=201)
def create_attr(trip_id: int, day_id: int, body: AttrIn, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db); check_day(day_id, trip_id, db)
    pos = db.execute("SELECT COALESCE(MAX(position),0)+1 FROM attractions WHERE day_id=?", (day_id,)).fetchone()[0]
    cur = db.execute("INSERT INTO attractions (day_id,name,meta,cost,cost_type,maps_url,icon,position) VALUES (?,?,?,?,?,?,?,?)",
        (day_id, body.name, body.meta, body.cost, body.cost_type, body.maps_url, body.icon, pos))
    db.commit()
    return dict(db.execute("SELECT * FROM attractions WHERE id=?", (cur.lastrowid,)).fetchone())

@app.put("/api/trips/{trip_id}/days/{day_id}/attractions/{attr_id}")
def update_attr(trip_id: int, day_id: int, attr_id: int, body: AttrIn, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    db.execute("UPDATE attractions SET name=?,meta=?,cost=?,cost_type=?,maps_url=?,icon=?,position=? WHERE id=? AND day_id=?",
        (body.name, body.meta, body.cost, body.cost_type, body.maps_url, body.icon, body.position, attr_id, day_id))
    db.commit(); return {"ok": True}

@app.delete("/api/trips/{trip_id}/days/{day_id}/attractions/{attr_id}", status_code=204)
def delete_attr(trip_id: int, day_id: int, attr_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    db.execute("DELETE FROM attractions WHERE id=? AND day_id=?", (attr_id, day_id))
    db.commit()

# ── NOTE ROUTES ───────────────────────────────────────────
@app.post("/api/trips/{trip_id}/days/{day_id}/notes", status_code=201)
def create_note(trip_id: int, day_id: int, body: NoteIn, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db); check_day(day_id, trip_id, db)
    pos = db.execute("SELECT COALESCE(MAX(position),0)+1 FROM notes WHERE day_id=?", (day_id,)).fetchone()[0]
    cur = db.execute("INSERT INTO notes (day_id,text,position) VALUES (?,?,?)", (day_id, body.text, pos))
    db.commit()
    return dict(db.execute("SELECT * FROM notes WHERE id=?", (cur.lastrowid,)).fetchone())

@app.put("/api/trips/{trip_id}/days/{day_id}/notes/{note_id}")
def update_note(trip_id: int, day_id: int, note_id: int, body: NoteIn, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    db.execute("UPDATE notes SET text=?,position=? WHERE id=? AND day_id=?", (body.text, body.position, note_id, day_id))
    db.commit(); return {"ok": True}

@app.delete("/api/trips/{trip_id}/days/{day_id}/notes/{note_id}", status_code=204)
def delete_note(trip_id: int, day_id: int, note_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    db.execute("DELETE FROM notes WHERE id=? AND day_id=?", (note_id, day_id))
    db.commit()

# ── CALLOUT ROUTES ────────────────────────────────────────
@app.post("/api/trips/{trip_id}/days/{day_id}/callouts", status_code=201)
def create_callout(trip_id: int, day_id: int, body: CalloutIn, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db); check_day(day_id, trip_id, db)
    pos = db.execute("SELECT COALESCE(MAX(position),0)+1 FROM callouts WHERE day_id=?", (day_id,)).fetchone()[0]
    cur = db.execute("INSERT INTO callouts (day_id,type,icon,text,position) VALUES (?,?,?,?,?)",
        (day_id, body.type, body.icon, body.text, pos))
    db.commit()
    return dict(db.execute("SELECT * FROM callouts WHERE id=?", (cur.lastrowid,)).fetchone())

@app.delete("/api/trips/{trip_id}/days/{day_id}/callouts/{callout_id}", status_code=204)
def delete_callout(trip_id: int, day_id: int, callout_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    check_trip_owner(trip_id, user["id"], db)
    db.execute("DELETE FROM callouts WHERE id=? AND day_id=?", (callout_id, day_id))
    db.commit()

# ── HEALTH ────────────────────────────────────────────────
@app.get("/api/health")
def health(): return {"status": "ok"}

@app.on_event("startup")
def startup(): init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8092, reload=False)
