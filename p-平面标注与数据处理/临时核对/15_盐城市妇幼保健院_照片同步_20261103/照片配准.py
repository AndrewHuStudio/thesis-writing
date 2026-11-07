from pathlib import Path
import cv2,json,numpy as np
R=Path(__file__).resolve().parent
P=R.parent.parent/'标注试样/15_盐城市妇幼保健院'
original=cv2.imread(str(P/'15_盐城市妇幼保健院_原图.jpg'))
gray=cv2.cvtColor(original,cv2.COLOR_BGR2GRAY)
sift=cv2.SIFT_create(nfeatures=18000,contrastThreshold=.02)
k0,d0=sift.detectAndCompute(gray,None)
matcher=cv2.BFMatcher()
records=[]
for f in sorted((R/'用户补充照片').glob('照片*.jpg')):
    im=cv2.imread(str(f));g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    k1,d1=sift.detectAndCompute(g,None)
    pairs=matcher.knnMatch(d0,d1,k=2)
    matches=[a for a,b in pairs if a.distance<.68*b.distance]
    a=np.float32([k0[m.queryIdx].pt for m in matches])
    b=np.float32([k1[m.trainIdx].pt for m in matches])
    H,mask=cv2.findHomography(a,b,cv2.USAC_MAGSAC,4.0,maxIters=20000)
    if H is None:
        records.append({'photo':f.name,'error':'no homography'});continue
    good=mask.ravel().astype(bool)
    coords=a[good]
    rec={'photo':f.name,'matches':len(matches),'inliers':int(good.sum()),'source_bounds':[coords.min(0).tolist(),coords.max(0).tolist()],'H':H.tolist()}
    records.append(rec)
    # A diagnostic contact sheet displays actual feature correspondences.
    debug=cv2.drawMatches(original,k0,im,k1,[m for m,ok in zip(matches,good) if ok][::max(1,int(good.sum()/30))],None,flags=2)
    debug=cv2.resize(debug,(1800,int(debug.shape[0]*1800/debug.shape[1])))
    cv2.imwrite(str(R/(f.stem+'_配准检查.jpg')),debug)
    print(f.name,'matches',len(matches),'inliers',int(good.sum()),'bounds',np.round(coords.min(0)).tolist(),np.round(coords.max(0)).tolist(),flush=True)
(R/'照片配准结果.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
