import os
import subprocess

from hippmapper import DEPENDS_DIR

class add_paths():
    """ Context manager to add c3d and ANTs to PATH environment variable while function is being called.
    Files will be removed after use.
    """
    def __init__(self):
        self.command_paths = dict(ANTS=os.path.join(DEPENDS_DIR, "ANTs"),
                                  c3d=os.path.join(DEPENDS_DIR, "c3d/bin"))
        self.added_paths = []  # empty list for all paths to be added

    def __enter__(self):
        for command in self.command_paths.keys():
            # if command doesnt have path, add path to env variable
            try:
                subprocess.check_output(["which", command])
            except subprocess.CalledProcessError: # command was not found
                if os.path.exists(self.command_paths[command]):
                    os.environ['PATH'] += os.pathsep + self.command_paths[command]
                    self.added_paths.append(self.command_paths[command])
                else:  # if installation script hasnt been run
                    print("The command {} has not been installed. Install it locally by running install_scripts.sh".format(command))
                    exit()

    def __exit__(self, exc_type, exc_value, traceback):
        for path in self.added_paths:  # remove all added PATH variables
            try:
                os.environ['PATH'] = os.environ['PATH'].replace(path, '')
            except ValueError:
                pass
