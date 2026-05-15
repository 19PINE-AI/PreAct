#!/bin/bash
# Runs Muscle-Mem + Workflow-Use baselines for 3 reps on the WebArena
# shopping_admin 12-task string_match subset, to bring head-to-head
# baselines (paper §5.6) from n=1 to n=4 (1 existing + 3 new).
#
# Each rep is sequential (single browser, single Docker shopping_admin).
# Logs land in /home/ubuntu/PreAct/webarena_baselines_rep{2,3,4}_<date>.log
# Results JSON in benchmark/webarena/results/.

set -u
cd /home/ubuntu/PreAct

DATE=$(date +%Y%m%d_%H%M%S)
for REP in 2 3 4; do
  LOG="/home/ubuntu/PreAct/webarena_baselines_rep${REP}_${DATE}.log"
  echo "[$(date +%H:%M:%S)] === Starting rep $REP -> $LOG ==="
  python3 -m benchmark.webarena.run_webarena \
    --systems muscle_mem workflow_use \
    --tasks 12 \
    --skip-setup \
    --eval-types string_match \
    > "$LOG" 2>&1
  EXIT=$?
  echo "[$(date +%H:%M:%S)] === rep $REP done, exit=$EXIT ==="
  if [[ $EXIT -ne 0 ]]; then
    echo "[FATAL] rep $REP failed; stopping queue"
    exit $EXIT
  fi
done
echo "[$(date +%H:%M:%S)] === all 3 reps complete ==="
