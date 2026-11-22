import argparse

parser = argparse.ArgumentParser()

parser.add_argument("input_file_name")
parser.add_argument("scheduling", choices=["EDF", "RM"])
parser.add_argument("energy_efficient", nargs="?", choices=["EE"], default=None)

args = parser.parse_args()

print("Input file:", args.input_file_name)
print("Scheduling:", args.scheduling)
print("Energy efficient:", args.energy_efficient is not None)