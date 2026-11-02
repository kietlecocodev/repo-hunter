import os
import sys

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", "repo-hunter", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
