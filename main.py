from cgi import test
import re
import os
import datetime
import copy 
import shutil
import ctypes
import platform

import cv2
import numpy as np
import easyocr
import matplotlib.pyplot as plt
import pytesseract
from pdf2jpg import pdf2jpg
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import PySimpleGUI as sg

from utils.generate_report import generate_report 


def make_dpi_aware():
    if int(platform.release()) >= 8:
        ctypes.windll.shcore.SetProcessDpiAwareness(True)

make_dpi_aware()
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
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
                date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            elif ',' in date_str:
                text_nearby = text[idx+6: idx+19].replace('，', ',')
                date_str = text_nearby.strip()
                if 'Sept' in date_str:
                    space_idx = 4
                else:
                    space_idx = 3

                if date_str[space_idx] != ' ':
                    date_str = date_str[:space_idx] + ' ' + date_str[space_idx:]
                print('checkpoint:', date_str)
                try:
                    date = datetime.datetime.strptime(date_str, "%b %d,%Y")
                except:
                    date = datetime.datetime.strptime(date_str, "%b %d, %Y")

                print('checkpoint:', date_str)

            else:
                # MM-DD-YYYY
                date = datetime.datetime.strptime(date_str, "%m-%d-%Y")
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
                date = datetime.datetime.strptime(date_str, "%Y/%m/%d")
            else:
                # MM-DD-YYYY
                date = datetime.datetime.strptime(date_str, "%m/%d/%Y")
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
    text = text.replace(' ', '')
    idx = text.find('MD:')
    text_nearby = text[idx: idx+80].replace(' ','')
    print(text_nearby)
    print(text.count('MD:'))

    idxs_dB = [i.start() for i in re.finditer('dB', text_nearby)]
    print(idxs_dB)
    if len(idxs_dB) == 2:
        # find the number
        md_value = float(find_dB_value(idxs_dB[0], text_nearby))
        psd_value = float(find_dB_value(idxs_dB[1], text_nearby))

        # didnt recongize the dot
        md_value = md_value if abs(md_value)>30 else md_value
        psd_value = psd_value if abs(psd_value)>30 else psd_value
        return md_value, psd_value
    else:
        return False, False


