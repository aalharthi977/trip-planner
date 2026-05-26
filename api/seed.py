#!/usr/bin/env python3
"""
Seed script — run once after first launch to create the admin account
and pre-load the Northern Italy & Dolomites sample trip.

Usage:
  docker exec trip-planner-api python seed.py
  docker exec trip-planner-api python seed.py --username admin --password yourpassword
"""
import sys, sqlite3, os, bcrypt
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "/data/trips.db")

def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt()).decode()

# ── Parse args ────────────────────────────────────────────
username = "admin"
password = "Planner123"
for i, arg in enumerate(sys.argv[1:]):
    if arg == "--username" and i+1 < len(sys.argv)-1: username = sys.argv[i+2]
    if arg == "--password" and i+1 < len(sys.argv)-1: password = sys.argv[i+2]

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys=ON")

# ── Create user ───────────────────────────────────────────
existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
if existing:
    user_id = existing[0]
    print(f"User '{username}' already exists (id={user_id}), skipping user creation.")
else:
    cur = conn.execute("INSERT INTO users (username, hashed_password, lang) VALUES (?,?,?)",
        (username, hash_pw(password), "en"))
    user_id = cur.lastrowid
    conn.commit()
    print(f"Created user '{username}' (id={user_id})")

# ── Check if Italy trip already exists ────────────────────
existing_trip = conn.execute(
    "SELECT id FROM trips WHERE user_id=? AND title=?",
    (user_id, "Northern Italy & The Dolomites")).fetchone()

if existing_trip:
    print("Sample trip already exists, skipping.")
    conn.close()
    sys.exit(0)

