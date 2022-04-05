import cv2 
from paddleocr import PaddleOCR


paddleocr=PaddleOCR(enable_mkldnn=True,use_tensorrt=True, use_angle_cls = True,use_gpu= False) 

img = cv2.imread(r'D:\Github\VisualFieldOCR\test\00-1.jpg')
img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

recong_texts = paddleocr.ocr(img_gray, cls=True)
text = ''
for object in recong_texts:
    text += ' ' + str(object[1][0]) + ' '
print(text)
idx = text.find('出生日期')
print(text[idx:idx+4])