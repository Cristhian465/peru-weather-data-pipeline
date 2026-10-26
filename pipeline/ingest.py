"""Fetch a reproducible 14-day window of reanalysis data, then atomically replace raw rows."""
import datetime as dt
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request
import duckdb

CITIES = {'Tacna': (-18.0146, -70.2536), 'Lima': (-12.0464, -77.0428), 'Arequipa': (-16.409, -71.5375)}

def main():
    end = dt.date.today() - dt.timedelta(days=7)
    start = end - dt.timedelta(days=13)
    folder = Path('data/raw')
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for city, (lat, lon) in CITIES.items():
        params = urllib.parse.urlencode(dict(latitude=lat, longitude=lon, start_date=start.isoformat(), end_date=end.isoformat(), daily='temperature_2m_max,temperature_2m_min,precipitation_sum', timezone='America/Lima'))
        url = 'https://archive-api.open-meteo.com/v1/archive?' + params
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    payload = json.load(response)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        daily = payload['daily']
        expected = [start + dt.timedelta(days=i) for i in range(14)]
        if daily['time'] != [day.isoformat() for day in expected]:
            raise ValueError(f'{city}: incomplete date window')
        fields = ['temperature_2m_max', 'temperature_2m_min', 'precipitation_sum']
        if any(len(daily[f]) != 14 or any(v is None for v in daily[f]) for f in fields):
            raise ValueError(f'{city}: missing daily measurements')
        (folder / f'{city.lower()}.json').write_text(json.dumps({'source_url': url, 'fetched_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'response': payload}, indent=2))
        for i, day in enumerate(daily['time']):
            rows.append((city, day, *(daily[f][i] for f in fields)))
    with duckdb.connect('data/weather.duckdb') as con:
        con.execute('begin')
        con.execute('create schema if not exists raw')
        con.execute('create or replace table raw.weather(city varchar, date date, temperature_2m_max double, temperature_2m_min double, precipitation_sum double)')
        con.executemany('insert into raw.weather values (?, ?, ?, ?, ?)', rows)
        con.execute('commit')
    print(f'Loaded {len(rows)} city-days: {start} to {end}')

if __name__ == '__main__':
    main()
