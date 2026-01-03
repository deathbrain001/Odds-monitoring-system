import os
import requests
from flask import Flask, jsonify, render_template

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# ================= ENV =================
BETSAPI_TOKEN = os.getenv("BETSAPI_TOKEN")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

# ================= URLS =================
BETFAIR_INPLAY_URL = "https://api.b365api.com/v1/betfair/inplay"
BETFAIR_EVENT_URL = "https://api.b365api.com/v1/betfair/ex/event"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds"

# ================= MEMORY =================
previous_odds = {}

# ================= BETFAIR =================
def get_betfair_live_events():
    if not BETSAPI_TOKEN:
        return []

    try:
        r = requests.get(
            BETFAIR_INPLAY_URL,
            params={"token": BETSAPI_TOKEN},
            timeout=10
        )
        return r.json().get("results", [])
    except Exception:
        return []

def get_betfair_event_odds(event_id):
    try:
        r = requests.get(
            BETFAIR_EVENT_URL,
            params={"token": BETSAPI_TOKEN, "event_id": event_id},
            timeout=10
        )
        return r.json()
    except Exception:
        return {}

def parse_betfair_odds(event_json, event_id):
    output = []

    markets = event_json.get("results", [])
    if not markets:
        return output

    runners = markets[0].get("runners", [])

    for r in runners:
        name = r.get("name")
        ex = r.get("ex", {})

        backs = ex.get("availableToBack", [])
        lays = ex.get("availableToLay", [])

        if not backs or not lays:
            continue

        back_price = backs[0]["price"]
        lay_price = lays[0]["price"]

        key_back = f"{event_id}_{name}_back"
        key_lay = f"{event_id}_{name}_lay"

        prev_back = previous_odds.get(key_back, back_price)
        prev_lay = previous_odds.get(key_lay, lay_price)

        previous_odds[key_back] = back_price
        previous_odds[key_lay] = lay_price

        output.append({
            "team": name,
            "back": back_price,
            "lay": lay_price,
            "back_dir": "up" if back_price > prev_back else "down" if back_price < prev_back else "same",
            "lay_dir": "up" if lay_price > prev_lay else "down" if lay_price < prev_lay else "same",
            "source": "betfair"
        })

    return output

# ================= THE ODDS API =================
def get_oddsapi_live():
    if not ODDS_API_KEY:
        return []

    try:
        r = requests.get(
            ODDS_API_URL,
            params={
                "apiKey": ODDS_API_KEY,
                "regions": "uk",
                "markets": "h2h",
                "oddsFormat": "decimal"
            },
            timeout=10
        )
        data = r.json()
    except Exception:
        return []

    output = []

    for g in data:
        if not g.get("in_play", False):
            continue

        if not g.get("bookmakers"):
            continue

        outcomes = g["bookmakers"][0]["markets"][0]["outcomes"]

        for o in outcomes:
            output.append({
                "match": f"{g['home_team']} vs {g['away_team']}",
                "team": o["name"],
                "odds": o["price"],
                "source": "bookmaker"
            })

    return output

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/live")
def live_data():
    response = []

    # -------- BETFAIR --------
    betfair_events = get_betfair_live_events()
    for e in betfair_events[:10]:
        event_id = e.get("id")
        odds_json = get_betfair_event_odds(event_id)
        markets = parse_betfair_odds(odds_json, event_id)

        if markets:
            response.append({
                "match": f"{e.get('home')} vs {e.get('away')}",
                "markets": markets
            })

    # -------- THE ODDS API --------
    oddsapi_data = get_oddsapi_live()
    for o in oddsapi_data:
        response.append({
            "match": o["match"],
            "markets": [{
                "team": o["team"],
                "odds": o["odds"],
                "source": "bookmaker"
            }]
        })

    return jsonify(response)

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
