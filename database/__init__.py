from .config import DB_PATH
from .config import HELP_REQUEST_BUTTONS

from .init_db import init_db

from .admins import *
from .clients import *
from .messages import *
from .statistics import *


init_db()