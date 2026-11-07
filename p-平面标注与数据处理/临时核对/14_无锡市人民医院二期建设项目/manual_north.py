def manual_routes(M,G):
 R={}
 def src(n):return [v*G for v in M[n-1]['anchor']]
 def end(n):return [v*G for v in M[n-1]['end']]
 def put(n,pts):
  points=[src(n)]+pts+[end(n)]
  R[n-1]=points
 loops=[610,650,656,660,662,664,666,668,680]
 turns=[260,270,280,300,380,420,500,580,660]
 for i in range(9):
  x,y=src(i+1);mx=2064-i*4;lx=1800-i*10;ly=loops[i];ty=turns[i]
  put(i+1,[[x,ly],[mx,ly],[mx,ty],[lx,ty],[lx,end(i+1)[1]]])
 put(10,[[2608,src(10)[1]],[2608,270],[3600,270],[3600,end(10)[1]]])
 put(11,[[2614,src(11)[1]],[2614,280],[3610,280],[3610,end(11)[1]]])
 for n,lo,lx in [(12,800,1710),(13,810,1700),(14,850,1690),(15,920,1680)]:
  x,y=src(n);put(n,[[x,lo],[lx,lo],[lx,end(n)[1]]])
 for n,esc,mx,ty,rx in [(16,720,2720,410,3650),(17,725,2726,450,3660),(18,730,2732,530,3670),(19,735,2738,610,3680),(20,740,2744,680,3690),(21,745,2750,755,3700)]:
  x,y=src(n);pre=[]
  if n==18:pre=[[2580,y]];x=2580
  put(n,pre+[[x,esc],[mx,esc],[mx,ty],[rx,ty],[rx,end(n)[1]]])
 # Separate upper and lower support clusters around the examination row.
 for n,esc,mx,ty,rx in [(33,1760,3450,1330,3800),(37,1970,3550,1680,3840),(38,1980,3560,1760,3850),(39,1990,3570,1840,3860),(40,2000,3580,1920,3870),(41,2060,3590,2000,3880),(42,2070,3600,2080,3890),(43,2140,3610,2160,3900)]:
  x,y=src(n)
  put(n,[[x,esc],[mx,esc],[mx,ty],[rx,ty],[rx,end(n)[1]]])
 # Examination row uses the gap above the lower support leaders.
 for n,esc,mx,ty,rx in [(34,1780,3470,1420,3740),(35,1784,3480,1500,3750),(36,1788,3490,1580,3760)]:
  x,y=src(n);put(n,[[x,esc],[mx,esc],[mx,ty],[rx,ty],[rx,end(n)[1]]])
 # Northern staff rooms.
 for n,esc,mx,ty,rx in [(22,860,3650,830,3740),(23,870,3660,930,3750),(24,1010,3670,1030,3760)]:
  x,y=src(n);put(n,[[x,esc],[mx,esc],[mx,ty],[rx,ty],[rx,end(n)[1]]])
 # Infusion review points, above laboratory points.
 x,y=src(25);put(25,[[x,1100],[1500,1100],[1500,end(25)[1]]])
 for n,lo,mx,ty,lx in [(26,None,2080,1125,1490),(27,None,2070,1210,1480),(28,1720,2060,1290,1470)]:
  x,y=src(n);pre=[[mx,y]] if lo is None else [[x,lo],[mx,lo]]
  put(n,pre+[[mx,ty],[lx,ty],[lx,end(n)[1]]])
 # Laboratory row moves down in a single ordered fan.
 for n,lo,mx,ty,lx in [(29,1820,2048,1610,1450),(30,1918,2040,1670,1440),(31,2010,2032,1750,1430),(32,2030,2024,1830,1420)]:
  x,y=src(n);put(n,[[x,lo],[mx,lo],[mx,ty],[lx,ty],[lx,end(n)[1]]])
 # Southwest cluster, with separate bands for each neighboring room group.
 x,y=src(44);put(44,[[x,2050],[800,2050],[800,end(44)[1]]])
 for n,lo,mx,ty,lx in [(45,2120,940,2060,790),(46,2200,930,2100,780),(47,2220,920,2170,770),(48,2290,910,2250,760)]:
  x,y=src(n);put(n,[[x,lo],[mx,lo],[mx,ty],[lx,ty],[lx,end(n)[1]]])
 x,y=src(49);put(49,[[1812,y],[1812,2310],[1050,2310],[1050,2340],[670,2340],[670,end(49)[1]]])
 x,y=src(50);put(50,[[1840,y],[1840,2312],[1054,2312],[1054,2410],[660,2410],[660,end(50)[1]]])
 x,y=src(51);put(51,[[x,2315],[1060,2315],[1060,2500],[680,2500],[680,end(51)[1]]])
 x,y=src(52);put(52,[[x,2420],[1080,2420],[1080,2580],[690,2580],[690,end(52)[1]]])
 x,y=src(53);put(53,[[x,2640],[700,2640],[700,end(53)[1]]])
 x,y=src(54);put(54,[[x,2300],[3950,2300],[3950,end(54)[1]]])
 x,y=src(55);put(55,[[x,2360],[3940,2360],[3940,2460],[3960,2460],[3960,end(55)[1]]])
 return R
