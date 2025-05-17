import requests
import json
import hashlib
import time
import urllib.parse
import gzip
import struct
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from railgo.config import *

import warnings
warnings.filterwarnings('ignore')

def postM(api, form):
    '''MpaaS表单通讯'''
    ts = time.strftime("%Y%m%d%H%M%S")
    form["baseDTO"] = {
        "check_code": hashlib.md5(b"F"+ts.encode()+b"TEMP-ZtHkH8JaHw4DACg6y/l2Wykr").hexdigest(),
        "device_no": "TEMP-ZtHkH8JaHw4DACg6y/l2Wykr",
        "h5_app_id": "60000013",
        "h5_app_version": "5.8.2.23",
        "hwv": "BNE-AL00",
        "mobile_no": "",
        "os_type": "a",
        "time_str": ts,
        "user_name": "",
        "version_no": "5.8.2.13"
    }

    rc = AES.new(MGW_RQ_KEY, AES.MODE_CBC, MGW_RQ_IV).encrypt(pad(gzip.compress(json.dumps([{
        "_requestBody": form
    }]).encode()), 16))
    payload = bytes.fromhex(
        "02" +
        "{:06x}".format(len(MGW_RG_CONST)) +
        MGW_RG_CONST.hex() +
        "0f" +
        "{:06x}".format(len(rc)) +
        rc.hex()
    )

    r = requests.post(
        MGW_PATH,
        data=payload,
        headers={
            "pagets": "",
            "nbappid": "60000013",
            "nbversion": "5.8.2.23",
            "appv": "5.8.2.13",
            "user-agent": "Dalvik/2.1.0 (Linux; U; Android 12; BNE-AL00 Build/V417IR)",
            "Platform": "ANDROID",
            "AppId": "9101430221728",
            "WorkspaceId": "product",
            "Version": "2",
            "Operation-Type": "com.cars.otsmobile."+api,
            "x-app-sys-Id": "com.MobileTicket",
            "Retryable2": "0",
            "x-mgs-encryption": "1",
            "x-Content-Encoding": "mgss",
            "Content-Type": "application/json",
        }, verify = False)
    if r.content == b'':
        raise ConnectionError(
            "mPaaS Request Failed: "+r.headers["Result-Status"]+" "+urllib.parse.unquote(r.headers["Memo"]))

    return json.loads(gzip.decompress(unpad(AES.new(MGW_RQ_KEY, AES.MODE_CBC, MGW_RQ_IV).decrypt(r.content), 16)).decode())