"""Publish only models which have passed dbt build."""
import csv
import datetime as dt
import html
import json
from pathlib import Path
import duckdb

out = Path('site')
out.mkdir(exist_ok=True)
with duckdb.connect('data/weather.duckdb', read_only=True) as con:
    cursor = con.execute('select * from city_summary order by city')
    names = [d[0] for d in cursor.description]
    summaries = [dict(zip(names, row)) for row in cursor.fetchall()]
    cursor = con.execute('select * from stg_weather order by city, weather_date')
    columns = [d[0] for d in cursor.description]
    records = [dict(zip(columns, row)) for row in cursor.fetchall()]
with (out / 'weather.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(records)
results = json.loads(Path('target/run_results.json').read_text())['results']
tests = [r for r in results if r['unique_id'].startswith('test.')]
if not tests or any(r['status'] != 'pass' for r in tests):
    raise RuntimeError('Refusing to publish without passing data tests')
payload = {'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'tests_passed': len(tests), 'summary': summaries, 'daily': records}
(out / 'data.json').write_text(json.dumps(payload, default=str, indent=2))
cards = ''
for row in summaries:
    cards += f'''<article><p class="eyebrow">PERU / {html.escape(row['city'].upper())}</p><h2>{row['city']}</h2><p class="temp">{row['avg_midpoint_temp_c']}<span> °C</span></p><p>Average daily temperature midpoint</p><dl><dt>Peak temperature</dt><dd>{row['peak_temp_c']} °C</dd><dt>Total precipitation</dt><dd>{row['total_precipitation_mm']} mm</dd><dt>Complete daily records</dt><dd>{row['days']}</dd></dl></article>'''
table = ''.join(f"<tr><td>{r['city']}</td><td>{r['weather_date']}</td><td>{r['min_temp_c']}</td><td>{r['max_temp_c']}</td><td>{r['precipitation_mm']}</td></tr>" for r in records)
page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Peru Weather Observatory</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#0b1320;color:#edf3fa}*{box-sizing:border-box}body{max-width:1180px;margin:auto;padding:40px 24px}nav,footer{display:flex;gap:24px;flex-wrap:wrap;align-items:center}a{color:#79e0d0}nav{justify-content:space-between;border-bottom:1px solid #304055;padding-bottom:22px}.brand{font-weight:750;letter-spacing:.08em}h1{font-size:clamp(40px,7vw,76px);line-height:1.06;max-width:850px;margin:48px 0 22px}p{color:#b4c3d7;line-height:1.6}.eyebrow{font-size:12px;letter-spacing:.14em;color:#79e0d0}.intro{max-width:700px}.status{display:inline-block;border:1px solid #315c58;padding:9px 16px;border-radius:24px;color:#8ce6c5}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:32px 0}article{border:1px solid #304055;border-radius:18px;padding:24px;background:#111f30}h2{font-size:28px}.temp{font-size:52px;font-weight:750;margin:16px 0;color:#fff}.temp span{font-size:24px;color:#79e0d0}dl{display:grid;grid-template-columns:1fr auto;gap:14px;font-size:14px}dt{color:#b4c3d7}dd{margin:0}.flow{padding:22px;border:1px solid #304055;border-radius:12px;line-height:2;color:#79e0d0}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:12px;border-bottom:1px solid #304055}summary{cursor:pointer;padding:20px 0}footer{border-top:1px solid #304055;margin-top:44px;padding-top:20px;font-size:13px}.scroll{overflow:auto}@media(max-width:800px){.grid{grid-template-columns:1fr}body{padding:24px 16px}}
</style><nav><span class="brand">◉ PERU WEATHER OBSERVATORY</span><a href="https://github.com/Cristhian465/peru-weather-data-pipeline">Source & workflow ↗</a></nav><main><p class="eyebrow">PUBLIC DATA · AUTOMATED ANALYTICS</p><h1>Three cities.<br>One reliable data pipeline.</h1><p class="intro">A 14-day view of weather reanalysis for Tacna, Lima and Arequipa. Python ingests the data, DuckDB stores it, and dbt transforms and validates every release.</p>'''
page += f'<p class="status">✓ {len(tests)} data tests passed · {len(records)} city-day records</p><p>Window: {summaries[0]["start_date"]} → {summaries[0]["end_date"]} · Updated: {payload["generated_at"]}</p><section class="grid">{cards}</section>'
page += '<h2>From source to public insight</h2><p class="flow">Open-Meteo → Python → DuckDB → dbt models + tests → GitHub Actions → GitHub Pages</p><p>The window ends seven days before the run date to allow reanalysis availability. Temperature midpoint is (daily maximum + daily minimum) / 2, not the measured daily mean. Data represents gridded reanalysis rather than a local station.</p><p><a href="weather.csv">Download daily CSV</a> · <a href="data.json">Download JSON and run metadata</a></p>'
page += f'<details><summary>Explore all {len(records)} daily records</summary><div class="scroll"><table><thead><tr><th>City</th><th>Date</th><th>Min °C</th><th>Max °C</th><th>Rain mm</th></tr></thead><tbody>{table}</tbody></table></div></details></main>'
page += '<footer><span>By Cristhian Carlos Mamani Cori</span><a href="https://open-meteo.com/">Weather data by Open-Meteo</a><a href="https://creativecommons.org/licenses/by/4.0/">Data: CC BY 4.0</a></footer></html>'
(out / 'index.html').write_text(page)
print(f'Exported {len(records)} rows and {len(tests)} passing tests to site/')
