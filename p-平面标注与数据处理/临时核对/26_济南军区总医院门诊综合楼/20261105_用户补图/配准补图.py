from pathlib import Path
import cv2, numpy as np, json
W=Path(__file__).parent
P=W.parents[2]/'标注试样/26_济南军区总医院门诊综合楼'
original=cv2.imread(str(P/'26_济南军区总医院门诊综合楼_原图.jpg'))
sift=cv2.SIFT_create(nfeatures=14000)
ka,da=sift.detectAndCompute(cv2.cvtColor(original,cv2.COLOR_BGR2GRAY),None)
result={}
for i in range(1,7):
    photo=cv2.imread(str(W/f'补图{i:02}_正向.jpg'))
    kb,db=sift.detectAndCompute(cv2.cvtColor(photo,cv2.COLOR_BGR2GRAY),None)
    matches=cv2.BFMatcher().knnMatch(da,db,k=2)
    good=[m for m,n in matches if m.distance<.67*n.distance]
    a=np.float32([ka[m.queryIdx].pt for m in good]);b=np.float32([kb[m.trainIdx].pt for m in good])
    h,mask=cv2.findHomography(a,b,cv2.RANSAC,5)
    inliers=int(mask.sum());result[str(i)]=dict(h=h.tolist(),matches=len(good),inliers=inliers)
    transform=np.diag([2.,2.,1.])@np.linalg.inv(h)
    registered=cv2.warpPerspective(photo,transform,(4888,6520),borderValue=(245,245,245))
    cv2.imwrite(str(W/f'补图{i:02}_对应原图坐标.jpg'),registered)
    print(i,len(good),inliers)
(W/'照片配准.json').write_text(json.dumps(result,indent=2)+'\n')
