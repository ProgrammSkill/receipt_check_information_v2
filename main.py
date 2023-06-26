import os
from fnsapi.api import FNSApi
import json
from pydrive.drive import GoogleDrive
from qreader import QReader
import cv2
import re
import ast
import httplib2
from pydrive.auth import GoogleAuth
import googleapiclient
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from pdf2image import convert_from_path
from os.path import abspath
import warnings

warnings.filterwarnings("ignore")

fns_api = FNSApi()
qreader = QReader()
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

path = str(abspath(os.curdir)) + '\Checks' #Path to the folder where checks are stored

all_files = os.listdir(path)
for file in os.listdir(path):
    os.remove(os.path.join(path, file)) #Clearing previous checks

# Downloading files from Google Drive
folder_id = 'folder id from Google Drive'
def download_files_from_folder(folder_id):
    file_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format(folder_id)}).GetList()
    for file in file_list:
        if file['mimeType'] == 'application/vnd.google-apps.folder':
            download_files_from_folder(file['id'])
        else:
            try:
                file.GetContentFile(path + '\\' + file['title'])
            except:
                pass

download_files_from_folder(folder_id)

for file in os.listdir(path):
    if file.endswith('.pdf'):
        images = convert_from_path(path + '/' + file)
        for i in range(len(images)):
            # Save pages as images in the pdf
                images[i].save(path + '/' + file + ' page ' + str(i) + '.jpg', 'JPEG')
                os.remove(os.path.join(path, file))

os.environ.setdefault('FNS_API_MASTER_TOKEN', 'your token')
os.environ.setdefault('FNS_API_BASE_URL', 'https://openapi.nalog.ru:8090/')
session_token = fns_api.get_session_token()['token']
user_id = 'user'
list_files = []

all_files = os.listdir(path)
for file in os.listdir(path):
    if file.endswith('.jpg') or file.endswith('.png'):
        list_files.append(path + '\\' + file)

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
with open(str(abspath(os.curdir)) + "data_checks.json", "w") as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)

# Connecting to the API
spreadsheet_id = '15Mj2PEX6lcM_0io_NxxwQUHCFbApcq-vmD6L6_P1SeQ'
creds_json = os.path.dirname(__file__) + "/robust-carver.json"
scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds_service = ServiceAccountCredentials.from_json_keyfile_name(creds_json, scopes).authorize(httplib2.Http())
service = googleapiclient.discovery.build('sheets', 'v4', http=creds_service)

rangeAll = '{0}!A1:Z'.format('Лист1')
body = {}
resultClear = service.spreadsheets().values().clear(spreadsheetId=spreadsheet_id, range=rangeAll, body=body).execute()

title_list = {
    'values': [
        ['Номер чека', 'Дата', 'Итоговая сумма', 'Тип чека', 'Организация', 'Наименование', 'Количество', 'Цена',
         'Сумма', 'НДС', 'Тип номенклатуры']
    ]
}
resp = service.spreadsheets().values().append(
    spreadsheetId=spreadsheet_id,
    range="Лист1!A1",
    valueInputOption="RAW",
    body=title_list).execute() #Writing table headers

row = 2
for data_check in list_data_checks:
    message = ast.literal_eval(data_check["message"])
    date = message["receiveDate"]
    date = date[8:10] + '.' + date[5:7] + '.' + date[0:4]
    content = message["content"]
    fiscalDocumentNumber = content["fiscalDocumentNumber"]
    totalSum = str(content["totalSum"])[:-2] + ',' + str(content["totalSum"])[-2:]
    organization = content["user"]

    operationType = str(content["operationType"])
    if operationType == '1' or operationType == '2':
        operationType = 'Приход'
    else:
        operationType = 'Расход'

    nomenclature = content['items']
    str_nomenclature = ''
    row_nomenclature = row
    for n in nomenclature:
        nds = str(n['nds'])

        if nds == '1':
            nds = '20%'
        elif nds == '2':
            nds = '20%'
        elif nds == '3':
            nds = '20/120'
        elif nds == '4':
            nds = '10/110'
        elif nds == '5':
            nds = '0%'
        else:
            nds = 'Без НДС'

        productType = str(n['productType'])
        if productType == '1' or productType == '2' or productType == '30' or productType == '31' or productType == '32'\
                or productType == '33':
            productType = 'Товар'
        else:
            productType = 'Услуга'

        body = {
            'values': [
                [n['name'], n['quantity'], str(n['price'])[:-2] + ',' + str(n['price'])[-2:], str(n['sum'])[:-2] +\
                            ',' + str(n['sum'])[-2:], nds, productType]
            ]
        }
        resp = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="Лист1!F" + str(row_nomenclature),
            valueInputOption="RAW",
            body=body).execute()

        if len(nomenclature) > 1:
            row_nomenclature +=1

    body = {
        'values': [
            [fiscalDocumentNumber, date, totalSum, operationType, organization]
        ]
    }

    resp = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="Лист1!A" + str(row),
        valueInputOption="RAW",
        body=body).execute()

    if len(nomenclature) > 1:
        row = row_nomenclature
    else:
        row +=1