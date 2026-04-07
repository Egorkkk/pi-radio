#!/usr/bin/env bash
set -u

MAC="00:1B:66:E8:E3:9B"
BT_SINK_DESC="HD 350BT"
JACK_SINK_DESC="Built-in Audio Stereo"

LOG="$HOME/pi-radio/logs/bt-audio-watch.log"
mkdir -p "$(dirname "$LOG")"

log() {
  printf '%s %s\n' "$(date '+%F %T')" "$*" >> "$LOG"
}

is_connected() {
  bluetoothctl info "$MAC" 2>/dev/null | grep -q "Connected: yes"
}

device_seen() {
  bluetoothctl info "$MAC" 2>/dev/null | grep -q "Device $MAC"
}

set_default_by_description() {
  local desc="$1"
  local id

  id="$(wpctl status | awk -v d="$desc" '
    /^[[:space:]]*├─ Sinks:/, /^[[:space:]]*├─ Sources:/ {
      if (index($0, d)) {
        for (i = 1; i <= NF; i++) {
          if ($i ~ /^[0-9]+\.$/) {
            gsub(/\./, "", $i)
            print $i
            exit
          }
        }
      }
    }
  ')"

#  log "resolve desc=$desc id=${id:-<empty>}"

  if [[ -n "${id:-}" && "$id" =~ ^[0-9]+$ && "$id" -gt 0 ]]; then
    wpctl set-default "$id"
    log "set default sink: $desc (id=$id)"
    return 0
  fi

  log "failed to resolve sink id for desc: $desc"
  return 1
}

last_state="unknown"

log "bt-audio-watch started"

while true; do
#  log "tick seen=$(device_seen && echo yes || echo no) connected=$(is_connected && echo yes || echo no)"

  if device_seen; then
    if is_connected; then
      if [ "$last_state" != "connected" ]; then
        log "headphones connected"
        set_default_by_description "$BT_SINK_DESC" || log "failed to set BT sink"
        last_state="connected"
      fi
    else
      bluetoothctl connect "$MAC" >/dev/null 2>&1 && log "connect requested"
      if [ "$last_state" != "disconnected" ]; then
        log "headphones disconnected"
        set_default_by_description "$JACK_SINK_DESC" || log "failed to set jack sink"
        last_state="disconnected"
      fi
    fi
  else
    if [ "$last_state" != "missing" ]; then
      log "device not visible yet"
      set_default_by_description "$JACK_SINK_DESC" || log "failed to set jack sink while missing"
      last_state="missing"
    fi
  fi

  sleep 5
done
