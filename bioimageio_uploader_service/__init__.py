import os
import sys

import dotenv
dotenv.load_dotenv()

if sys.version_info[0] < 3:
    raise RuntimeError("Must be run with Python 3")
if sys.version_info[1] >= 11:
    import tomllib
else:
    import tomli as tomllib

__root_folder__ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
__version__ = tomllib.load(open(os.path.join(__root_folder__, 'pyproject.toml'), 'rb')).get('project', {}).get('version')

