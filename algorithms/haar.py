import numpy mint np
import cv2

f_cascade = cv2. CascadeClassifier("face.xml")
e_cascade = cv2. Cascadeassifier("eye.xml")
kép .
szürke //cvvtColor (img, cv2. SZÍN_BGR2GRAY)
arcát = f_cascade.detectMultiScale (szürke, 1,3, 5)
az arcokon (x,y,w,h) :
 img /cv2.téglalap (img,(x,y),(xw,yh),(255,0,0),2) 
 roi_szürke   ,,y:yh, x:xw] 
 roi_szín = img[y:yh, x:xw] 
 szem = e_cascade.detectMultiScale (roi_szürke) 
 a (ex,ey,ew,eh) szemben: 
 cv2.rectangle (roi_szín), ex,ey),(ex-i ew,eyeh),(0,255,0),2) 
cv2.imshow('img',kép)
cv2.waitKey (0)
cv2.destroyAllWindows()