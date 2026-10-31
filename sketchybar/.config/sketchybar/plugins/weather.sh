#!/bin/bash

# Vancouver, BC. Current conditions from https://open-meteo.com/.
URL='https://api.open-meteo.com/v1/forecast?latitude=49.2827&longitude=-123.1207&current=temperature_2m,weather_code,is_day&temperature_unit=celsius&timezone=America%2FVancouver'

set_weather() {
  sketchybar --set weather icon="$1" label="$2" \
             --set weather.notch icon="$1" label="$2"
}

unavailable() {
  set_weather "☁" "--°C"
}

if ! WEATHER=$(curl --fail --silent --show-error --connect-timeout 5 --max-time 15 "$URL"); then
  unavailable
  exit 0
fi

if ! VALUES=$(printf '%s' "$WEATHER" | jq -er '
  .current
  | select((.temperature_2m | type) == "number"
      and (.weather_code | type) == "number"
      and (.is_day | type) == "number")
  | [.temperature_2m | round] + [ .weather_code, .is_day ]
  | @tsv
'); then
  unavailable
  exit 0
fi

IFS=$'\t' read -r TEMPERATURE CODE IS_DAY <<< "$VALUES"
case "$CODE" in
  0) if [ "$IS_DAY" = 1 ]; then ICON="☀"; else ICON="☾"; fi ;;
  1|2) ICON="⛅" ;;
  3|45|48) ICON="☁" ;;
  51|53|55|56|57|61|63|65|66|67|80|81|82) ICON="🌧" ;;
  71|73|75|77|85|86) ICON="❄" ;;
  95|96|99) ICON="⛈" ;;
  *) ICON="☁" ;;
esac

set_weather "$ICON" "${TEMPERATURE}°C"
