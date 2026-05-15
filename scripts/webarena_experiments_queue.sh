#!/bin/bash
# Runs 8 WebArena gate-ON reps sequentially against shopping_admin.
#
# A. Cache-miss-to-CUA fallback (Claude compile, gate ON, fallback ON):    4 reps
# B. Gemini-compile (gate ON, no fallback) to bring §5.5 from n=1 to n=3:   2 reps
# C. Plain gate-ON to verify bimodal reproducibility (§5.3.3):              2 reps

set -u
cd /home/ubuntu/PreAct
DATE=$(date +%Y%m%d_%H%M%S)

run_rep() {
  local label="$1"; shift
  local rep="$1"; shift
  local logfile="/home/ubuntu/PreAct/webarena_${label}_rep${rep}_${DATE}.log"
  echo "[$(date +%H:%M:%S)] === ${label} rep ${rep} -> ${logfile} ==="
  env "$@" python3 -m benchmark.webarena.run_webarena \
    --systems preact \
    --tasks 12 \
    --skip-setup \
    --eval-types string_match \
    > "${logfile}" 2>&1
  local exit=$?
  echo "[$(date +%H:%M:%S)] === ${label} rep ${rep} done, exit=${exit} ==="
  if [[ $exit -ne 0 ]]; then
    echo "[WARN] ${label} rep ${rep} non-zero exit; continuing anyway"
  fi
}

# A. Cache-miss-to-CUA fallback, n=4
for REP in 1 2 3 4; do
  run_rep "cachemiss_fallback" "$REP" \
    PREACT_VERIFY_BEFORE_STORE=on \
    PREACT_CACHE_MISS_FALLBACK=cua
done

# B. Gemini compile, n=2 (existing n=1 + 2 = 3 total)
for REP in 2 3; do
  run_rep "gemini_compile" "$REP" \
    PREACT_VERIFY_BEFORE_STORE=on \
    PREACT_COMPILE_PROVIDER=gemini
done

# C. Plain gate-ON, n=2 (bimodal reproducibility check)
for REP in 5 6; do
  run_rep "gate_on_reproducibility" "$REP" \
    PREACT_VERIFY_BEFORE_STORE=on
done

echo "[$(date +%H:%M:%S)] === all 8 reps complete ==="
