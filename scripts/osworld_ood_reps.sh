#!/bin/bash
# Runs 2 additional OSWorld test_small_ood reps (rep 2 + rep 3) to bring
# the OOD generalization claim from n=1 to n=3.
#
# Uses the same rag_db_expC_complete_20260429 warm corpus as the original
# rep 1, but RAG_DB_PATH points to a per-rep copy so the corpus isn't
# mutated by failed compiles during the run.

set -u
cd /home/ubuntu/PreAct
DATE=$(date +%Y%m%d_%H%M%S)

for REP in 2 3; do
  LOG="/home/ubuntu/PreAct/osworld_ood_rep${REP}_${DATE}.log"
  # Fresh copy of the warm corpus for this rep
  DB_COPY="/tmp/osworld_ood_rep${REP}_db"
  rm -rf "${DB_COPY}"
  cp -r rag_db_expC_complete_20260429 "${DB_COPY}"

  echo "[$(date +%H:%M:%S)] === OSWorld OOD rep ${REP} -> ${LOG} (db=${DB_COPY}) ==="
  RAG_DB_PATH="${DB_COPY}" python3 -m benchmark.osworld.run_osworld \
    --task-set test_small_ood \
    --systems preact \
    --headless \
    > "${LOG}" 2>&1
  local_exit=$?
  echo "[$(date +%H:%M:%S)] === OSWorld OOD rep ${REP} done, exit=${local_exit} ==="
done
echo "[$(date +%H:%M:%S)] === OSWorld OOD n=2 additional reps complete ==="
