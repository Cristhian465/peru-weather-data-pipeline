select
    city,
    cast(date as date) as weather_date,
    cast(temperature_2m_max as double) as max_temp_c,
    cast(temperature_2m_min as double) as min_temp_c,
    cast(precipitation_sum as double) as precipitation_mm
from raw.weather
