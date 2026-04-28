#!/bin/bash

# ==============================================================================
# Script Name: delete_models.sh
# Description: Interactively lists installed Hugging Face models and allows
#              the user to delete specific models or clear the entire cache.
# ==============================================================================

# --- Configuration ---
export HF_HOME="/srv/scratch/z5542506/hf_cache"
HUB_DIR="$HF_HOME/hub"

# --- 1. Check Environment ---
if [ ! -d "$HUB_DIR" ]; then
    echo "[Error] Hub directory not found at: $HUB_DIR"
    exit 1
fi

echo "==========================================================="
echo "HF_HOME: $HF_HOME"
echo "Scanning for cached models..."
echo "==========================================================="

# --- 2. List Available Models ---
# Find directories starting with 'models--'
mapfile -t model_dirs < <(find "$HUB_DIR" -maxdepth 1 -type d -name "models--*")

if [ ${#model_dirs[@]} -eq 0 ]; then
    echo "[Info] No models found in cache."
    exit 0
fi

echo "Found the following models:"
i=1
for dir in "${model_dirs[@]}"; do
    # Extract clean model name (remove path and 'models--' prefix, replace '--' with '/')
    dirname=$(basename "$dir")
    clean_name=$(echo "$dirname" | sed 's/^models--//; s/--/\//g')
    echo "  [$i] $clean_name  (Path: $dirname)"
    i=$((i+1))
done
echo ""

# --- 3. User Selection ---
echo "Options:"
echo "  - Enter the NUMBER of the model to delete (e.g., 1)"
echo "  - Enter 'all' to delete EVERYTHING"
echo "  - Enter 'q' to quit"
echo ""
read -p "Your choice: " choice

# --- 4. Process Deletion ---

if [ "$choice" == "q" ]; then
    echo "Exiting."
    exit 0

elif [ "$choice" == "all" ]; then
    echo ""
    echo "!!! WARNING !!!"
    echo "You are about to delete ALL models in $HUB_DIR"
    read -p "Are you sure? (Type 'yes' to confirm): " confirm
    
    if [ "$confirm" == "yes" ]; then
        echo "Deleting all models..."
        rm -rf "$HUB_DIR"/models--*
        echo "[Success] Cache cleared."
    else
        echo "Cancelled."
    fi

elif [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -lt "$i" ]; then
    # Map selection back to array index (0-based)
    index=$((choice-1))
    target_dir="${model_dirs[$index]}"
    target_name=$(basename "$target_dir")
    
    echo ""
    echo "Target selected: $target_name"
    read -p "Are you sure you want to delete this model? (y/n): " confirm
    
    if [ "$confirm" == "y" ] || [ "$confirm" == "Y" ]; then
        echo "Deleting $target_dir ..."
        rm -rf "$target_dir"
        
        # Optional: Remove .locks folder if it exists to keep things clean
        # rm -rf "$HUB_DIR/.locks/models--${target_name#models--}" 2>/dev/null
        
        echo "[Success] Model deleted."
    else
        echo "Cancelled."
    fi

else
    echo "[Error] Invalid selection."
    exit 1
fi