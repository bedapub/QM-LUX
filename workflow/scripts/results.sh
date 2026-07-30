#!/bin/bash
# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
  
# Define input and output files
INPUT_DIR=$1
INPUT_FILE="$INPUT_DIR/data_ml/input.csv"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file not found!" >&2
    exit 1
fi

# Print header
echo "Folder,SRN,Status"

# Read input file (skipping header line)
tail -n +2 "$INPUT_FILE" | while IFS=',' read -r index srn smiles
do
    found_any_fp_dir=false
    
    # Look for any fp_* directories
    for RESULTS_DIR in "$INPUT_DIR"/fp_*; do
        # Skip if no directories match the pattern
        if [ ! -e "$RESULTS_DIR" ]; then
            continue
        fi
        
        found_any_fp_dir=true
        # Get the base folder name
        FOLDER_NAME=$(basename "$RESULTS_DIR")
        
        # If directory exists, check for failed molecules
        if [ -d "$RESULTS_DIR" ]; then
            FAILED_FILE="$RESULTS_DIR/failed_molecules.txt"
            
            if [ -f "$FAILED_FILE" ] && [ -s "$FAILED_FILE" ]; then
                if grep -q "$srn" "$FAILED_FILE"; then
                    status="FAILED"
                else
                    status="SUCCESS"
                fi
            else
                status="SUCCESS"
            fi
            
            # Write to stdout
            echo "$FOLDER_NAME,$srn,$status"
        fi
    done
    
    # If no fp_* directories were found, output UNKNOWN status
    if [ "$found_any_fp_dir" = false ]; then
        echo "NO_FP_DIR,$srn,UNKNOWN"
    fi
done