# ── Create Italy trip ─────────────────────────────────────
cur = conn.execute("""INSERT INTO trips
    (user_id,title,destination,start_date,end_date,budget,currency,notes,color,status,position)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
    (user_id, "Northern Italy & The Dolomites", "Northern Italy, Dolomites & Austria",
     "2025-06-01", "2025-06-11", 3500, "EUR",
     "Self-drive road trip. Car rental from Malpensa. Return to Malpensa on day 10.",
     "green", "planning", 0))
trip_id = cur.lastrowid
conn.commit()
print(f"Created trip 'Northern Italy & The Dolomites' (id={trip_id})")

# ── Day data ──────────────────────────────────────────────
DAYS = [
  {
    "num":1,"title":"Arrive Milan","tagline":"Navigli canals & first aperitivo",
    "region":"cities","drive":"","dont_miss":"",
    "callouts":[
      {"type":"car","icon":"car","text":"Park the car at your hotel and don't move it in Milan. ZTL cameras fine you automatically."},
      {"type":"cost","icon":"coin","text":"Malpensa Express €13 vs taxi €90 — same journey, €77 saved on day one."},
    ],
    "attractions":[
      {"name":"Navigli Canal District","meta":"Evening walk, aperitivo bars","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Navigli+Milan+Italy","icon":"anchor"},
      {"name":"Piazza del Duomo","meta":"Milan Cathedral & main square","cost":"Free / €5 rooftop","cost_type":"paid","maps_url":"https://maps.google.com/?q=Duomo+di+Milano","icon":"church"},
      {"name":"Brera District","meta":"Art galleries, cafes, boutiques","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Brera+Milan+Italy","icon":"palette"},
      {"name":"Malpensa Express","meta":"Airport → Centrale (50 min)","cost":"€13","cost_type":"paid","maps_url":"https://maps.google.com/?q=Milano+Centrale+Station","icon":"train"},
    ]
  },
  {
    "num":2,"title":"Milan → Lake Como → Riva del Garda",
    "tagline":"Bellagio by car, lakeside road, onward to Garda",
    "region":"lakes","drive":"Milan → Bellagio 1.5 hrs · Bellagio → Riva 2 hrs",
    "dont_miss":"The SS340 lakeside road — pull over at any lay-by. The views are the whole point.",
    "callouts":[
      {"type":"gem","icon":"gem","text":"Varenna for lunch: quieter than Bellagio, 30% cheaper food, identical lake views."},
      {"type":"cost","icon":"coin","text":"Stay in Riva 2 nights — accommodation 30–40% cheaper than south Garda."},
    ],
    "attractions":[
      {"name":"SS340 Lakeside Road","meta":"Como's scenic west shore drive","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=SS340+Lake+Como+Italy","icon":"car"},
      {"name":"Bellagio","meta":"Iconic lake town, stepped streets","cost":"Free to explore","cost_type":"free","maps_url":"https://maps.google.com/?q=Bellagio+Lake+Como+Italy","icon":"home"},
      {"name":"Varenna","meta":"Ferry across for lunch — quieter & cheaper","cost":"Ferry €5","cost_type":"paid","maps_url":"https://maps.google.com/?q=Varenna+Lake+Como+Italy","icon":"ship"},
      {"name":"Castello di Vezio","meta":"Castle ruins above the lake, 20 min hike","cost":"€4","cost_type":"paid","maps_url":"https://maps.google.com/?q=Castello+di+Vezio+Varenna+Italy","icon":"castle"},
      {"name":"Riva del Garda Lakefront","meta":"Arrive & stroll the promenade","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Riva+del+Garda+lakefront+Italy","icon":"anchor"},
    ]
  },
  {
    "num":3,"title":"Riva del Garda — Full Day",
    "tagline":"Cliffs, waterfalls & the best free trail in Italy",
    "region":"lakes","drive":"Base day — short drives only",
    "dont_miss":"Sentiero del Ponale — genuinely jaw-dropping and completely free. Don't skip it.",
    "callouts":[
      {"type":"gem","icon":"gem","text":"Arco: free castle, great espresso, completely authentic — almost unknown to tourists."},
    ],
    "attractions":[
      {"name":"Sentiero del Ponale","meta":"Cliffside trail, waterfalls, 45 min each way","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Sentiero+del+Ponale+Riva+del+Garda","icon":"mountain"},
      {"name":"Arco Castle","meta":"Medieval ruins on a rock spike — 20 min hike","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Castello+di+Arco+Italy","icon":"castle"},
      {"name":"Rocca di Riva Fortress","meta":"In-town fortress, rooftop lake views","cost":"€2","cost_type":"paid","maps_url":"https://maps.google.com/?q=Rocca+di+Riva+del+Garda","icon":"tower"},
      {"name":"Torbole Village","meta":"Best sunset angle, 3 km east","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Torbole+sul+Garda+Italy","icon":"sunset"},
      {"name":"Kayak Rental, Riva Harbour","meta":"Paddle toward the waterfall cave","cost":"~€15/hr","cost_type":"paid","maps_url":"https://maps.google.com/?q=Riva+del+Garda+harbour+Italy","icon":"kayak"},
    ]
  },
  {
    "num":4,"title":"Riva → Trento → Val Gardena (Ortisei)",
    "tagline":"Into the Dolomites via Trento",
    "region":"dolomites","drive":"Riva → Trento 45 min · Trento → Ortisei 1.5 hrs",
    "dont_miss":"",
    "callouts":[
      {"type":"dont","icon":"star","text":"Don't miss: Seceda ridgeline at golden hour — the Geisler peaks turn deep orange."},
      {"type":"car","icon":"car","text":"Seceda cable car closes ~5:30pm. Arrive by 4pm."},
    ],
    "attractions":[
      {"name":"Piazza del Duomo, Trento","meta":"Beautiful cathedral square, coffee stop","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Piazza+Duomo+Trento+Italy","icon":"church"},
      {"name":"Castelrotto (Kastelruth)","meta":"Tyrolean village, charming main square","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Castelrotto+South+Tyrol+Italy","icon":"home"},
      {"name":"Seceda Cable Car","meta":"Most iconic Dolomite ridgeline view","cost":"€30 return","cost_type":"paid","maps_url":"https://maps.google.com/?q=Seceda+Urtijei+Val+Gardena+Italy","icon":"gondola"},
      {"name":"Ortisei Town Centre","meta":"Val Gardena's main village","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Ortisei+Val+Gardena+Italy","icon":"home"},
    ]
  },
  {
    "num":5,"title":"Val Gardena — Alpe di Siusi & Passes",
    "tagline":"Europe's largest Alpine meadow + great road passes",
    "region":"dolomites","drive":"Short drives — all within 30 min of Ortisei",
    "dont_miss":"The view from Alpe di Siusi back down over Val Gardena — you'll stop walking and just stare.",
    "callouts":[
      {"type":"warn","icon":"clock","text":"Alpe di Siusi road closed 9am–5pm. Leave by 8am."},
      {"type":"cost","icon":"coin","text":"Pack your own lunch — rifugio meals €15–18 per dish."},
      {"type":"gem","icon":"gem","text":"Passo Sella at dusk — the massifs glow pink and amber."},
    ],
    "attractions":[
      {"name":"Alpe di Siusi (Seiser Alm)","meta":"Drive up before 9am — road closes 9am–5pm","cost":"Free / €18 cable car","cost_type":"free","maps_url":"https://maps.google.com/?q=Alpe+di+Siusi+Seiser+Alm+Italy","icon":"mountain"},
      {"name":"Panorama Trail Loop","meta":"4–5 hrs, moderate — Sassolungo backdrop","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Panorama+Trail+Alpe+di+Siusi+Italy","icon":"walk"},
      {"name":"Rifugio Compatsch","meta":"Mountain hut lunch at 2000m","cost":"€12–18/dish","cost_type":"paid","maps_url":"https://maps.google.com/?q=Rifugio+Compatsch+Alpe+di+Siusi","icon":"coffee"},
      {"name":"Passo Sella","meta":"Great Dolomite road pass","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Passo+Sella+Dolomites+Italy","icon":"road"},
      {"name":"Passo Gardena","meta":"Second great pass — equally dramatic","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Passo+Gardena+Dolomites+Italy","icon":"road"},
    ]
  },
  {
    "num":6,"title":"Val Gardena → Tre Cime → San Candido",
    "tagline":"The Dolomites' most iconic landmark",
    "region":"dolomites","drive":"Ortisei → Misurina 1.5 hrs · Misurina → Tre Cime 20 min",
    "dont_miss":"Tre Cime from the north side — three towers framed against the sky.",
    "callouts":[
      {"type":"warn","icon":"clock","text":"Arrive at Tre Cime toll gate before 9am — fills by 9:30am."},
      {"type":"gem","icon":"gem","text":"Lake Misurina — free, 10 min off-route, one of Italy's most beautiful lakes."},
    ],
    "attractions":[
      {"name":"Lake Misurina","meta":"Mirror reflections of the Dolomites","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Lago+di+Misurina+Italy","icon":"drop"},
      {"name":"Tre Cime di Lavaredo","meta":"The 3 iconic rock towers — circuit loop 9km","cost":"€30 toll road","cost_type":"paid","maps_url":"https://maps.google.com/?q=Tre+Cime+di+Lavaredo+Italy","icon":"mountain"},
      {"name":"Rifugio Auronzo","meta":"Drive-up base at 2333m","cost":"Included in toll","cost_type":"free","maps_url":"https://maps.google.com/?q=Rifugio+Auronzo+Tre+Cime+Italy","icon":"home"},
      {"name":"San Candido (Innichen)","meta":"Charming Tyrolean town, overnight","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=San+Candido+South+Tyrol+Italy","icon":"home"},
      {"name":"Collegiate Church of San Candido","meta":"12th century Romanesque — hidden gem","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Collegiate+Church+San+Candido+Italy","icon":"church"},
    ]
  },
  {
    "num":7,"title":"San Candido → Innsbruck",
    "tagline":"Cross the Brenner, Tyrolean capital",
    "region":"austria","drive":"San Candido → Innsbruck 1.5 hrs via Brenner Pass",
    "dont_miss":"The view from Nordkette looking down over Innsbruck and the Inn valley.",
    "callouts":[
      {"type":"cost","icon":"coin","text":"Austrian food 20–30% cheaper than Italian tourist areas."},
      {"type":"car","icon":"car","text":"Park at Marktplatz garage (€2/hr) — don't drive into the pedestrian zone."},
    ],
    "attractions":[
      {"name":"Brenner Pass","meta":"Dramatic mountain border crossing","cost":"€12 toll","cost_type":"paid","maps_url":"https://maps.google.com/?q=Brenner+Pass+Austria+Italy+border","icon":"road"},
      {"name":"Golden Roof (Goldenes Dachl)","meta":"Innsbruck's iconic landmark","cost":"Free to view / €5 museum","cost_type":"free","maps_url":"https://maps.google.com/?q=Goldenes+Dachl+Innsbruck+Austria","icon":"building"},
      {"name":"Hofburg Palace","meta":"Imperial palace, grand interiors","cost":"€9.50","cost_type":"paid","maps_url":"https://maps.google.com/?q=Hofburg+Innsbruck+Austria","icon":"castle"},
      {"name":"Nordkette Cable Car","meta":"City centre to 2300m in 20 min","cost":"€40 return","cost_type":"paid","maps_url":"https://maps.google.com/?q=Nordkette+Innsbruck+Austria","icon":"gondola"},
      {"name":"Maria-Theresien-Strasse","meta":"Main boulevard, free to stroll","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Maria+Theresien+Strasse+Innsbruck+Austria","icon":"walk"},
      {"name":"Bergisel Ski Jump","meta":"Zaha Hadid architecture, panoramic deck","cost":"€8","cost_type":"paid","maps_url":"https://maps.google.com/?q=Bergisel+Ski+Jump+Innsbruck+Austria","icon":"chart"},
    ]
  },
  {
    "num":8,"title":"Innsbruck → Verona",
    "tagline":"Romeo, Juliet, Roman arenas & great wine",
    "region":"cities","drive":"Innsbruck → Verona 2.5 hrs via Brenner",
    "dont_miss":"The Roman Arena interior — one of the best-preserved in the world.",
    "callouts":[
      {"type":"car","icon":"car","text":"Park at Parcheggio Arsenale outside ZTL (€1.50/hr) — 15 min walk to the Arena."},
      {"type":"cost","icon":"coin","text":"Verona much cheaper than Venice or Florence — good meals with wine €18–25."},
    ],
    "attractions":[
      {"name":"Verona Arena","meta":"2,000-year-old Roman amphitheatre","cost":"€10","cost_type":"paid","maps_url":"https://maps.google.com/?q=Arena+di+Verona+Italy","icon":"circus"},
      {"name":"Juliet's House","meta":"Balcony & courtyard","cost":"Courtyard free / Balcony €6","cost_type":"free","maps_url":"https://maps.google.com/?q=Casa+di+Giulietta+Verona+Italy","icon":"heart"},
      {"name":"Piazza delle Erbe","meta":"Best aperitivo square in Verona","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Piazza+delle+Erbe+Verona+Italy","icon":"glass"},
      {"name":"Castelvecchio & Bridge","meta":"Medieval castle + bridge, sunset walk","cost":"Free / €6 museum","cost_type":"free","maps_url":"https://maps.google.com/?q=Castelvecchio+Verona+Italy","icon":"bridge"},
      {"name":"Piazza Bra","meta":"Grand square encircling the Arena","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Piazza+Bra+Verona+Italy","icon":"anchor"},
      {"name":"Lamberti Tower","meta":"Best rooftop views over Verona","cost":"€8","cost_type":"paid","maps_url":"https://maps.google.com/?q=Torre+dei+Lamberti+Verona+Italy","icon":"tower"},
    ]
  },
  {
    "num":9,"title":"Verona — Choose Your Day",
    "tagline":"Venice, wine country, or Lake Garda south",
    "region":"cities","drive":"Depends on choice",
    "dont_miss":"",
    "callouts":[
      {"type":"cost","icon":"coin","text":"Venice as a day trip saves €150–250 vs overnight."},
      {"type":"car","icon":"car","text":"For Venice: leave the car at Verona hotel, take the train."},
    ],
    "attractions":[
      {"name":"Venice — St. Mark's Basilica","meta":"Day trip by train (1h15, €15 return)","cost":"€3 / Free outside","cost_type":"paid","maps_url":"https://maps.google.com/?q=St+Marks+Basilica+Venice+Italy","icon":"church"},
      {"name":"Venice — Rialto Bridge","meta":"Iconic bridge + morning market","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Rialto+Bridge+Venice+Italy","icon":"bridge"},
      {"name":"Valpolicella Wine Region","meta":"Free cantina tastings, Amarone country","cost":"Free tastings","cost_type":"free","maps_url":"https://maps.google.com/?q=Valpolicella+Verona+Italy","icon":"wine"},
      {"name":"Sirmione & Scaliger Castle","meta":"Lake Garda south — castle on the water","cost":"€8","cost_type":"paid","maps_url":"https://maps.google.com/?q=Castello+Scaligero+Sirmione+Italy","icon":"castle"},
      {"name":"Bardolino Village","meta":"Local wine, zero crowds, lake views","cost":"Free","cost_type":"free","maps_url":"https://maps.google.com/?q=Bardolino+Lake+Garda+Italy","icon":"anchor"},
      {"name":"Giardino Giusti","meta":"Renaissance garden — rest day option","cost":"€10","cost_type":"paid","maps_url":"https://maps.google.com/?q=Giardino+Giusti+Verona+Italy","icon":"plant"},
    ]
  },
  {
    "num":10,"title":"Verona → Milan → Home",
    "tagline":"Final morning, relaxed return",
    "region":"transit","drive":"Verona → Malpensa 1h45 via A4",
    "dont_miss":"",
    "callouts":[
      {"type":"cost","icon":"coin","text":"Return at Malpensa (same pickup) to avoid one-way surcharges of €150–200."},
      {"type":"warn","icon":"clock","text":"Leave Verona 3.5 hrs before your flight."},
    ],
    "attractions":[
      {"name":"A4 Motorway to Milan","meta":"Straightforward final drive","cost":"~€12 toll","cost_type":"paid","maps_url":"https://maps.google.com/?q=A4+Motorway+Verona+to+Milan+Italy","icon":"road"},
      {"name":"Malpensa Airport Car Return","meta":"Return car, same pickup point","cost":"No one-way fee","cost_type":"free","maps_url":"https://maps.google.com/?q=Milan+Malpensa+Airport+Italy","icon":"plane"},
    ]
  },
]

# ── Insert days, attractions, callouts ────────────────────
for pos, day in enumerate(DAYS):
    cur = conn.execute("""INSERT INTO days
        (trip_id,num,title,tagline,region,drive,dont_miss,position)
        VALUES (?,?,?,?,?,?,?,?)""",
        (trip_id, day["num"], day["title"], day["tagline"],
         day["region"], day["drive"], day["dont_miss"], pos))
    day_id = cur.lastrowid

    for apos, a in enumerate(day["attractions"]):
        conn.execute("""INSERT INTO attractions
            (day_id,name,meta,cost,cost_type,maps_url,icon,position)
            VALUES (?,?,?,?,?,?,?,?)""",
            (day_id, a["name"], a["meta"], a["cost"],
             a["cost_type"], a["maps_url"], a["icon"], apos))

    for cpos, c in enumerate(day.get("callouts",[])):
        conn.execute("""INSERT INTO callouts (day_id,type,icon,text,position)
            VALUES (?,?,?,?,?)""",
            (day_id, c["type"], c["icon"], c["text"], cpos))

conn.commit()
conn.close()
print(f"Seeded {len(DAYS)} days with all attractions and callouts.")
print(f"\nLogin credentials:")
print(f"  Username: {username}")
print(f"  Password: {password}")
print(f"\nChange your password after first login!")
