import json,sys
def r(o):
    if isinstance(o,float): return round(o,5)
    if isinstance(o,list): return [r(x) for x in o]
    if isinstance(o,dict): return {k:r(v) for k,v in o.items()}
    return o
src,name,out=sys.argv[1:4]
d=r(json.load(open(src)))
open(out,'w').write('window.D=window.D||{};D["%s"]='%name+json.dumps(d,ensure_ascii=False,separators=(',',':'))+';')
