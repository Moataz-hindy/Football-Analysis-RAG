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
    "https://breakingthelines.com/@keepit_tactical/argentina-vs-egypt-wc-2026-the-egyptian-miracle-that-lasted-80-minutes",
    "https://theanalyst.com/articles/qatar-ecuador-stats-world-cup-2022",
    "https://theanalyst.com/articles/england-iran-world-cup-2022",
    "https://theanalyst.com/articles/netherlands-senegal-world-cup-2022-stats",
    "https://theanalyst.com/articles/united-states-wales-world-cup-2022-stats",
    "https://theanalyst.com/articles/argentina-saudi-arabia-world-cup-2022-stats",
    "https://theanalyst.com/articles/denmark-tunisia-stats-world-cup-2022",
    "https://theanalyst.com/articles/mexico-poland-stats-world-cup-2022",
    "https://theanalyst.com/articles/france-australia-world-cup-2022-stats",
    "https://theanalyst.com/articles/croatia-morocco-world-cup-2022-stats",
    "https://theanalyst.com/articles/germany-japan-world-cup-2022-stats",
    "https://theanalyst.com/2022/11/spain-vs-costa-rica-world-cup-stats/",
    "https://theanalyst.com/articles/belgium-canada-world-cup-2022-stats",
    "https://theanalyst.com/articles/switzerland-cameroon-world-cup-2022-stats",
    "https://theanalyst.com/articles/uruguay-south-korea-world-cup-stats",
    "https://theanalyst.com/articles/portugal-ghana-2022-world-cup-stats",
    "https://theanalyst.com/articles/brazil-2-0-serbia",
    "https://theanalyst.com/articles/wales-0-2-iran-world-cup",
    "https://theanalyst.com/articles/qatar-1-3-senegal-lions-of-teranga-cruise-past-spirited-qatar",
    "https://theanalyst.com/articles/netherlands-ecuador-world-cup-2022-stats",
    "https://theanalyst.com/articles/england-united-states-2022-world-cup-stats",
    "https://theanalyst.com/articles/tunisia-0-1-australia-battling-socceroos-are-still-in-this-world-cup",
    "https://theanalyst.com/articles/poland-2-0-saudi-arabia",
    "https://theanalyst.com/articles/france-2-1-denmark-kylian-mbappe-steps-on-the-accelerator",
    "https://theanalyst.com/articles/argentina-mexico-2022-world-cup-stats",
    "https://theanalyst.com/articles/japan-costa-rica-stats-world-cup",
    "https://theanalyst.com/articles/belgium-0-2-morocco-stats-world-cup",
    "https://theanalyst.com/articles/croatia-canada-2022-world-cup-stats",
    "https://theanalyst.com/articles/spain-1-1-germany-substitute-strikers-serve-up-the-narrative",
    "https://theanalyst.com/articles/serbia-3-3-cameroon-stats-world-cup-2022",
    "https://theanalyst.com/articles/south-korea-2-3-ghana-world-cup-stats",
    "https://theanalyst.com/articles/brazil-1-0-switzerland-favourites-through-to-last-16-for-14th-straight-world-cup",
    "https://theanalyst.com/articles/uruguay-0-2-portugal-world-cup-2022-stats",
    "https://theanalyst.com/articles/netherlands-2-0-qatar-world-cup-stats",
    "https://theanalyst.com/articles/ecuador-1-2-senegal-lions-of-teranga-roar-into-last-16",
    "https://theanalyst.com/2022/11/wales-0-3-england-stats",
    "https://theanalyst.com/articles/iran-usa-world-cup-2022-stats",
    "https://theanalyst.com/articles/australia-denmark-2022-world-cup-stats",
    "https://theanalyst.com/articles/tunisia-france-world-cup-2022-stats",
    "https://theanalyst.com/articles/saudi-arabia-1-2-mexico-stats-world-cup",
    "https://theanalyst.com/articles/poland-0-2-argentina-polands-do-nothing-approach-pays-dividends",
    "https://theanalyst.com/articles/croatia-0-0-belgium-times-up-for-belgiums-olden-generation",
    "https://theanalyst.com/articles/canada-1-2-morocco",
    "https://theanalyst.com/articles/japan-spain-2022-world-cup-stats",
    "https://theanalyst.com/articles/south-korea-2-1-portugal-hwang-hee-chan-heroics-send-south-korea-through",
    "https://theanalyst.com/articles/ghana-0-2-uruguay-stats-world-cup",
    "https://theanalyst.com/2022/12/cameroon-brazil-2022-world-cup-stats",
    "https://theanalyst.com/articles/serbia-2-3-switzerland-opta-report",
    "https://theanalyst.com/articles/netherlands-united-states-2022-world-cup-stats",
    "https://theanalyst.com/articles/argentina-australia-world-cup-2022-stats",
    "https://theanalyst.com/articles/france-poland-2022-world-cup-stats",
    "https://theanalyst.com/articles/england-3-0-senegal",
    "https://theanalyst.com/articles/japan-1-1-croatia-penalty-masters-croatia-prevail-on-spot-kicks-once-again",
    "https://theanalyst.com/articles/brazil-4-1-korea-brazilian-masterclass",
    "https://theanalyst.com/articles/morocco-spain-more-penalty-pain-for-spain",
    "https://theanalyst.com/articles/portugal-6-1-switzerland-2022-world-cup-stats",
    "https://theanalyst.com/articles/croatia-1-1-brazil-world-cup-stats",
    "https://theanalyst.com/articles/netherlands-2-2-argentina-world-cup-stats",
    "https://theanalyst.com/articles/morocco-portugal-2022-world-cup-stats",
    "https://theanalyst.com/articles/england-1-2-france",
    "https://theanalyst.com/articles/argentina-3-0-croatia-lionel-messi-is-one-game-from-immortality",
    "https://theanalyst.com/articles/france-2-0-morocco-france-through-to-fourth-final-in-last-seven-world-cups",
    "https://theanalyst.com/articles/croatia-2-1-morocco-2022-world-cup-stats",
    "https://theanalyst.com/articles/argentina-3-3-france-debate-over-as-lionel-messi-finally-wins-the-world-cup"
    # 2026
    "https://theanalyst.com/articles/mexico-vs-south-africa-stats-2026-world-cup",
    "https://theanalyst.com/articles/south-korea-vs-czechia-stats-2026-world-cup-live",
    "https://theanalyst.com/articles/canada-vs-bosnia-herzegovina-stats-world-cup-2026",
    "https://theanalyst.com/articles/united-states-vs-paraguay-stats-world-cup-2026",
    "https://theanalyst.com/articles/qatar-vs-switzerland-stats-world-cup-2026",
    "https://theanalyst.com/articles/brazil-vs-morocco-stats-world-cup-2026",
    "https://theanalyst.com/articles/haiti-vs-scotland-stats-world-cup-2026",
    "https://theanalyst.com/articles/australia-vs-turkiye-stats-world-cup-2026",
    "https://theanalyst.com/articles/germany-vs-curacao-stats-world-cup-2026",
    "https://theanalyst.com/articles/netherlands-vs-japan-stats-world-cup-2026",
    "https://theanalyst.com/articles/ivory-coast-vs-ecuador-stats-world-cup-2026",
    "https://theanalyst.com/articles/sweden-vs-tunisia-stats-world-cup-2026",
    "https://theanalyst.com/articles/saudi-arabia-vs-uruguay-stats-world-cup-2026",
    "https://theanalyst.com/articles/iran-vs-new-zealand-stats-world-cup-2026",
    "https://theanalyst.com/articles/france-vs-senegal-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/iraq-vs-norway-stats-world-cup-2026",
    "https://theanalyst.com/articles/argentina-vs-algeria-stats-world-cup-2026",
    "https://theanalyst.com/articles/austria-vs-jordan-stats-world-cup-2026",
    "https://theanalyst.com/articles/portugal-vs-dr-congo-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/england-vs-croatia-stats-world-cup-2026",
    "https://theanalyst.com/articles/ghana-vs-panama-stats-world-cup-2026",
    "https://theanalyst.com/articles/uzbekistan-vs-colombia-stats-fifa-world-cup-2026",
    "https://theanalyst.com/articles/czechia-vs-south-africa-stats-world-cup-2026",
    "https://theanalyst.com/articles/switzerland-vs-bosnia-herzegovina-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/canada-vs-qatar-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/mexico-vs-south-korea-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/usa-vs-australia-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/scotland-vs-morocco-stats-fifa-world-cup-2026-live",
    "https://theanalyst.com/articles/brazil-vs-haiti-stats-fifa-world-cup-2026-live",
    "https://theanalyst.com/articles/turkiye-vs-paraguay-stats-fifa-world-cup-2026-live",
    "https://theanalyst.com/articles/netherlands-vs-sweden-stats-world-cup-2026",
    "https://theanalyst.com/articles/germany-vs-ivory-coast-stats-world-cup-2026",
    "https://theanalyst.com/articles/ecuador-vs-curacao-stats-world-cup-2026",
    "https://theanalyst.com/articles/tunisia-vs-japan-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/new-zealand-vs-egypt-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/argentina-vs-austria-stats-world-cup-2026-messi",
    "https://theanalyst.com/articles/france-vs-iraq-stats-world-cup-2026",
    "https://theanalyst.com/articles/norway-vs-senegal-stats-world-cup-2026",
    "https://theanalyst.com/articles/jordan-vs-algeria-stats-world-cup-2026",
    "https://theanalyst.com/articles/portugal-vs-uzbekistan-stats-world-cup-2026",
    "https://theanalyst.com/articles/england-vs-ghana-stats-world-cup-2026",
    "https://theanalyst.com/articles/panama-vs-croatia-stats-world-cup-2026",
    "https://theanalyst.com/articles/colombia-vs-dr-congo-stats-world-cup-2026",
    "https://theanalyst.com/articles/bosnia-herzegovina-vs-qatar-stats-world-cup-2026",
    "https://theanalyst.com/articles/switzerland-vs-canada-stats-world-cup-2026",
    "https://theanalyst.com/articles/scotland-vs-brazil-stats-world-cup-2026",
    "https://theanalyst.com/articles/morocco-vs-haiti-stats-world-cup-2026",
    "https://theanalyst.com/articles/czechia-vs-mexico-stats-2026-world-cup-group-a-live",
    "https://theanalyst.com/articles/south-africa-vs-south-korea-stats-world-cup-2026",
    "https://theanalyst.com/articles/curacao-vs-ivory-coast-stats-2026-world-cup",
    "https://theanalyst.com/articles/ecuador-vs-germany-stats-2026-world-cup",
    "https://theanalyst.com/articles/tunisia-vs-netherlands-stats-2026-world-cup",
    "https://theanalyst.com/articles/japan-vs-sweden-stats-2026-world-cup",
    "https://theanalyst.com/articles/paraguay-vs-australia-stats-2026-world-cup",
    "https://theanalyst.com/articles/turkiye-vs-usa-stats-2026-world-cup",
    "https://theanalyst.com/articles/senegal-vs-iraq-stats-world-cup-2026",
    "https://theanalyst.com/articles/norway-vs-france-stats-world-cup-2026",
    "https://theanalyst.com/articles/uruguay-vs-spain-stats-fifa-world-cup-2026",
    "https://theanalyst.com/articles/cape-verde-vs-saudi-arabia-stats-fifa-world-cup-2026",
    "https://theanalyst.com/articles/new-zealand-vs-belgium-stats-fifa-world-cup-2026",
    "https://theanalyst.com/articles/panama-vs-england-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/croatia-vs-ghana-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/colombia-vs-portugal-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/dr-congo-vs-uzbekistan-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/jordan-vs-argentina-stats-world-cup-2026",
    "https://theanalyst.com/articles/algeria-vs-austria-stats-world-cup-2026-live",
    "https://theanalyst.com/articles/south-africa-vs-canada-stats-world-cup-2026",
    "https://theanalyst.com/articles/brazil-vs-japan-stats-world-cup-2026",
    "https://theanalyst.com/articles/germany-vs-paraguay-stats-world-cup-2026",
    "https://theanalyst.com/articles/netherlands-vs-morocco-stats-world-cup-2026",
    "https://theanalyst.com/articles/england-vs-dr-congo-stats-world-cup-2026",
    "https://theanalyst.com/articles/belgium-vs-senegal-stats-world-cup-2026",
    "https://theanalyst.com/articles/usa-vs-bosnia-herzegovina-stats-world-cup-2026",
    "https://theanalyst.com/articles/egypt-vs-iran-stats-fifa-world-cup-2026",
    "https://theanalyst.com/articles/spain-vs-austria-stats-world-cup-2026",
    "https://theanalyst.com/articles/portugal-vs-croatia-stats-world-cup-2026",
    "https://theanalyst.com/articles/australia-vs-egypt-stats-world-cup-2026",
    "https://theanalyst.com/articles/switzerland-vs-algeria-stats-world-cup-2026",
    "https://theanalyst.com/articles/argentina-vs-cape-verde-stats-world-cup-2026",
    "https://theanalyst.com/articles/colombia-vs-ghana-stats-world-cup-2026",
    "https://theanalyst.com/articles/canada-vs-morocco-stats-world-cup-2026-last-16",
    "https://theanalyst.com/articles/paraguay-vs-france-stats-world-cup-2026-last-16",
    "https://theanalyst.com/articles/brazil-vs-norway-stats-world-cup-2026-last-16",
    "https://theanalyst.com/articles/mexico-vs-england-stats-world-cup-2026-last-16",
    "https://theanalyst.com/articles/usa-vs-belgium-stats-world-cup-2026-round-of-16",
    "https://theanalyst.com/articles/argentina-vs-egypt-stats-world-cup-2026",
    "https://theanalyst.com/articles/switzerland-vs-colombia-stats-world-cup-2026",
    "https://theanalyst.com/articles/france-vs-morocco-stats-world-cup-2026-quarter-final",
    "https://theanalyst.com/articles/spain-vs-belgium-stats-world-cup-2026-quarter-final",
    "https://theanalyst.com/articles/england-vs-argentina-stats-world-cup-2026",
    "https://theanalyst.com/articles/france-vs-england-stats-world-cup-2026-bronze-final",
    "https://theanalyst.com/articles/spain-vs-argentina-stats-2026-world-cup-final",
    "https://theanalyst.com/articles/belgium-vs-egypt-stats-world-cup-group-g",
    "https://theanalyst.com/articles/spain-vs-cape-verde-stats-world-cup-group-h",
    "https://theanalyst.com/articles/belgium-vs-iran-stats-world-cup-group-g-live",
    "https://theanalyst.com/articles/spain-vs-saudi-arabia-stats-world-cup-group-h",
    "https://theanalyst.com/articles/uruguay-vs-cape-verde-stats-world-cup-group-h-live",
    "https://theanalyst.com/articles/ivory-coast-vs-norway-stats-world-cup-round-of-32",
    "https://theanalyst.com/articles/france-vs-sweden-stats-world-cup-round-of-32",
    "https://theanalyst.com/articles/mexico-vs-ecuador-world-cup-round-of-32-stats",
    "https://theanalyst.com/articles/portugal-vs-spain-stats-world-cup-round-of-16",
    "https://theanalyst.com/articles/norway-vs-england-stats-quarter-final",
    "https://theanalyst.com/articles/argentina-vs-switzerland-stats-world-cup-quarter-final",
    "https://theanalyst.com/articles/france-vs-spain-stats-world-cup-semi-final",
]


def collect_data():
    for i, url in enumerate(SEED_URLS):
        print(f"Fetching {url}...")
        try:
            # 1. Fetch the page
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()

            # Fix: requests guesses the encoding from HTTP headers, and defaults
            # to ISO-8859-1 when the server doesn't declare a charset. Most of
            # these sites are actually UTF-8, so let requests sniff the real
            # encoding from the response content instead (avoids mojibake like
            # "â€¢" instead of "•").
            if response.encoding is None or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding

            # 2. Extract the text (You will need to improve this basic cleaning)
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string if soup.title else f"Document {i}"

            # 3. Create the document metadata
            doc = {
                "id": f"doc_{i:03d}",
                "url": url,
                "title": title.strip(),
                "collection_date": datetime.now().isoformat(),
                "raw_html": response.text,  # Save raw HTML for the cleaning phase later
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
