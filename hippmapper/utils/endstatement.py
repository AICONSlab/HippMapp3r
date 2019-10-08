#! /usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# coding: utf-8

import os
import pwd
import re
from datetime import datetime
import warnings
warnings.simplefilter("ignore", RuntimeWarning)
warnings.simplefilter("ignore", FutureWarning)


def main(task=None, timediff=None):
    """
    Generates end statement based on function/task and time difference
    """
    name = pwd.getpwuid(os.getuid())[4]

    if re.search('[a-zA-Z]', name):
        user = name.split(" ")[0]
        user = user.replace(',', '').strip()
    else:
        user = os.environ['USER']

    if 6 < datetime.now().hour < 12:
        timeday = 'morning'
    elif 12 <= datetime.now().hour < 18:
        timeday = 'afternoon'
    elif 18 <= datetime.now().hour < 22:
        timeday = 'evening'
    else:
        timeday = 'night'

    print("\n %s done in %s ... Have a good %s %s!\n" % (task, timediff, timeday, user))


if __name__ == "__main__":
    main()