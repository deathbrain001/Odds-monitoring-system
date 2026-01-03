
import os, requests
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ODDS_API_KEY", "")
app = Flask(__name__)

FOOTBALL_API = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
CRICKET_API = "https://api.the-odds-api.com/v4/sports/cricket/odds"

previous = {}

def fetch_odds(url, limit=10):
    params = {
        "apiKey": API_KEY,
        "regions": "uk",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
    except Exception:
        return []

    result = []
    for g in data[:limit]:
        name = f"{g['home_team']} vs {g['away_team']}"
        odds = g["bookmakers"][0]["markets"][0]["outcomes"][0]["price"]
        last = previous.get(name, odds)
        change = round(((odds - last) / last) * 100, 2) if last else 0

        if abs(change) > 15:
            status = "alert"
        elif abs(change) > 5:
            status = "watch"
        else:
            status = "normal"

        previous[name] = odds
        result.append({
            "match": name,
            "odds": odds,
            "change": change,
            "status": status
        })
    return result

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/football")
def football():
    return jsonify(fetch_odds(FOOTBALL_API, 15))

@app.route("/api/cricket")
def cricket():
    data = fetch_odds(CRICKET_API, 10)
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
