import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Calculate absolute path to data/raw
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

# Make sure the data directory exists
os.makedirs(RAW_DIR, exist_ok=True)

SEED_URLS = [
    # Referees and Laws
    "https://www.theifab.com/laws/latest/the-field-of-play/",
    "https://www.theifab.com/laws/latest/the-ball/",
    "https://www.theifab.com/laws/latest/the-players/",
    "https://theifab.com/laws/latest/the-players-equipment/",
    "https://theifab.com/laws/latest/the-referee/",
    "https://theifab.com/laws/latest/the-other-match-officials/",
    "https://theifab.com/laws/latest/the-duration-of-the-match/",
    "https://theifab.com/laws/latest/the-start-and-restart-of-play/",
    "https://theifab.com/laws/latest/the-ball-in-and-out-of-play/",
    "https://www.theifab.com/laws/latest/video-assistant-referee-var-protocol/",
    "https://www.theifab.com/laws/latest/determining-the-outcome-of-a-match/",
    "https://www.theifab.com/laws/latest/offside/",
    "https://www.theifab.com/news/law-11-offside-deliberate-play-guidelines-clarified/",
    "https://www.theifab.com/laws/latest/fouls-and-misconduct/",
    "https://www.theifab.com/laws/latest/free-kicks/",
    "https://www.theifab.com/laws/latest/the-penalty-kick/",
    "http://theifab.com/laws/latest/the-throw-in/",
    "https://www.theifab.com/laws/latest/the-goal-kick/",
    "https://www.theifab.com/laws/latest/the-corner-kick/",

    # Football Analytics & Metrics
    "https://www.hudl.com/blog/expected-goals-xg-explained",
    "https://theanalyst.com/articles/what-are-expected-assists-xa",
    "https://www.skysports.com/football/news/11095/12829539/expected-goals-expected-assists-pressures-carries-high-turnovers-and-more-advanced-stats-explained",
    "https://theanalyst.com/articles/tottenham-problems-chances-created",
    "https://theanalyst.com/articles/braga-push-to-break-the-big-three-hegemony-in-portugal",
    "https://www.nytimes.com/athletic/2730755/2021/07/28/the-athletics-football-analytics-glossary-explaining-xg-ppda-field-tilt-and-how-to-use-them/",
    "https://blogarchive.statsbomb.com/articles/soccer/the-dual-life-of-expected-goals-part-1/",
    "https://blogarchive.statsbomb.com/articles/soccer/the-dual-life-of-expected-goals-part-2/",
    "https://english-programs.sportsdatacampus.com/important-football-metrics/",
    "https://planetefootball.com/guides/ppda-football-explained",
    "https://www.americansocceranalysis.com/home/2018/7/10/expected-possession-goals-the-value-of-a-possession-and-comparing-xpg-to-other-metrics",
    "https://datafield.dev/professional-soccer-analytics/part-02/chapter-09/",

    # Tactical Concepts
    "https://www.fourfourtwo.com/features/half-space-football-tactics-explained",
    "https://www.fourfourtwo.com/features/the-inverted-full-back-football-tactics-explained",
    "https://learning.coachesvoice.com/cv/in-focus-high-press/",
    "https://totalfootballanalysis.com/article/tactical-theory-the-low-standard-and-high-block-tactical-analysis-tactics",
    "https://totalfootballanalysis.com/article/tactical-analysis-identifying-the-best-moments-to-engage-opponents-tactical-analysis-tactics",
    "http://totalfootballanalysis.com/article/tactical-theory-a-comprehensive-guide-to-direct-possession-tactical-analysis-tactics",
    "https://spielverlagerung.com/glossary/tactical-methods/pressing/",
    "https://spielverlagerung.com/2017/03/05/pressing-counterpressing-and-counterattacking/",
    "https://totalfootballanalysis.com/",
    "https://www.bbc.com/sport/football/articles/c785rxj5gp2o",
    "https://learning.coachesvoice.com/cv/low-block-football-tactics-explained-simeone-dyche-mourinho/",
    "https://learning.coachesvoice.com/cv/4-3-3-football-tactics-explained-formation-liverpool-klopp-barcelona-guardiola/",
    "https://guidetofootball.com/tactics/4-3-3-formation/",
    "https://guidetofootball.com/tactics/4-2-3-1-formation/",
    "https://guidetofootball.com/tactics/4-4-2-formation/",
    "https://guidetofootball.com/tactics/football-tactics-explained/",
    "https://guidetofootball.com/tactics/formations/",
    "https://guidetofootball.com/tactics/3-5-2-formation/",
    "https://guidetofootball.com/tactics/3-4-3-formation/",
    "https://guidetofootball.com/tactics/playing-styles-and-systems/",
    "https://guidetofootball.com/tactics/attacking-football/",
    "https://guidetofootball.com/tactics/tiki-taka-and-pass-and-move/",
    "https://guidetofootball.com/tactics/counter-pressing/",
    "https://guidetofootball.com/tactics/direct-football/",
    "https://guidetofootball.com/tactics/target-man/",
    "https://guidetofootball.com/tactics/poacher/",
    "https://guidetofootball.com/tactics/false-nine/",
    "https://guidetofootball.com/tactics/winger-roles/",
    "https://guidetofootball.com/tactics/counter-attacking-football/",
    "https://guidetofootball.com/tactics/defensive-transitions/",
    "https://guidetofootball.com/tactics/defensive-football/",
    "https://guidetofootball.com/tactics/possession-football/",
    "https://guidetofootball.com/tactics/playing-out-from-the-back/",
    "https://guidetofootball.com/tactics/defensive-shape/",
    "https://guidetofootball.com/tactics/mid-block-press/",
    "https://guidetofootball.com/tactics/match-strategies/",
    "https://guidetofootball.com/tactics/game-management/",
    "https://guidetofootball.com/tactics/time-wasting/",

    # FIFA World Cup 2022/2026 Context & Technology
    "https://inside.fifa.com/innovation/world-cup-2022/semi-automated-offside-technology",
    "https://inside.fifa.com/innovation/news/offside-decisions-referee-body-cams-innovation-world-cup-2026",
    "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/gueye-pina-connected-ball-technology-leader-boards",
    "https://inside.fifa.com/innovation/world-cup-2022/video-assistant-referee-var",
    "https://inside.fifa.com/refereeing/news/collina-with-saot-we-can-make-quicker-and-more-accurate-decisions",
    "https://inside.fifa.com/tournaments/mens/worldcup/qatar2022/media-releases/introducing-al-hilm-the-official-match-ball-of-the-fifa-world-cup-qatar-2022-finals",
    "https://inside.fifa.com/innovation/innovating-the-game/football-data-ecosystem",

    # Match Analysis Examples
    "https://theanalyst.com/articles/japan-spain-2022-world-cup-stats",
    "https://theanalyst.com/articles/netherlands-2-2-argentina-world-cup-stats",
    "https://theanalyst.com/articles/morocco-portugal-2022-world-cup-stats",
    "https://breakingthelines.com/@keepit_tactical/argentina-vs-egypt-wc-2026-the-egyptian-miracle-that-lasted-80-minutes",
    "https://theanalyst.com/articles/argentina-vs-egypt-stats-world-cup-2026",
    "https://theanalyst.com/articles/spains-intensity-crushes-hype-france-attack-world-cup-stats",
    "https://theanalyst.com/articles/france-vs-england-stats-world-cup-2026-bronze-final"
]

def collect_data():
    for i, url in enumerate(SEED_URLS):
        print(f"Fetching {url}...")
        try:
            # 1. Fetch the page
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()

            # Fix: requests guesses the encoding from HTTP headers, and defaults
            # to ISO-8859-1 when the server doesn't declare a charset. Most of
            # these sites are actually UTF-8, so let requests sniff the real
            # encoding from the response content instead (avoids mojibake like
            # "â€¢" instead of "•").
            if response.encoding is None or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding

            # 2. Extract the text (You will need to improve this basic cleaning)
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else f"Document {i}"
            
            # 3. Create the document metadata
            doc = {
                "id": f"doc_{i:03d}",
                "url": url,
                "title": title.strip(),
                "collection_date": datetime.now().isoformat(),
                "raw_html": response.text # Save raw HTML for the cleaning phase later
            }
            
            # 4. Save to JSON in the data/raw folder
            file_path = os.path.join(RAW_DIR, f"{doc['id']}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=4)
                
            print(f"Saved {doc['id']} successfully.")
            
            # Sleep to be polite to servers
            time.sleep(2)
            
        except Exception as e:
            print(f"Error fetching {url}: {e}")

if __name__ == "__main__":
    collect_data()