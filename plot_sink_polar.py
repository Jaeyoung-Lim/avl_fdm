#!/usr/bin/env python3

import argparse
import os
import subprocess
import shutil
import numpy as np
import matplotlib.pyplot as plt
import re
import time
from typing import List, Tuple

"""
Extract aerodynamic coefficients from AVL output file.

Args:
    filepath (str): Path to AVL output file

Return:
    dict: Dictionary with CL, CD, alpha, and other coefficients
"""
def parse_avl_output(filepath: str) -> dict:
    coeffs = {
        'Alpha': None,
        'CLtot': None,
        'CDtot': None,
        'Cmtot': None,
        'CYtot': None,
    }
    
    with open(filepath, 'r') as f:
        for line in f:
            for key in coeffs.keys():
                if f' {key} ' in line or f'{key} =' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == key and i + 2 < len(parts):
                            try:
                                coeffs[key] = float(parts[i + 2])
                            except ValueError:
                                # Try the next token
                                if i + 3 < len(parts):
                                    try:
                                        coeffs[key] = float(parts[i + 3])
                                    except ValueError:
                                        pass
                            break
    
    return coeffs


"""
Parse AVL file to extract aircraft parameters.

Args:
    avl_file_path (str): Path to the AVL file

Return:
    dict: Dictionary containing extracted parameters
"""
def parse_avl_file(avl_file_path: str) -> dict:
    params = {
        'vehicle_name': None,
        'area': None,
        'chord': None,
        'span': None,
    }
    
    with open(avl_file_path, 'r') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Get vehicle name
        if params['vehicle_name'] is None:
            if line and not line.startswith('!') and not line.startswith('#'):
                if not re.match(r'^[\d\.\-\s]+$', line):
                    params['vehicle_name'] = line.strip()
                    i += 1
                    continue
        
        # Look for Sref, Cref, Bref
        if 'Sref' in line and 'Cref' in line and 'Bref' in line:
            if not line.startswith('!'):
                parts = line.split('!')
                if len(parts) > 0:
                    values = parts[0].strip().split()
                    if len(values) >= 3:
                        params['area'] = float(values[0])
                        params['chord'] = float(values[1])
                        params['span'] = float(values[2])
            else:
                if i + 1 < len(lines):
                    values = lines[i + 1].strip().split()
                    if len(values) >= 3:
                        params['area'] = float(values[0])
                        params['chord'] = float(values[1])
                        params['span'] = float(values[2])
                i += 1
                continue
        
        i += 1
    
    return params


