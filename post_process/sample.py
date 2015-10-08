#!/usr/bin/python
import os
import json


def main():
	print("Sample Post Script")

	files = json.loads(os.environ.get('MH_FILES'))

	for filename in files:
		print(filename)

if __name__ == "__main__":
    main()
