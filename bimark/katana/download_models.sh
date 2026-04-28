#!/bin/bash

# ==============================================================================
# Script Name: download_models_unified.sh
# Description: Automates the process of setting up the environment, optionally
#              cleaning the cache, and downloading a specified list of Hugging
#              Face models (LLMs). Includes performance metrics (time/speed).
# ==============================================================================

# --- Configuration ---
# Set to 'true' to force delete existing cache before downloading.
# Set to 'false' to allow 'hf download' to resume or skip existing files.
CLEAN_CACHE=false

# List of models to download
MODELS_TO_DOWNLOAD=(
    "google/t5-v1_1-xxl"
    "kalpeshk2011/dipper-paraphraser-xxl"
    "Qwen/Qwen2.5-3B"
    "meta-llama/Meta-Llama-3.1-8B"
    "google/gemma-2-9b"
)

# Environment Paths
export HF_HOME="/srv/scratch/z5542506/hf_cache"
VENV_PATH=".venv/bin/activate"
HUB_DIR="$HF_HOME/hub"

echo "==========================================================="
echo "HF_HOME Configured: $HF_HOME"
echo "Mode: $( [ "$CLEAN_CACHE" = "true" ] && echo "Fresh Download (Clean Cache)" || echo "Incremental/Resume Download" )"
echo "Models queued: ${#MODELS_TO_DOWNLOAD[@]}"
echo "==========================================================="

# --- 1. Environment Setup ---

# Load Python module
echo "[Info] Loading Python module: python/3.13.2..."
module load python/3.13.2
if [ $? -ne 0 ]; then
    echo "[Error] Failed to load module 'python/3.13.2'. Exiting."
    exit 1
fi

# Activate Virtual Environment
echo "[Info] Activating virtual environment: $VENV_PATH"
if [ -f "$VENV_PATH" ]; then
    source "$VENV_PATH"
else
    echo "[Error] Virtual environment not found at $VENV_PATH. Exiting."
    exit 1
fi

# Verify dependencies
if ! command -v hf &> /dev/null; then
    echo "[Error] Command 'hf' not found. Ensure huggingface-cli is installed in the venv."
    exit 1
fi
if ! command -v bc &> /dev/null; then
    echo "[Error] Command 'bc' not found. Required for speed calculations."
    exit 1
fi

# --- 2. Cache Management (Optional) ---

if [ "$CLEAN_CACHE" = "true" ]; then
    echo "--- Cleaning Cache ---"
    echo "Target: $HUB_DIR/models--*"
    
    if [ -d "$HUB_DIR" ]; then
        if compgen -G "$HUB_DIR/models--*" > /dev/null; then
            echo "[Warn] Removing existing model cache..."
            rm -rf "$HUB_DIR/models--*"
            
            if [ $? -eq 0 ]; then
                echo "[Success] Cache cleared."
            else
                echo "[Error] Failed to delete cache. Check permissions."
                deactivate
                exit 1
            fi
        else
            echo "[Info] Cache directory exists but contains no models."
        fi
    else
        echo "[Info] Hub directory does not exist. Skipping cleanup."
    fi
    echo ""
fi

# --- 3. Model Download Loop ---

echo "--- Starting Download Process ---"
echo "(Using token cached in $HF_HOME/token)"
echo ""

for model in "${MODELS_TO_DOWNLOAD[@]}"; do
    echo "-----------------------------------------------------------"
    echo "Processing: $model"
    echo "-----------------------------------------------------------"
    
    start_time=$(date +%s)
    
    # Execute download.
    # If cache exists and is valid, this validates checksums and skips.
    # If incomplete, it resumes.
    hf download "$model"
    download_status=$?

    if [ $download_status -eq 0 ]; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        
        # --- Metrics Calculation ---
        # Construct the local directory path for the model
        model_dir_name="models--${model//\//--}"
        model_path="$HUB_DIR/$model_dir_name"

        if [ -d "$model_path" ]; then
            model_size_human=$(du -sh "$model_path" | cut -f1)
            model_size_bytes=$(du -sb "$model_path" | cut -f1)
        else
            model_size_human="Unknown"
            model_size_bytes=0
        fi

        speed_display="N/A"
        if [ $duration -gt 0 ] && [ $model_size_bytes -gt 0 ]; then
            # Calculate speed in MB/s
            speed_bps=$(echo "scale=2; $model_size_bytes / $duration" | bc)
            speed_mbs=$(echo "scale=2; $speed_bps / 1024 / 1024" | bc)
            speed_display="${speed_mbs} MB/s"
        elif [ $model_size_bytes -gt 0 ]; then
             speed_display="Instant (<1s)"
        fi

        echo ""
        echo "[Success] Download/Verification complete for $model"
        echo "  - Disk Usage:  $model_size_human"
        echo "  - Duration:    ${duration} sec"
        echo "  - Avg Speed:   $speed_display"
        echo ""
    else
        echo ""
        echo "[Warning] Failed to download $model."
        echo "  - Check your Hugging Face token permissions."
        echo "  - Check network connectivity or disk quota."
        echo ""
    fi
done

echo "==========================================================="
echo "All tasks completed."
echo "Models stored in: $HF_HOME"
echo "==========================================================="

deactivate
echo "[Info] Virtual environment deactivated."