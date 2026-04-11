# -*- coding: utf-8 -*-

import base64
import hashlib
import random
import re
import time
from datetime import timedelta

import fitz
from docx import Document


def getSkillName(path: str) -> str | None:
    match = re.search(r'/skills/([^/]+)/', path)
    if match: return match.group(1)
    match = re.search(r'skills/([^/]+)/', path)
    if match: return match.group(1)
    return None


def getMillisecond():
    return int(time.time() * 1000)


def getMixId():
    number = 731250000000000000
    now = datetime.now()
    tims = int(now.timestamp() * 1000)
    return str(tims + number)


def getToday():
    return datetime.now().strftime('%Y%m%d')


def getTimeFormat():
    return datetime.now().strftime('%H:%M:%S')


def isNumber(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def getCountFormat(num: int):
    today = datetime.today()
    future = today + timedelta(days=num)
    return future.strftime('%Y-%m-%d')


def getWeeks():
    today = datetime.today()
    dates = []
    for i in range(7):
        date = today - timedelta(days=i)
        dates.append(date.strftime('%Y%m%d'))
    return dates


def generateMD5(input):
    return hashlib.md5(input.encode('utf-8')).hexdigest()


def base64Encode(text: str):
    bytes = text.encode('utf-8')
    code = base64.b64encode(bytes)
    return code.decode()


def base64Decode(code: str):
    bytes = base64.b64decode(code)
    return bytes.decode('utf-8')


def markdownBeautify(word: str):
    list = word.split('\n\n')
    for i, item in enumerate(list):
        if '#### ' in item:
            list[i] = (item.replace('#### ', '***') + '***')
    word = '\n\n'.join(list)
    return word


def extractTextPdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block['type'] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text += span["text"] + " "
                text += "\n"
    return text


def extractTextDoc(docx_path):
    doc = Document(docx_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text


from datetime import datetime


def getHourFormat(timeOld: int) -> str:
    currentTime = int(datetime.now().timestamp() * 1000)
    dateTime1 = datetime.fromtimestamp(timeOld / 1000)
    dateTime2 = datetime.fromtimestamp(currentTime / 1000)
    timeDiff = timeOld - currentTime
    hour = f"{dateTime1.hour:02d}"
    minute = f"{dateTime1.minute:02d}"
    if dateTime1.year == dateTime2.year and dateTime1.month == dateTime2.month and dateTime1.day == dateTime2.day:
        timeStr = f"今天 {hour}:{minute}"
    elif 60000 < timeDiff < 86400000:
        timeStr = f"明天 {hour}:{minute}"
    elif dateTime1.year == dateTime2.year:
        timeStr = f"{dateTime1.month}月{dateTime1.day}日 {hour}:{minute}"
    else:
        timeStr = f"{dateTime1.year}年{dateTime1.month}月{dateTime1.day}日 {hour}:{minute}"
    return timeStr


def strToTimestamp(timeStr: str) -> int:
    dt = datetime.strptime(timeStr, "%Y-%m-%d %H:%M:%S")
    return int(dt.timestamp() * 1000)


def generateCode():
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def isValidEmail(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def clearPycache():
    import shutil
    import os
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            cache_dir = os.path.join(root, '__pycache__')
            shutil.rmtree(cache_dir)
            print(f"已清理缓存目录: {cache_dir}")