"""
Run AVL to generate aerodynamic coefficients for a range of alpha values.

Args:
    avl_file (str): Path to AVL file
    alpha_range (tuple): (min_alpha, max_alpha, num_points)
    avl_path (str): Path to AVL installation
    output_dir (str): Directory to store output files

Return:
    List[dict]: List of dictionaries containing alpha, CL, CD, etc.
"""
def run_avl_sweep(avl_file: str, alpha_range: Tuple[float, float, int], 
                  avl_path: str, output_dir: str) -> List[dict]:
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get AVL file name and directory
    avl_filename = os.path.basename(avl_file)
    avl_dir = os.path.dirname(avl_file)
    vehicle_name = os.path.splitext(avl_filename)[0]
    
    # Copy AVL file to output directory
    output_avl = os.path.join(output_dir, avl_filename)
    shutil.copy(avl_file, output_avl)
    
    # Find and copy any airfoil data files (.dat) referenced in the AVL file
    with open(avl_file, 'r') as f:
        avl_content = f.read()
        # Look for AFILE directives
        for line in avl_content.split('\n'):
            if line.strip() and not line.strip().startswith('!'):
                # Check if this looks like an airfoil filename
                if '.dat' in line.lower() or 'AFILE' in line.upper():
                    # Next non-comment line after AFILE is the filename
                    continue
                # If previous line was AFILE, this might be the filename
                if '.dat' in line:
                    airfoil_file = line.strip()
                    # Look for this file in the same directory as the AVL file
                    source_airfoil = os.path.join(avl_dir, airfoil_file)
                    if os.path.exists(source_airfoil):
                        dest_airfoil = os.path.join(output_dir, airfoil_file)
                        shutil.copy(source_airfoil, dest_airfoil)
    
    # Also copy all .dat files from the AVL file directory
    if avl_dir:
        for file in os.listdir(avl_dir):
            if file.endswith('.dat'):
                source = os.path.join(avl_dir, file)
                dest = os.path.join(output_dir, file)
                if os.path.isfile(source):
                    shutil.copy(source, dest)
    
    # Generate alpha values
    alpha_min, alpha_max, num_points = alpha_range
    alphas = np.linspace(alpha_min, alpha_max, num_points)
    
    results = []
    
    print(f"Running AVL sweep from {alpha_min}° to {alpha_max}° ({num_points} points)...")
    
    for i, alpha in enumerate(alphas):
        print(f"  [{i+1}/{num_points}] Alpha = {alpha:.2f}°", end='', flush=True)
        
        # Create AVL command file
        output_filename = f'polar_alpha_{alpha:.2f}.txt'
        output_file = os.path.join(output_dir, output_filename)
        
        avl_commands = f"""oper
a a {alpha}
x
st {output_filename}


quit
"""
        
        commands_file = os.path.join(output_dir, 'temp_commands.txt')
        with open(commands_file, 'w') as f:
            f.write(avl_commands)
        
        # Run AVL
        avl_binary = os.path.join(avl_path, 'Avl', 'bin', 'avl')
        
        # Read commands as string instead of file handle
        with open(commands_file, 'r') as f:
            commands_str = f.read()
        
        result = subprocess.run(
            f'{avl_binary} {avl_filename}',
            input=commands_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            cwd=output_dir
        )
        
        # Small delay to ensure file is written
        time.sleep(0.1)
        
        if result.returncode != 0:
            print(f"\n  WARNING: AVL failed for alpha={alpha}")
            if i == 0:  # Print error details for first failure
                print(f"    stdout: {result.stdout[:200]}")
                print(f"    stderr: {result.stderr[:200]}")
            continue
        
        # Parse output
        if os.path.exists(output_file):
            coeffs = parse_avl_output(output_file)
            if coeffs['CLtot'] is not None and coeffs['CDtot'] is not None:
                results.append(coeffs)
                print(f"  CL={coeffs['CLtot']:.4f}, CD={coeffs['CDtot']:.5f}")
            else:
                print(f"\n  WARNING: Could not extract coefficients for alpha={alpha}")
                if i == 0:  # Show file content for debugging
                    print(f"    Checking output file: {output_file}")
                    with open(output_file, 'r') as f:
                        print(f"    First 200 chars: {f.read(200)}")
        else:
            print(f"\n  WARNING: Output file not created for alpha={alpha}")
            if i == 0:  # Debug first failure
                abs_output_file = os.path.abspath(output_file)
                print(f"    Expected file: {output_file}")
                print(f"    Absolute path: {abs_output_file}")
                print(f"    File exists (relative): {os.path.exists(output_file)}")
                print(f"    File exists (absolute): {os.path.exists(abs_output_file)}")
                print(f"    Working dir: {output_dir}")
                print(f"    Current Python dir: {os.getcwd()}")
                print(f"    Files in output_dir: {os.listdir(output_dir)[:15]}")
                print(f"    AVL stdout: {result.stdout[:300] if result.stdout else 'None'}")
                print(f"    AVL stderr: {result.stderr[:300] if result.stderr else 'None'}")
                print(f"    AVL returncode: {result.returncode}")
                # Save commands for manual inspection
                print(f"    Commands file saved for inspection: {commands_file}")
    
    # Clean up (skip if debugging first failure)
    if os.path.exists(commands_file) and len(results) > 0:
        os.remove(commands_file)
    
    return results


