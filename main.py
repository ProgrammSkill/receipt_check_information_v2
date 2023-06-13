import os
from fnsapi.api import FNSApi
import json
from qreader import QReader
import cv2
import re

fns_api = FNSApi()
qreader = QReader()

os.environ.setdefault('FNS_API_MASTER_TOKEN', 'token')
os.environ.setdefault('FNS_API_BASE_URL', 'https://openapi.nalog.ru:8090/')
session_token = fns_api.get_session_token()['token']
user_id = 'user'
list_files = []

path = r'C:\Users\Admin\Downloads\Scan_check_1-1' #Path to the folder where checks are stored
all_files = os.listdir(path)
for file in os.listdir(path):
    if file.endswith('.jpg'):
        list_files.append(path + '\\' + file)


print(list_files)
list_data_from_qr_code = []
for file in list_files:
    try:
        image = cv2.cvtColor(cv2.imread(file), cv2.COLOR_BGR2RGB)
        decoded_text = qreader.detect_and_decode(image=image)
        for value in decoded_text:
            # Extracting the necessary data received via QR code
            dateTime = re.search('t=(.+?)&s', value).group(1)
            timestamp = dateTime[:4] + '-' + dateTime[4:6] + '-' + dateTime[6:8] + 'T' + dateTime[9:11] + ':' + \
            dateTime[11:] + ':00'
            sum = int(re.search('s=(.+?)&fn', value).group(1).replace('.', ''))
            fiscal_number = int(re.search('fn=(.+?)&i', value).group(1))
            fiscal_document_id = int(re.search('i=(.+?)&fp', value).group(1))
            fiscal_sign = int(re.search('fp=(.+?)&n', value).group(1))
            operation_type = int(re.search('&n=(.+?)$', value).group(1))

            dict_check = {
                'timestamp': timestamp,
                'sum': sum,
                'fiscal_number': fiscal_number,
                'operation_type': operation_type,
                'fiscal_document_id': fiscal_document_id,
                'fiscal_sign': fiscal_sign
            }
            list_data_from_qr_code.append(dict_check)
    except:
        pass

list_data_checks = []
for value in list_data_from_qr_code:
    result = fns_api.get_ticket(
        session_token,
        user_id,
        value["sum"],
        value["timestamp"],
        value["fiscal_number"],
        value["operation_type"],
        value["fiscal_document_id"],
        value["fiscal_sign"]
    )
    list_data_checks.append(result)

data = {
    'data': list_data_checks
}

with open("data_checks.json", "w") as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)