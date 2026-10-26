select
    city,
    count(*) as days,
    min(weather_date) as start_date,
    max(weather_date) as end_date,
    round(avg((max_temp_c + min_temp_c) / 2), 1) as avg_midpoint_temp_c,
    round(max(max_temp_c), 1) as peak_temp_c,
    round(sum(precipitation_mm), 1) as total_precipitation_mm
from {{ ref('stg_weather') }}
group by city
