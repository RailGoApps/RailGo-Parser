import requests
import time



import hashlib
import urllib.parse
import json
import warnings
warnings.filterwarnings('ignore')

def postM(api, form):
    '''MpaaS表单通讯'''
    t=time.localtime()
    ts = time.strftime("%Y%m%d%H%M%S",t)
    form["baseDTO"] = {
        "check_code": hashlib.md5(b"F"+ts.encode()+b"TEMP-ZtHkH8JaHw4DACg6y/l2Wykr").hexdigest(),
        "device_no": "TEMP-ZtHkH8JaHw4DACg6y/l2Wykr",
        "h5_app_id": "60000013",
        "h5_app_version": "5.9.0.17",
        "hwv": "BNE-AL00",
        "mobile_no": "",
        "os_type": "a",
        "time_str": ts,
        "user_name": "",
        "version_no": "5.9.0.8"
    }
    r = requests.post(
        "https://mobile.12306.cn/otsmobile/app/mgs/mgw.htm?operationType=com.cars.otsmobile."+api+"&requestData="+urllib.parse.urlencode({"c":json.dumps(form).replace(" ","")}).split("=")[1]+"&ts="+str(int(time.mktime(t))*1000)+"&sign=j9wkld5lo6kydnordwx9xy2amvzznj8e",verify = False,
        headers={
            "user-agent": "Dalvik/2.1.0 (Linux; U; Android 12; BNE-AL00 Build/V417IR)",
            "cookie":"BIGipServernginxformobile=343277834.44075.0000; path=/"
        })
    print(r.text)
    print(r.headers)

postM("com.cars.otsmobile.queryLeftTicketG",{"train_date": "20251004", "purpose_codes": "00",
                 "from_station": "SHH", "to_station": "BJP",
                 "station_train_code": "", "start_time_begin": "0000", "start_time_end": "2400", "train_headers": "QB#",
                 "train_flag": "", "seat_type": "0", "seatBack_Type": "", "ticket_num": "", "dfpStr": ""})

#from railgo.parser.utils.client_app import postM
#
#d = postM("initStation",{})
#print(d)