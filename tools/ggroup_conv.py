#!/bin/python3
import sys
import textwrap
import os

def main():
	if len(sys.argv) != 2:
		print(textwrap.dedent(f"""
		ERROR: not enough arguments provided.

		Converts selection data from google groups to tsv and prints them to stdout.
		Get the data from: https://groups.google.com/u/{{account_id}}/a/v-lo.krakow.pl/g/nauczyciele/members
	
		Usage:
		ggroup_conv.py [input_file]
		"""))
		exit(1)
	
	path = sys.argv[1]
	if not os.path.exists(path):
		print(f"ERROR: \"{path}\" is not a valid file.")
		exit(1)
	
	f = open(path, "r")
	data = f.read().splitlines()
	f.close()

	pairs = []
	for i, line in enumerate(data):
		if "@" in line:
			pairs.append([line, data[i-1]])
	
	for email, name in pairs:
		print(f"{email};{name}")

if __name__ == "__main__":
	main()