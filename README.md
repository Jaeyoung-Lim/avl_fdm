# AVL to Gazebo Advanced Lift Drag Plugin Generator

This tool generates Gazebo advanced_lft_drag plugin coefficients directly from AVL files.

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

3. **evince** (for viewing geometry plots)
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

- `input_avl_direct.py` - Main script
- `avl_out_parse.py` - Parses AVL output and generates SDF
- `templates/` - SDF template files
- `fms_fox.avl` - Example AVL file

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

## Support

This is a standalone version of the PX4-Autopilot AVL automation tool.

For issues or questions, check the AVL documentation:
https://web.mit.edu/drela/Public/web/avl/AVL_User_Primer.pdf
