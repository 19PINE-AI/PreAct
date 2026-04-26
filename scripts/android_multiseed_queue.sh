#!/bin/bash
# Multi-seed extensions of n=1 AB experiments to n=5.
# Sequential because the Android container is shared (port 5555).
#
# Coverage (seeds 42, 100, 1337 partly done from earlier today):
#   Exp 1 (verify-gate): need seeds 100/1337 gate-OFF, plus seeds 2024/7777 both ON+OFF
#   Exp 3 (guardrails):  need seeds 100/1337/2024/7777 both ON+OFF (cold+warm each)
#   Exp 4 (step-budget): need seeds 100/1337/2024/7777 with --max-steps 60 --no-dynamic-steps
#
# Each cold/warm pair wipes rag_db. Logs to /home/ubuntu/PreAct/android_multiseed/.
set -u
LOG_DIR=/home/ubuntu/PreAct/android_multiseed
mkdir -p "$LOG_DIR"

# Use a separate rag_db dir so we don't collide with the parallel OSWorld
# experiments running on the default rag_db/.
export RAG_DB_PATH=/home/ubuntu/PreAct/rag_db_android_multiseed

TASKS="AudioRecorderRecordAudio AudioRecorderRecordAudioWithFileName BrowserDraw BrowserMaze CameraTakePhoto CameraTakeVideo ClockStopWatchPausedVerify ClockStopWatchRunning ContactsAddContact ContactsNewContactDraft FilesDeleteFile MarkorCreateFolder MarkorCreateNote SystemBrightnessMax SystemWifiTurnOn"

run_pair() {
    local seed=$1; local label=$2; local extra_env=$3; local extra_args=$4
    echo "=== $(date +%H:%M:%S) [$label seed=$seed] COLD ===" | tee -a "$LOG_DIR/orchestrator.log"
    # Wipe rag_db for clean cold start (operates on isolated multiseed dir)
    if [ -d "$RAG_DB_PATH" ]; then
        mv "$RAG_DB_PATH" "$LOG_DIR/rag_db_${label}_seed${seed}_pre_$(date +%H%M%S)"
    fi
    eval "$extra_env" PYTHONPATH=/home/ubuntu/PreAct python3 -u -m benchmark.androidworld.run_docker \
        --port 5555 --seed $seed --tasks $TASKS \
        --n-instances 1 --max-steps 20 $extra_args \
        > "$LOG_DIR/${label}_cold_seed${seed}.log" 2>&1
    cold_sr=$(grep -oE "Success: [0-9]+/[0-9]+" "$LOG_DIR/${label}_cold_seed${seed}.log" | tail -1)
    echo "$(date +%H:%M:%S) [$label seed=$seed] COLD done: $cold_sr" | tee -a "$LOG_DIR/orchestrator.log"

    # Warm pass on the just-built rag_db
    echo "=== $(date +%H:%M:%S) [$label seed=$seed] WARM ===" | tee -a "$LOG_DIR/orchestrator.log"
    eval "$extra_env" PYTHONPATH=/home/ubuntu/PreAct python3 -u -m benchmark.androidworld.run_docker \
        --port 5555 --seed $seed --tasks $TASKS \
        --n-instances 1 --max-steps 20 $extra_args \
        > "$LOG_DIR/${label}_warm_seed${seed}.log" 2>&1
    warm_sr=$(grep -oE "Success: [0-9]+/[0-9]+" "$LOG_DIR/${label}_warm_seed${seed}.log" | tail -1)
    echo "$(date +%H:%M:%S) [$label seed=$seed] WARM done: $warm_sr" | tee -a "$LOG_DIR/orchestrator.log"
}

# Single-condition runs for Exp 4 (no warm needed — just budget=60 cold)
run_single_cold() {
    local seed=$1; local label=$2; local extra_args=$3
    echo "=== $(date +%H:%M:%S) [$label seed=$seed] COLD ===" | tee -a "$LOG_DIR/orchestrator.log"
    if [ -d "$RAG_DB_PATH" ]; then
        mv "$RAG_DB_PATH" "$LOG_DIR/rag_db_${label}_seed${seed}_pre_$(date +%H%M%S)"
    fi
    PYTHONPATH=/home/ubuntu/PreAct python3 -u -m benchmark.androidworld.run_docker \
        --port 5555 --seed $seed --tasks $TASKS \
        --n-instances 1 $extra_args \
        > "$LOG_DIR/${label}_cold_seed${seed}.log" 2>&1
    sr=$(grep -oE "Success: [0-9]+/[0-9]+" "$LOG_DIR/${label}_cold_seed${seed}.log" | tail -1)
    echo "$(date +%H:%M:%S) [$label seed=$seed] COLD done: $sr" | tee -a "$LOG_DIR/orchestrator.log"
}

echo "Starting multi-seed Android queue at $(date)" | tee -a "$LOG_DIR/orchestrator.log"

# --- Exp 1 (verify-gate ablation) extensions: need OFF on seeds 100, 1337, 2024, 7777
#     Plus ON on 2024, 7777
run_pair 100  "exp1_off"  ""                          "--no-verify-before-store"
run_pair 1337 "exp1_off"  ""                          "--no-verify-before-store"
run_pair 2024 "exp1_on"   ""                          ""
run_pair 2024 "exp1_off"  ""                          "--no-verify-before-store"
run_pair 7777 "exp1_on"   ""                          ""
run_pair 7777 "exp1_off"  ""                          "--no-verify-before-store"

# --- Exp 3 (guardrails) extensions: need cold+warm of both ON and OFF on seeds 100, 1337, 2024, 7777
run_pair 100  "exp3_on"      ""                              ""
run_pair 100  "exp3_off"     "PREACT_GUARDRAILS=off"         ""
run_pair 1337 "exp3_on"      ""                              ""
run_pair 1337 "exp3_off"     "PREACT_GUARDRAILS=off"         ""
run_pair 2024 "exp3_on"      ""                              ""
run_pair 2024 "exp3_off"     "PREACT_GUARDRAILS=off"         ""
run_pair 7777 "exp3_on"      ""                              ""
run_pair 7777 "exp3_off"     "PREACT_GUARDRAILS=off"         ""

# --- Exp 4 (step-budget) extensions: budget=60 cold on seeds 100, 1337, 2024, 7777
run_single_cold 100  "exp4_b60" "--max-steps 60 --no-dynamic-steps"
run_single_cold 1337 "exp4_b60" "--max-steps 60 --no-dynamic-steps"
run_single_cold 2024 "exp4_b60" "--max-steps 60 --no-dynamic-steps"
run_single_cold 7777 "exp4_b60" "--max-steps 60 --no-dynamic-steps"

echo "All multi-seed Android runs complete at $(date)" | tee -a "$LOG_DIR/orchestrator.log"
