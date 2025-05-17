'''网络Base'''
from railgo.config import LOGGER
import requests
import time
import retry

import warnings
warnings.filterwarnings('ignore')

@retry.retry(tries=5, delay=5)
def get(url, headers={}, data={}):
    tc = 0
    while tc < 5:
        try:
            r = requests.get(url, headers=headers,
                             data=data)
            if r.status_code == 200:
                return r
            LOGGER.warning(f"Request Error {url}:{r.text}")
        except Exception as e:
            LOGGER.exception(e)
        finally:
            tc += 1
        time.sleep(10)
    raise ConnectionRefusedError("Too fast or data error")

@retry.retry(tries=5, delay=5)
def post(url, headers={}, json={}, data={}):
    tc = 0
    while tc < 5:
        try:
            r = requests.post(url, headers=headers,
                              json=json, data=data)
            if r.status_code == 200:
                return r
            LOGGER.warning(f"Request Error {url}:{r.text}")
        except Exception as e:
            LOGGER.exception(e)
        finally:
            tc += 1
    raise ConnectionRefusedError("Too fast or data error")
