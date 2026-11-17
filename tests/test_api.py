"""Local API integration test; ephemeral test listener, not a browser preview."""
import json,threading,urllib.request,urllib.error
from http.server import HTTPServer
from reachbench.serve import Handler

def test_fresh_local_api_and_static_data():
    server=HTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        assert json.load(urllib.request.urlopen(base+'/api/health'))['mode']=='fresh-local'
        data=json.load(urllib.request.urlopen(base+'/data/summary.json'));assert len(data['episodes'])==400
        req=urllib.request.Request(base+'/api/run',data=json.dumps({'seed':42,'condition':'nominal','target':[.24,.35]}).encode(),headers={'Content-Type':'application/json'})
        result=json.load(urllib.request.urlopen(req));assert len(result['episodes'])==2
        for r in result['episodes']:
            assert r['scene']['target']==[.24,.35] and r['frames']==len(r['trace'])
        req=urllib.request.Request(base+'/api/run',data=json.dumps({'target':[99,99]}).encode(),headers={'Content-Type':'application/json'})
        try:urllib.request.urlopen(req);assert False,'invalid coordinate accepted'
        except urllib.error.HTTPError as e:assert e.code==400
    finally:server.shutdown();server.server_close();thread.join(timeout=2)
