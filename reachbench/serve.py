"""Local-only fresh Python runs and static replay UI. Binds localhost, sequential execution."""
from http.server import SimpleHTTPRequestHandler,HTTPServer
from pathlib import Path
import json, argparse
from .sim import scene,rollout,METHODS
ROOT=Path(__file__).resolve().parents[1]/'dist'
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def send_json(self,obj,status=200):
        data=json.dumps(obj).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path=='/api/health':return self.send_json({'engine':'pybullet','mode':'fresh-local'})
        super().do_GET()
    def do_POST(self):
        if self.path!='/api/run':return self.send_json({'error':'not found'},404)
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<4096:raise ValueError('invalid body size')
            cfg=json.loads(self.rfile.read(n));seed=int(cfg.get('seed',42));cond=cfg.get('condition','nominal')
            if not 0<=seed<1000000 or cond not in ['nominal','dim','clutter','occluded','calibration']:raise ValueError('invalid scene')
            s=scene(seed,cond)
            if 'target' in cfg:
                x,y=map(float,cfg['target'])
                if not -.1<=x<=.4 or not .15<=y<=.55:raise ValueError('target outside workspace')
                s.target=[x,y]
            results=[]
            for m in ['baseline','improved']:
                uid=f'local-{m}';r=rollout(s,m,ROOT/'data'/'frames'/uid);r['id']=uid;results.append(r)
            self.send_json({'episodes':results})
        except (ValueError,TypeError,KeyError) as e:self.send_json({'error':str(e)},400)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8000);a=ap.parse_args()
    print(f'ReachBench: http://127.0.0.1:{a.port}',flush=True);HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
