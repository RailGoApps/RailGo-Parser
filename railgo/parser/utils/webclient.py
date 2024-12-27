'''网络Base'''
from railgo.config import LOGGER
import requests
import time


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
