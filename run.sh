#!/bin/bash
# Quick run script for generating Gazebo SDF from AVL files

# Check if AVL file is provided
if [ $# -eq 0 ]; then
    echo "Usage: ./run.sh <avl_file> [options]"
    echo ""
    echo "Examples:"
    echo "  ./run.sh fms_fox.avl --auto"
    echo "  ./run.sh my_plane.avl --auto --vehicle_name my_custom_plane"
    echo ""
    echo "Options:"
    echo "  --auto              Run fully automated (recommended)"
    echo "  --vehicle_name      Override vehicle name"
    echo "  --no-display        Don't show geometry plot"
    echo "  --avl_path          Custom AVL installation path"
    echo ""
    exit 1
fi

# Run the script
python3 input_avl_direct.py --avl_file "$@"
