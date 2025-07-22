from dotenv import load_dotenv
import asyncio
import os
import sys

libdir = '/home/drux/demandResponse_UX_research/lib/helper_classes'

if os.path.exists(libdir):
    sys.path.append(libdir)

from KasaDRUX import KasaDRUX

kD = KasaDRUX()

load_dotenv()
un = os.getenv('KASA_UN')
pw = os.getenv('KASA_PW')
if not un or not pw:
    logger.error("Missing KASA_UN or KASA_PW in environment.")
    raise EnvironmentError("Missing Kasa credentials")

async def main():
    kD.setEventState()

    asyncio.sleep(30)

    kD.setNormalState()

# get event status

# listen for button

# get baseline

# predict event


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Main loop crashed: {e}")