if __name__ == '__main__':
    test_dir = './test4/'
    reader = easyocr.Reader(['en'], gpu=False)

    ocr_result_dict = {
                0:{},
                1:{}
                } 

    # GUI design
    file_list_column = [
        [
            sg.Text(" Glaucoma Staging System ", size=(20, 3), font=("Helvetica", 20), justification='center')
        ],
        [
            sg.Text("Select Images    "),
            sg.In(size=(25, 1), enable_events=True, key="-Selections-"),
            sg.FilesBrowse(),
        ],
        [
            sg.Text("Folder to Save    "),
            sg.In(size=(25, 1), enable_events=True, key="-Target-"),
            sg.FolderBrowse(),
        ],
        [
            sg.Text("报告类别          "),
            sg.T("   "), sg.Radio('群组', "type", key="-type-"),
            sg.T("   "), sg.Radio('个人', "type", default=True),
        ],
        [
            sg.Text("群组/病人名        "),
            sg.In(size=(25, 1), enable_events=True, key="-PatientInfo-"),
        ],

        
        [
            sg.Button('Reset', size=(20, 1)),
            sg.Button('Confirm', size=(20, 1))
        ],
        [
            sg.Listbox(
                values=[], enable_events=True, size=(47, 20), key="-FILE LIST-"
            )
        ],
    ]
    image_viewer_column = [
        [sg.Text("Choose an image from list on left:")],
        [sg.Text(size=(40, 1), key="-TOUT-")],
        [sg.Image(key="-IMAGE-")],
    ]


    layout = [
        [
            sg.Column(file_list_column),
            sg.VSeperator(),
            sg.Column(image_viewer_column),
        ],
        [sg.Text("分析进度： ")],
        [sg.ProgressBar(100, orientation='h', size=(110, 20), key='progressbar')]

    ]

    window = sg.Window("Image Viewer", layout, size=(1100, 1000), finalize=True)

    fnames = []
    read_images = []
    while True:
        event, values = window.read()
        if event == "Exit" or event == sg.WIN_CLOSED:
            break

        # Folder name was filled in, make a list of files in the folder
        if event == "-Selections-":
            files_path_str = values["-Selections-"]
            print(files_path_str)
            files = files_path_str.split(';')
            if not fnames:
                fnames = [
                    f
                    for f in files
                    if os.path.isfile(f)
                    and f.lower().endswith((".png", ".jpg", 'tif', '.pdf'))
                ]
            else:
                fnames += [
                    f
                    for f in files
                    if os.path.isfile(f)
                    and f.lower().endswith((".png", ".jpg", 'tif', '.pdf')) and f not in fnames
                ]
            
            # convert pdfs into images, and save into folder
            for fname in fnames:
                if '.pdf' in fname:
                    images = convert_from_path(fname, poppler_path=r'C:\Program Files\poppler-0.68.0\bin')
                    raw_fname = copy.deepcopy(fname)
                    fname = fname.replace('.pdf', '.png')
                    for i in range(len(images)):
                        # Save pages as images in the pdf
                        images[i] = images[i].resize((int(images[i].width/3.7), int(images[i].height/3.7)))
                        images[i].save('./cache/' + fname.split('/')[-1], 'png')

                        read_images.append('./cache/' + fname.split('/')[-1])
                else:
                    temp_img = Image.open(fname)
                    temp_img = temp_img.resize((int(images[i].width/3.7), int(images[i].height/3.7)))
                    temp_img.save('./cache/' + fname.split('/')[-1], 'png')
                    read_images.append('./cache/' + fname.split('/')[-1])
            window["-FILE LIST-"].update(fnames)

        elif event == "-FILE LIST-":  # A file was chosen from the listbox
            try:
                filename_ = read_images[fnames.index(values["-FILE LIST-"][0])]
                window["-TOUT-"].update(filename_)
                window["-IMAGE-"].update(filename=filename_)
            except:
                pass
        elif event == "Reset":
            fnames = []
            read_images = []
            window["-Selections-"].update('')
            window["-Target-"].update('')
            window["-FILE LIST-"].update([])
            window["-PatientInfo-"].update('')
            window['progressbar'].UpdateBar(0)

        elif event == "Confirm":

            group_type_bool = values["-type-"]
            print('----------------', group_type_bool)
            if not fnames:
                sg.Popup('！！！No image included', keep_on_top=True)
                
            elif not values["-PatientInfo-"]:
                sg.Popup('！！！No patient Name/ID', keep_on_top=True)
            else:

                date_idx = datetime.datetime.now()
                idx = 0
                for full_path in [fname for fname in fnames]:
                    
                    idx += 1
                    imgname = full_path.split('/')[-1]
                    target_dir = values["-Target-"] if values["-Target-"] else './' 
                    image_dir = full_path.replace(imgname, '')
                    if 'jpg' in imgname or 'png' in imgname or 'pdf' in imgname:
                        # use Tessert
                        if 'pdf' not in imgname:
                            img = cv2.imread(image_dir + imgname)
                        else:
                            images = convert_from_path(image_dir + imgname, poppler_path=r'C:\Program Files\poppler-0.68.0\bin')
                            raw_imgname = copy.deepcopy(imgname)
                            imgname = imgname.replace('.pdf', '.png')
                            for i in range(len(images)):
                                # Save pages as images in the pdf
                                images[i].save(image_dir + imgname, 'png')
                            img = cv2.imread(image_dir + imgname)
                            os.remove(image_dir + imgname)

                        img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                        text = pytesseract.image_to_string(img)
                        print('=============', imgname, '================')
                        MD, PSD = extract_md_psd(text)

                        if not group_type_bool:
                            eye_side = extract_eye(text)
                            date = extract_date(text)
                        else:
                            # template assignment
                            eye_side = 0
                            date = date_idx.strftime("%Y-%m-%d")
                            date_idx = date_idx - datetime.timedelta(days=1)



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

                        # print('MD, PSD: ', MD, PSD)
                        # print('Eye: ', eye_side)
                        # print('Date: ', date)

                        if eye_side != -1:
                            ocr_result_dict[eye_side][date] = [MD, PSD]
                    window['progressbar'].UpdateBar((idx/len(fnames)+1)*100)

                if not group_type_bool:
                    to_save_path = target_dir + '/' + values["-PatientInfo-"] + '_Left' + '.png'   
                    try:            
                        generate_report(ocr_result_dict[0], to_save_path)
                    except:
                        pass
                    to_save_path = target_dir + '/' + values["-PatientInfo-"] + '_Right' + '.png'                
                    try:
                        generate_report(ocr_result_dict[1], to_save_path)
                    except:
                        pass
                else:
                    to_save_path = target_dir + '/' + values["-PatientInfo-"] + '_Group' + '.png'                
                    generate_report(ocr_result_dict[0], to_save_path, group_type_bool=True)


                # sg.Popup('Plot(s) generated!!!', keep_on_top=True)
                window.Finalize()