"""
Calculate sink polar data from aerodynamic coefficients.

Args:
    results (List[dict]): List of coefficient dictionaries
    weight (float): Aircraft weight in Newtons
    area (float): Wing area in m^2
    rho (float): Air density in kg/m^3

Return:
    Tuple[np.ndarray, np.ndarray]: Arrays of airspeed and sink rate
"""
def calculate_sink_polar(results: List[dict], weight: float, 
                         area: float, rho: float = 1.225) -> Tuple[np.ndarray, np.ndarray]:
    
    velocities = []
    sink_rates = []
    
    for coeffs in results:
        CL = coeffs['CLtot']
        CD = coeffs['CDtot']
        
        # Skip invalid data points
        if CL <= 0 or CD <= 0:
            continue
        
        # Calculate airspeed from lift equation: L = 0.5 * rho * V^2 * S * CL
        # At equilibrium, L = W, so: V = sqrt(2 * W / (rho * S * CL))
        velocity = np.sqrt(2 * weight / (rho * area * CL))
        
        # Calculate sink rate from: sink_rate = D/L * V = (CD/CL) * V
        # Or equivalently: sink_rate = V / (L/D)
        sink_rate = velocity * (CD / CL)
        
        velocities.append(velocity)
        sink_rates.append(sink_rate)
    
    return np.array(velocities), np.array(sink_rates)


