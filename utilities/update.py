# runs at midnight to check for updates and branch changes
# don't run as a service, run in RC.local maybe

from dotenv import load_dotenv
import asyncio
import os
import sys
import logging
import time
from datetime import datetime, timedelta
import json

logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.INFO)

libdir = '/home/drux/demandResponse_UX_research/lib/helper_classes'
if os.path.exists(libdir):
    sys.path.append(libdir)

from Airtable import Airtable

load_dotenv()
atKey = os.getenv('AIRTABLE')

if not atKey:
    logger.error("Missing Airtable key in environment.")
    raise EnvironmentError("Missing Airtable credentials")

atEvents = Airtable(atKey,'apptjKq3GAr5CVOQT','system')


# checks airtable

# check current branch

# switch branch if necessary

# git stash

# git pull

# restart
