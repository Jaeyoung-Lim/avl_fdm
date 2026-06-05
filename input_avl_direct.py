#!/usr/bin/env python3

import argparse
import avl_out_parse
import os
import subprocess
import shutil
import re

"""
Parse an existing AVL file to extract vehicle parameters.

Args:
    avl_file_path (str): Path to the AVL file.

Return:
    dict: Dictionary containing extracted parameters.
"""
def parse_avl_file(avl_file_path: str) -> dict:
    params = {
        'vehicle_name': None,
        'area': None,
        'chord': None,
        'span': None,
        'ref_pt_x': None,
        'ref_pt_y': None,
        'ref_pt_z': None,
        'control_surfaces': []
    }
    
    with open(avl_file_path, 'r') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Get vehicle name (first non-comment, non-empty line after header that's not numbers)
        if params['vehicle_name'] is None:
            if line and not line.startswith('!') and not line.startswith('#'):
                # Check if this looks like a vehicle name (not a number line)
                if not re.match(r'^[\d\.\-\s]+$', line):
                    params['vehicle_name'] = line.strip()
                    i += 1
                    continue
        
        # Look for Sref, Cref, Bref - check both inline comment and separate line formats
        if 'Sref' in line and 'Cref' in line and 'Bref' in line:
            # Check if values are on the same line (inline comment)
            if not line.startswith('!'):
                # Values and comment on same line
                parts = line.split('!')
                if len(parts) > 0:
                    values = parts[0].strip().split()
                    if len(values) >= 3:
                        params['area'] = values[0]
                        params['chord'] = values[1]
                        params['span'] = values[2]
            else:
                # Comment line, values on next line
                if i + 1 < len(lines):
                    values = lines[i + 1].strip().split()
                    if len(values) >= 3:
                        params['area'] = values[0]
                        params['chord'] = values[1]
                        params['span'] = values[2]
                i += 1
                continue
        
        # Look for Xref, Yref, Zref - check both inline comment and separate line formats
        if 'Xref' in line and 'Yref' in line and 'Zref' in line:
            # Check if values are on the same line (inline comment)
            if not line.startswith('!'):
                # Values and comment on same line
                parts = line.split('!')
                if len(parts) > 0:
                    values = parts[0].strip().split()
                    if len(values) >= 3:
                        params['ref_pt_x'] = values[0]
                        params['ref_pt_y'] = values[1]
                        params['ref_pt_z'] = values[2]
            else:
                # Comment line, values on next line
                if i + 1 < len(lines):
                    values = lines[i + 1].strip().split()
                    if len(values) >= 3:
                        params['ref_pt_x'] = values[0]
                        params['ref_pt_y'] = values[1]
                        params['ref_pt_z'] = values[2]
                i += 1
                continue
        
        # Look for SURFACE definitions and count control surfaces
        if line.upper() == 'SURFACE':
            has_yduplicate = False
            surface_controls = []  # unique control names in this surface, in order

            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()

                if next_line.upper() == 'SURFACE':
                    break

                if next_line.upper() == 'YDUPLICATE':
                    has_yduplicate = True

                if next_line.upper() == 'CONTROL':
                    # Get control surface name from next non-comment line
                    k = j + 1
                    while k < len(lines) and k < j + 5:
                        ctrl_line = lines[k].strip()
                        if ctrl_line and not ctrl_line.startswith('!'):
                            ctrl_parts = ctrl_line.split()
                            if ctrl_parts:
                                ctrl_name = ctrl_parts[0].lower()
                                if ctrl_name not in surface_controls:
                                    surface_controls.append(ctrl_name)
                                break
                        k += 1

                j += 1

            # YDUPLICATE surfaces have mirrored left/right control surfaces;
            # add each unique control name twice so downstream code gets a
            # separate servo entry per physical side.
            for ctrl_name in surface_controls:
                if has_yduplicate:
                    params['control_surfaces'].append(ctrl_name)  # left
                    params['control_surfaces'].append(ctrl_name)  # right
                else:
                    params['control_surfaces'].append(ctrl_name)
        
        i += 1
    
    return params

"""
Process an existing AVL file and generate the advanced lift drag plugin coefficients.

Args:
    avl_file: Path to the input AVL file
    avl_path: Set the avl_path to provide a desired directory for where AVL should be located.

Return:
    None
"""
def main():
    user = os.environ.get('USER')
    
    # Find AVL on the user's machine
    target_directory_path = None
    for root, dirs, _ in os.walk(f'/home/{user}/'):
        if "Avl" in dirs:
            target_directory_path = os.path.join(root, "Avl")
            break
    
    if target_directory_path is None:
        print("ERROR: AVL installation not found. Please install AVL first.")
        print("See README.md for installation instructions.")
        return
    
    parent_directory_path = os.path.dirname(target_directory_path)
    filedir = f'{parent_directory_path}/'
    
    parser = argparse.ArgumentParser(
        description='Generate advanced lift drag plugin coefficients from an AVL file.'
    )
    parser.add_argument("--avl_file", required=True, help="Path to input AVL file.")
    parser.add_argument("--avl_path", default=filedir, 
                       help="Provide an absolute AVL path. If this argument is passed, "
                            "AVL will be moved there and the files will adjust their paths accordingly.")
    parser.add_argument("--vehicle_name", default=None,
                       help="Override vehicle name (default: extracted from AVL file)")
    parser.add_argument("--auto", action="store_true",
                       help="Run in automated mode without opening AVL interactively (default: interactive)")
    parser.add_argument("--no-display", action="store_true",
                       help="Don't display the geometry plot window (only with --auto)")
    inputs = parser.parse_args()
    
    # Interactive is default, unless --auto is specified
    inputs.interactive = not inputs.auto
    
    # Check if AVL file exists
    if not os.path.exists(inputs.avl_file):
        print(f"ERROR: AVL file not found: {inputs.avl_file}")
        return
    
    print(f"Parsing AVL file: {inputs.avl_file}")
    
    # Parse the AVL file to extract parameters
    params = parse_avl_file(inputs.avl_file)
    
    # Override vehicle name if provided
    if inputs.vehicle_name:
        params['vehicle_name'] = inputs.vehicle_name
    
    # Validate that we got all required parameters
    if params['vehicle_name'] is None:
        print("ERROR: Could not extract vehicle name from AVL file.")
        print("Please provide it using --vehicle_name flag.")
        return
    
    if params['area'] is None or params['span'] is None:
        print("ERROR: Could not extract reference area and wing span from AVL file.")
        return
    
    if params['ref_pt_x'] is None or params['ref_pt_y'] is None or params['ref_pt_z'] is None:
        print("ERROR: Could not extract reference point from AVL file.")
        return
    
    plane_name = params['vehicle_name']
    area = params['area']
    span = params['span']
    ref_chord = params['chord']
    ref_pt_x = params['ref_pt_x']
    ref_pt_y = params['ref_pt_y']
    ref_pt_z = params['ref_pt_z']
    ctrl_surface_order = params['control_surfaces']
    num_ctrl_surfaces = len(ctrl_surface_order)
    
    print(f"\nExtracted parameters:")
    print(f"  Vehicle name: {plane_name}")
    print(f"  Reference area: {area}")
    print(f"  Wing span: {span}")
    print(f"  Reference chord: {ref_chord}")
    print(f"  Reference point: ({ref_pt_x}, {ref_pt_y}, {ref_pt_z})")
    print(f"  Number of control surfaces: {num_ctrl_surfaces}")
    print(f"  Control surfaces: {ctrl_surface_order}")
    
    # If the user passes the avl_path argument then move AVL to that location:
    if inputs.avl_path != filedir:
        # Check if the directory is already there
        if os.path.exists(f'{inputs.avl_path}/Avl') and os.path.isdir(f'{inputs.avl_path}/Avl'):
            print("AVL is already at desired location")
        else:
            shutil.move(f'{filedir}Avl', inputs.avl_path)
    
    # Get the current working directory
    result = subprocess.run(['pwd'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        current_path = result.stdout.strip()
    else:
        print("ERROR: Could not determine current directory")
        return
    
    # Copy the AVL file to the AVL runs directory
    avl_runs_dir = f'{inputs.avl_path}Avl/runs/'
    shutil.copy(inputs.avl_file, f'{avl_runs_dir}{plane_name}.avl')
    print(f"\nCopied AVL file to: {avl_runs_dir}{plane_name}.avl")
    
    # Change to AVL runs directory
    os.chdir(avl_runs_dir)
    
    # Clean up old derivative files
    old_stability_derivatives = "custom_vehicle_stability_derivatives.txt"
    old_body_ax_derivatives = "custom_vehicle_body_axis_derivatives.txt"
    
    if os.path.exists(old_stability_derivatives):
        os.remove(old_stability_derivatives)
    if os.path.exists(old_body_ax_derivatives):
        os.remove(old_body_ax_derivatives)
    
    # Create AVL command file
    avl_commands = f"""oper
x
n custom_plane
st custom_vehicle_stability_derivatives.txt
sb custom_vehicle_body_axis_derivatives.txt
g
h


quit
"""
    
    commands_file = f'{avl_runs_dir}temp_avl_commands.txt'
    with open(commands_file, 'w') as f:
        f.write(avl_commands)
    
    print("\nRunning AVL to generate aerodynamic coefficients...")
    
    # Run AVL
    avl_binary = f'{inputs.avl_path}Avl/bin/avl'
    avl_input_file = f'{plane_name}.avl'
    
    if inputs.interactive:
        print("\n" + "="*60)
        print("INTERACTIVE MODE (default)")
        print("="*60)
        print(f"\nLaunching AVL with {avl_input_file}...")
        print("\nOnce AVL starts, run these commands to generate the coefficients:")
        print("  oper")
        print("  x")
        print("  n custom_plane")
        print("  st custom_vehicle_stability_derivatives.txt")
        print("  sb custom_vehicle_body_axis_derivatives.txt")
        print("  g")
        print("  h")
        print("  <press Enter twice>")
        print("  quit")
        print("\nAfter running these commands and quitting AVL,")
        print("re-run this script with --auto to generate the SDF file.")
        print("="*60 + "\n")
        
        # Launch AVL interactively
        print(f"Starting AVL (use 'quit' to exit)...\n")
        try:
            os.system(f'{avl_binary} {avl_input_file}')
        except KeyboardInterrupt:
            print("\nAVL closed.")
        except Exception as e:
            print(f"\nError running AVL: {e}")
        
        # Change back to original directory
        os.chdir(current_path)
        
        print("\n" + "="*60)
        print("To generate the SDF plugin file, run:")
        print(f"  python3 input_avl_direct.py --avl_file {inputs.avl_file} --auto")
        print("="*60 + "\n")
        return
    
    # Non-interactive mode: run AVL with automated commands
    with open(commands_file, 'r') as cmd_file:
        result = subprocess.run(
            [avl_binary, avl_input_file],
            stdin=cmd_file,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
    if result.returncode != 0:
        print(f"ERROR running AVL: {result.stderr}")
        return
    
    print("AVL execution completed successfully")
    
    # Check if output files were created
    if not os.path.exists(old_stability_derivatives):
        print("ERROR: AVL did not generate stability derivatives file")
        return
    if not os.path.exists(old_body_ax_derivatives):
        print("ERROR: AVL did not generate body axis derivatives file")
        return
    
    print("AVL execution completed successfully")
    
    # Move plot file if it exists
    if os.path.exists('plot.ps'):
        plot_dest = f'{current_path}/{plane_name}.ps'
        shutil.move('plot.ps', plot_dest)
        print(f"Geometry plot saved to: {plot_dest}")
    
    # Change back to original directory
    os.chdir(current_path)
    
    # Calculate Aspect Ratio (AR) and Mean Aerodynamic Chord (mac)
    AR = str((float(span) * float(span)) / float(area))
    mac = str((2/3) * (float(area) / float(span)))
    
    print("\nCalculated parameters:")
    print(f"  Aspect Ratio (AR): {AR}")
    print(f"  Mean Aerodynamic Chord (MAC): {mac}")
    
    # Call avl_out_parse to generate the SDF plugin
    print("\nGenerating advanced lift drag plugin SDF file...")
    frame_type = "custom"
    
    avl_out_parse.main(
        plane_name, frame_type, AR, mac, 
        ref_pt_x, ref_pt_y, ref_pt_z,
        num_ctrl_surfaces, area, ctrl_surface_order,
        inputs.avl_path
    )
    
    print(f"\nSDF plugin file generated successfully!")
    print(f"Output location: {current_path}/{plane_name}/{plane_name}.sdf")
    print(f"\nYou can now copy the contents of this file into your model.sdf")
    
    # Display the plot
    plot_src = f'{current_path}/{plane_name}.ps'
    plot_dest = f'{current_path}/{plane_name}/{plane_name}.ps'
    if os.path.exists(plot_src):
        shutil.move(plot_src, plot_dest)
        
        # Display the plot unless --no-display is specified
        if not inputs.no_display:
            print(f"\nOpening geometry visualization...")
            # Open with evince in the background so it stays open
            try:
                subprocess.run(['which', 'evince'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.Popen(['evince', plot_dest])
                print(f"Geometry plot displayed (close window when done)")
            except:
                print(f"(evince not found - plot saved to: {plot_dest})")
        else:
            print(f"\nGeometry plot saved to: {plot_dest}")
    
    # Clean up temporary command file
    if os.path.exists(commands_file):
        os.remove(commands_file)

if __name__ == '__main__':
    main()
