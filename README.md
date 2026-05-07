# AVL to Gazebo Advanced Lift Drag Plugin Generator

This tool generates Gazebo advanced_lft_drag plugin coefficients directly from AVL files and produces performance polar plots.

## Quick Start

Generate SDF plugin from your AVL file:

```bash
python3 input_avl_direct.py --avl_file your_aircraft.avl --auto
```

This will:
- Parse your AVL file
- Run AVL to generate aerodynamic coefficients
- Create an SDF plugin file ready for Gazebo
- Open a visualization of the aircraft geometry

## Prerequisites

1. **AVL 3.36** must be installed
   - Download from: https://web.mit.edu/drela/Public/web/avl/
   - Install to `~/Avl/` or use `--avl_path` to specify location

2. **Python 3.10+** (for match/case syntax)

3. **Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **evince** (for viewing geometry plots)
   ```bash
   sudo apt install evince
   ```

## Usage

### Automated Mode (Recommended)

```bash
python3 input_avl_direct.py --avl_file models/fms_fox.avl --auto
```

Generates everything automatically and shows the geometry plot.

### Interactive Mode

```bash
python3 input_avl_direct.py --avl_file models/fms_fox.avl
```

Opens AVL interactively so you can run commands manually.

### Options

- `--avl_file` (required): Path to your AVL file
- `--auto`: Run fully automated (recommended)
- `--vehicle_name`: Override vehicle name from AVL file
- `--avl_path`: Custom AVL installation path
- `--no-display`: Skip opening the geometry plot window

## Output

The script creates a directory named after your vehicle containing:

- `<vehicle_name>.sdf` - Plugin XML ready to paste into your Gazebo model
- `<vehicle_name>.ps` - PostScript geometry visualization

## Example

```bash
# Generate coefficients for the FMS Fox
python3 input_avl_direct.py --avl_file models/fms_fox.avl --auto

# Output will be in M2S/M2S.sdf
```

## AVL File Format Support

The script handles both AVL file formats:

**Inline comments:**
```
0.746    0.25   3.0     !Sref    Cref    Bref
```

**Separate lines:**
```
!Sref    Cref    Bref
0.746    0.25   3.0
```

## Control Surface Types

The script recognizes:
- `aileron`
- `elevator`
- `rudder`
- `flap` (treated as elevator)

## Files in This Directory

- `input_avl_direct.py` - Main script for generating Gazebo SDF plugins
- `avl_out_parse.py` - Parses AVL output and generates SDF
- `plot_sink_polar.py` - Generates sink polar performance plots
- `example_polar.sh` - Example commands for polar generation
- `run.sh` - Quick run script
- `requirements.txt` - Python dependencies
- `templates/` - SDF template files
- `models/` - Example AVL files (e.g., fms_fox.avl)

## Troubleshooting

### "AVL installation not found"

Make sure AVL is installed in `~/Avl/` or specify the path:
```bash
python3 input_avl_direct.py --avl_file your_file.avl --auto --avl_path /path/to/avl/
```

### "Could not extract vehicle name"

Provide the vehicle name manually:
```bash
python3 input_avl_direct.py --avl_file your_file.avl --auto --vehicle_name my_plane
```

### "Could not extract reference area and wing span"

Check that your AVL file has lines with `Sref`, `Cref`, `Bref` and the values either:
- On the same line: `0.746  0.25  3.0  !Sref Cref Bref`
- On the next line after a comment

## Integration with Gazebo

1. Generate the SDF plugin:
   ```bash
   python3 input_avl_direct.py --avl_file your_aircraft.avl --auto
   ```

2. Open the generated `.sdf` file in `<vehicle_name>/<vehicle_name>.sdf`

3. Copy the entire `<plugin>` block into your Gazebo model's `.sdf` file

4. The plugin should be placed inside the `<model>` tag

## Notes

- Stall parameters use default values (from PX4 advanced_plane)
- For custom stall values, edit the generated SDF file
- The script assumes standard AVL geometry conventions
- Reference point is where forces and moments are applied

## Plotting Sink Polars

Generate performance polar plots showing sink rate vs airspeed:

```bash
python3 plot_sink_polar.py --avl_file models/fms_fox.avl --weight 2.0
```

This will:
- Run AVL across a range of angles of attack
- Extract CL and CD coefficients
- Calculate airspeed and sink rate at each point
- Generate a sink polar plot with performance metrics
- Save data to CSV for further analysis

### Options

- `--avl_file` (required): Path to your AVL file
- `--weight` (required): Aircraft weight in kg
- `--alpha_min`: Minimum angle of attack (default: -5°)
- `--alpha_max`: Maximum angle of attack (default: 20°)
- `--num_points`: Number of points in sweep (default: 25)
- `--rho`: Air density in kg/m³ (default: 1.225)
- `--output_dir`: Output directory (default: polar_data)
- `--show`: Display plot interactively

### Example Output

The script identifies key performance points:
- **Minimum Sink Rate**: Best for thermal soaring
- **Best Glide Ratio (L/D)**: Maximum distance per altitude loss

Output files:
- `<vehicle>_sink_polar.png` - Polar plot
- `<vehicle>_polar_data.csv` - Raw data (airspeed, sink rate, L/D, etc.)

## Support

This is a standalone version of the PX4-Autopilot AVL automation tool.

For issues or questions, check the AVL documentation:
https://web.mit.edu/drela/Public/web/avl/AVL_User_Primer.pdf