"""
Plot the sink polar.

Args:
    velocities (np.ndarray): Airspeed values in m/s
    sink_rates (np.ndarray): Sink rate values in m/s
    output_file (str): Path to save the plot
    vehicle_name (str): Name of the vehicle
"""
def plot_sink_polar(velocities: np.ndarray, sink_rates: np.ndarray, 
                    output_file: str, vehicle_name: str):
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Plot the polar
    ax.plot(velocities, sink_rates, 'b-', linewidth=2, label='Sink Polar')
    ax.plot(velocities, sink_rates, 'ro', markersize=4)
    
    # Find minimum sink rate (best glide)
    min_sink_idx = np.argmin(sink_rates)
    min_sink_velocity = velocities[min_sink_idx]
    min_sink_rate = sink_rates[min_sink_idx]
    
    # Find best glide ratio (minimum sink rate / velocity)
    glide_ratios = sink_rates / velocities
    best_glide_idx = np.argmin(glide_ratios)
    best_glide_velocity = velocities[best_glide_idx]
    best_glide_sink = sink_rates[best_glide_idx]
    best_glide_ratio = velocities[best_glide_idx] / sink_rates[best_glide_idx]
    
    # Mark special points
    ax.plot(min_sink_velocity, min_sink_rate, 'gs', markersize=12, 
            label=f'Min Sink: {min_sink_rate:.3f} m/s @ {min_sink_velocity:.2f} m/s')
    ax.plot(best_glide_velocity, best_glide_sink, 'ms', markersize=12,
            label=f'Best L/D: {best_glide_ratio:.1f} @ {best_glide_velocity:.2f} m/s')
    
    # Add grid
    ax.grid(True, alpha=0.3)
    
    # Labels and title
    ax.set_xlabel('Airspeed (m/s)', fontsize=12)
    ax.set_ylabel('Sink Rate (m/s)', fontsize=12)
    ax.set_title(f'Sink Polar - {vehicle_name}', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    
    # Invert y-axis so lower sink rates are at the top
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nSink polar plot saved to: {output_file}")
    
    # Print performance summary
    print(f"\n{'='*60}")
    print(f"PERFORMANCE SUMMARY - {vehicle_name}")
    print(f"{'='*60}")
    print(f"Minimum Sink Rate:    {min_sink_rate:.3f} m/s @ {min_sink_velocity:.2f} m/s")
    print(f"Best Glide Ratio:     {best_glide_ratio:.1f}:1 @ {best_glide_velocity:.2f} m/s")
    print(f"Velocity Range:       {velocities.min():.2f} - {velocities.max():.2f} m/s")
    print(f"{'='*60}\n")
    
    return fig


"""
Main function to generate sink polar from AVL file.
"""
def main():
    parser = argparse.ArgumentParser(
        description='Generate sink polar plot from AVL file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate sink polar with default settings
  python3 plot_sink_polar.py --avl_file models/fms_fox.avl --weight 2.0
  
  # Specify custom alpha range and output directory
  python3 plot_sink_polar.py --avl_file models/fms_fox.avl --weight 2.0 \\
      --alpha_min -5 --alpha_max 15 --num_points 30 --output_dir results
  
  # Custom air density for high altitude
  python3 plot_sink_polar.py --avl_file models/fms_fox.avl --weight 2.0 \\
      --rho 1.0 --output_dir high_altitude
        """
    )
    
    parser.add_argument("--avl_file", required=True,
                       help="Path to AVL file")
    parser.add_argument("--weight", type=float, required=True,
                       help="Aircraft weight in kg")
    parser.add_argument("--alpha_min", type=float, default=-5.0,
                       help="Minimum angle of attack (degrees) [default: -5]")
    parser.add_argument("--alpha_max", type=float, default=20.0,
                       help="Maximum angle of attack (degrees) [default: 20]")
    parser.add_argument("--num_points", type=int, default=25,
                       help="Number of points in alpha sweep [default: 25]")
    parser.add_argument("--rho", type=float, default=1.225,
                       help="Air density in kg/m^3 [default: 1.225 at sea level]")
    parser.add_argument("--output_dir", default="polar_data",
                       help="Directory for output files [default: polar_data]")
    parser.add_argument("--avl_path", default=None,
                       help="Path to AVL installation (auto-detected if not specified)")
    parser.add_argument("--show", action="store_true",
                       help="Display the plot interactively")
    
    args = parser.parse_args()
    
    # Check if AVL file exists
    if not os.path.exists(args.avl_file):
        print(f"ERROR: AVL file not found: {args.avl_file}")
        return
    
    # Find AVL installation
    if args.avl_path is None:
        user = os.environ.get('USER')
        target_directory_path = None
        for root, dirs, _ in os.walk(f'/home/{user}/'):
            if "Avl" in dirs:
                target_directory_path = os.path.dirname(os.path.join(root, "Avl"))
                break
        
        if target_directory_path is None:
            print("ERROR: AVL installation not found. Please install AVL or specify --avl_path")
            return
        
        args.avl_path = target_directory_path
    
    print(f"Using AVL installation at: {args.avl_path}")
    
    # Parse AVL file
    print(f"\nParsing AVL file: {args.avl_file}")
    params = parse_avl_file(args.avl_file)
    
    if params['area'] is None or params['span'] is None:
        print("ERROR: Could not extract wing area and span from AVL file")
        return
    
    vehicle_name = params['vehicle_name'] or os.path.splitext(os.path.basename(args.avl_file))[0]
    area = params['area']
    span = params['span']
    
    print(f"  Vehicle: {vehicle_name}")
    print(f"  Wing Area: {area} m^2")
    print(f"  Wing Span: {span} m")
    print(f"  Weight: {args.weight} kg ({args.weight * 9.81:.2f} N)")
    print(f"  Air Density: {args.rho} kg/m^3")
    
    # Run AVL sweep
    alpha_range = (args.alpha_min, args.alpha_max, args.num_points)
    results = run_avl_sweep(args.avl_file, alpha_range, args.avl_path, args.output_dir)
    
    if len(results) < 3:
        print("ERROR: Not enough valid data points generated. Check AVL output.")
        return
    
    print(f"\nSuccessfully generated {len(results)} data points")
    
    # Calculate sink polar
    weight_N = args.weight * 9.81  # Convert kg to Newtons
    velocities, sink_rates = calculate_sink_polar(results, weight_N, area, args.rho)
    
    # Plot the polar
    output_plot = os.path.join(args.output_dir, f"{vehicle_name}_sink_polar.png")
    plot_sink_polar(velocities, sink_rates, output_plot, vehicle_name)
    
    # Save data to CSV
    csv_file = os.path.join(args.output_dir, f"{vehicle_name}_polar_data.csv")
    with open(csv_file, 'w') as f:
        f.write("Airspeed_m/s,Sink_Rate_m/s,L/D_Ratio,Alpha_deg,CL,CD\n")
        for i, (v, s) in enumerate(zip(velocities, sink_rates)):
            if i < len(results):
                alpha = results[i]['Alpha']
                CL = results[i]['CLtot']
                CD = results[i]['CDtot']
                LD = CL / CD if CD > 0 else 0
                f.write(f"{v:.4f},{s:.4f},{LD:.4f},{alpha:.4f},{CL:.6f},{CD:.6f}\n")
    
    print(f"Polar data saved to: {csv_file}")
    
    # Show plot if requested
    if args.show:
        plt.show()
    
    print(f"\nDone! Check {args.output_dir}/ for all output files.")


if __name__ == '__main__':
    main()
