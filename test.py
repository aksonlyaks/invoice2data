from invoice2data import extract_data
from invoice2data.extract.loader import read_templates
from os import walk
import logging
import threading
import time
import signal
import sys

logger = logging.getLogger(__name__)

# PATH of the Test Bills
FOLDER_PATH="/home/ec2-user/invoicedata_test/receipts/28551694_Sai_khushi_foods/"
# TID for the template to chose
TID = "28551694"
INPUT_MODULE= "png"
TARGET_INDEX = 0

CGREEN  = '\33[32m'
CYELLOW = '\33[33m'
CEND = '\033[0m'

r, d, filenames = next(walk(FOLDER_PATH))
issue_list = []

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    for issue in issue_list:
        print(issue)
    sys.exit(0)


def thread_fn(file, dummy):
    total_missed = 0
    total_corrected = 0
    total_line_with_issue = 0

    cmdlist = ["tesseract", "-c", "tessedit_char_whitelist=/.: abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"]
    templates = read_templates('./templates')
    result, missed, corrected, issue_lines, qtyerr, noofitem = extract_data(r+file, input_module=INPUT_MODULE, templates=templates, cmdlist=cmdlist, conv_cmdlist=None, tid = TID)

    total_missed = total_missed + missed
    total_corrected = total_corrected + corrected
    total_line_with_issue = total_line_with_issue + len(issue_lines)

    #logger.error("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    report = f'=============================> missed: {missed} corrected: {corrected} line with issue: {len(issue_lines)} Qty issue: {qtyerr} Total Items: {noofitem}<============================'
    if missed != 0 or qtyerr != "Match":
        logger.error(CYELLOW + report + CEND)
        issue_list.append(file+"\t"+report)
    else:
        logger.error(CGREEN + report + CEND)


index = 0
signal.signal(signal.SIGINT, signal_handler)
for file in filenames:
    if TID not in file or "png" not in file:
        continue
    index = index + 1
    if index < TARGET_INDEX:
        continue

    logger.error(f'{index}. File name is {file} ')

    #if file != "_28551694___06:25:39-03-04-2021.436_bill.png":
    #    continue
    time.sleep(1)

    upload_thread = threading.Thread(target=thread_fn, args= (file, 1))
    upload_thread.start()

    #logger.error("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


