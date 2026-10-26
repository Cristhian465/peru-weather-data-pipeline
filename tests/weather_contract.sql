select city
from {{ ref('stg_weather') }}
where min_temp_c > max_temp_c
   or precipitation_mm < 0
   or min_temp_c < -90 or max_temp_c > 65
union all
select city from {{ ref('stg_weather') }}
group by city, weather_date having count(*) <> 1
union all
select city from {{ ref('city_summary') }} where days <> 14
union all
select 'missing_city' where (select count(*) from {{ ref('city_summary') }}) <> 3
