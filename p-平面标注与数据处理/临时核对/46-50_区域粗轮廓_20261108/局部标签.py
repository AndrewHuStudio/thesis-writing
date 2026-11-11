"""仅对当前批次极窄真实小间提供可缩放的完整内部标签。"""
from shapely.geometry import box
import annotation_tools as a
original=a.place_label

def compact_label(poly,s):
    try:return original(poly,s)
    except ValueError:
        pending=s['type']=='unknown' or a.PENDING.search(s['name'])
        name='名称未确认' if pending else s['name']
        category='〔'+a.TYPE_NAMES.get(s['type'],s['type'])+'〕'
        x0,y0,x1,y1=poly.bounds
        for font in (4.5,4,3.5,3,2.5,2):
            for width in (min(120,x1-x0-2),min(70,x1-x0-2),min(40,x1-x0-2)):
                if width<8:continue
                lines=a.wrap(s['id']+' '+name,font,width-4)
                if not pending:lines+=a.wrap(category,font,width-4)
                w=max(a.visual_width(line,font) for line in lines)+4
                h=len(lines)*(font+2)+5
                for iy in range(1,24):
                    for ix in range(1,24):
                        cx=x0+(x1-x0)*ix/24;cy=y0+(y1-y0)*iy/24
                        if poly.covers(box(cx-w/2,cy-h/2,cx+w/2,cy+h/2)):
                            return cx-w/2,cy-h/2,w,h,font,lines
        raise

a.place_label=compact_label
