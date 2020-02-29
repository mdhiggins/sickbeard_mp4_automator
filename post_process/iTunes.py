#!/usr/bin/python
import os
import subprocess
import json


def main():
    print("iTunes Notification Script")

    if (os.name != 'posix'):
        print("iTunes.py post processing script requires OS X.")
        return

    MH_FILES = os.environ.get('SMA_FILES')
    if not (MH_FILES):
        print("Did not find environment variables.")
        return

    files = json.loads(MH_FILES)
    current_directory = os.path.dirname(os.path.realpath(__file__))
    add_to_itunes_script_path = os.path.join(current_directory, 'resources', 'add_to_itunes.scpt')

    for filename in files:
        if not os.path.exists(filename):
            print("The file '%s' you are trying to add to iTunes at does not exist." % filename)
        else:
            try:
                subprocess.call(['osascript', add_to_itunes_script_path, filename])
                print("%s added to iTunes." % filename)
                subprocess.call(['rm', '-rf', filename])
            except Exception as e:
                print('Error adding %s to iTunes.' % filename)
                print(e)


if __name__ == "__main__":
    main()
