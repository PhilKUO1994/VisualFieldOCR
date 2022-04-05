from cgi import test
import re
import os
from datetime import datetime

import cv2
import easyocr
import matplotlib.pyplot as plt
import pytesseract
from utils.generate_report import generate_report 
from paddleocr import PaddleOCR


pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
COMMON_CHRS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '-']
paddleocr=PaddleOCR(enable_mkldnn=True,use_tensorrt=True, use_angle_cls = True,use_gpu= False) 
def extract_eye(text):
    """
    Input: OCR-ed text
    Output: 0 for left and 1 for right
    """
    if 'Eye:' in text:
        idx = text.find('Eye:')
        text_nearby = text[idx: idx+10]
        # Eye: Right
        if 'Left' in text_nearby:
            return 0
        elif 'Right' in text_nearby:
            return 1
        else:
            return -1
    else:
        if 'OD' in text:
            return 1
        elif 'OS' in text:
            return 0
        else:
            return -1

def extract_date(text):
    try:
        if 'Date:' in text:
            idx = text.find('Date:')
            text_nearby = text[idx+6: idx+17].replace('，', ',')
            date_str = text_nearby.strip()
            if date_str.find('-') >= 4:
                # YYYY-MM-DD
                date = datetime.strptime(date_str, "%Y-%m-%d")
            elif ',' in date_str:
                text_nearby = text[idx+6: idx+19].replace('，', ',')
                date_str = text_nearby.strip()
                if 'Sept' in date_str:
                    space_idx = 4
                else:
                    space_idx = 3

                if date_str[space_idx] != ' ':
                    date_str = date_str[:space_idx] + ' ' + date_str[space_idx:]
                print(date_str)
                date = datetime.strptime(date_str, "%b %d,%Y")
            else:
                # MM-DD-YYYY
                date = datetime.strptime(date_str, "%m-%d-%Y")
            return date


        if '出生日期' in text:
            idx = text[text.find('出生日期')+10:].find('日期') + text.find('出生日期')+10
            print('+=======================')
            print(idx)
            text_nearby = text[idx+5: idx+15]
            print(text_nearby)
            date_str = text_nearby.strip()
            if date_str.find('/') >= 4:
                # YYYY/MM/DD
                date = datetime.strptime(date_str, "%Y/%m/%d")
            else:
                # MM-DD-YYYY
                date = datetime.strptime(date_str, "%m/%d/%Y")
            return date
    except:
        pass

def extract_vfi(text):
    idx = text.find('VFI')
    text_nearby = text[idx: idx+8]
    percentile_idx = text_nearby.find('%')
    vfi = text_nearby[percentile_idx-3: percentile_idx].strip()
    return vfi


def extract_md_psd(text):
    
    def find_dB_value(end_idx, text):
        start_idx = end_idx-1
        while text[start_idx] in COMMON_CHRS:
            start_idx -= 1
        else:
            return text[start_idx+1: end_idx]
    
    idx = text.find('MD')
    text_nearby = text[idx: idx+80].replace(' ','')
    idxs_dB = [i.start() for i in re.finditer('dB', text_nearby)]
    if len(idxs_dB) == 2:
        # find the number
        md_value = float(find_dB_value(idxs_dB[0], text_nearby))
        psd_value = float(find_dB_value(idxs_dB[1], text_nearby))

        # didnt recongize the dot
        md_value = md_value/100 if abs(md_value)>30 else md_value
        psd_value = psd_value/100 if abs(psd_value)>30 else psd_value
        return md_value, psd_value
    else:
        return False, False

test_dir = './test2/'
reader = easyocr.Reader(['en'], gpu=False)

ocr_result_dict = {
              0:{},
              1:{}
            }

for imgname in os.listdir(test_dir):
    if 'jpg' in imgname or 'png' in imgname:
        
        
        # use Tessert
        img = cv2.imread(test_dir + imgname)
        img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        text = pytesseract.image_to_string(img)
        print('=============', imgname, '================')
        MD, PSD = extract_md_psd(text)
        eye_side = extract_eye(text)
        date = extract_date(text)

        # use easyOCR to supplment the results
        if not MD or eye_side==-1 or not date: 
            #recong_texts = reader.readtext(img_gray)
            recong_texts = paddleocr.ocr(img_gray, cls=True)
            text = ''
            for object in recong_texts:
                text += ' ' + str(object[1][0]) + ' '
            print(text)
            if not MD:
                MD, PSD = extract_md_psd(text)
            if eye_side==-1:
                eye_side = extract_eye(text)
            if not date:
                date = extract_date(text)

        print('MD, PSD: ', MD, PSD)
        print('Eye: ', eye_side)
        print('Date: ', date)


        if eye_side != -1:
            ocr_result_dict[eye_side][date] = [MD, PSD]

generate_report(ocr_result_dict[0])
generate_report(ocr_result_dict[1])

print(ocr_result_dict)