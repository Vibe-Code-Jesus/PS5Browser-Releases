#!/usr/bin/env python3
"""Binary release automation only; no PS5Browser application source is included."""
from pathlib import Path
import argparse,hashlib,json,os,re,stat,subprocess,tempfile,time,zipfile
from urllib.parse import quote
REPOSITORY='Vibe-Code-Jesus/PS5Browser-Releases'
TITLE='PPSA99257'
def sha(data):return hashlib.sha256(data).hexdigest()
def validate(root):
    doc=json.loads((root/'release.json').read_text())
    v=doc['version'];assert re.fullmatch(r'\d{2}\.\d{3}\.\d{3}',v),'Invalid native version'
    name=f'PS5Browser-Native-{v}-Preview.zip'
    assert doc['repository']==REPOSITORY and doc['title_id']==TITLE
    assert doc['tag']=='native-v'+v and doc['asset']==name
    asset=root/name;data=asset.read_bytes()
    assert 1024<len(data)<=134217728 and len(data)==doc['size'] and sha(data)==doc['sha256'],'ZIP integrity mismatch'
    allowed={'eboot.bin','sce_sys/param.json','sce_sys/icon0.png','sce_module/libc.prx','assets/ps5browser.elf','assets/native-recovery.elf','assets/build-info.json','PREVIEW.txt','THIRD-PARTY-NOTICES.txt'}
    licenses={'miniz-LICENSE','FFmpeg-n7.0.1-COPYING.GPLv2','FFmpeg-n7.0.1-LICENSE.md','dav1d-1.5.3-COPYING','mbedtls-LICENSE','native-boilerplate-GPL-3.0.txt','openlibm-0.8.6-LICENSE.md','qrcode-LICENSE.txt','unrar-license.txt','x264-stable-COPYING','zlib-LICENSE'}
    with zipfile.ZipFile(asset) as z:
        assert 8<=len(z.infolist())<=40
        names=set();total=0
        for i in z.infolist():
            assert i.filename.startswith(TITLE+'/') and not i.is_dir()
            rel=i.filename[len(TITLE)+1:]
            assert rel not in names and '\\' not in rel and '..' not in rel.split('/')
            assert rel in allowed or rel in {'licenses/'+n for n in licenses},'Unexpected file in release: '+rel
            assert stat.S_IFMT(i.external_attr>>16) in (0,stat.S_IFREG),'Non-file entry'
            names.add(rel);total+=i.file_size
        assert total<=268435456 and allowed<=names
        assert z.testzip() is None
        p=json.loads(z.read(TITLE+'/sce_sys/param.json'));m=json.loads(z.read(TITLE+'/assets/build-info.json'))
        for filename in ('param.json','icon0.png'):
            assert (root/'sce_sys'/filename).read_bytes()==z.read(TITLE+'/sce_sys/'+filename),'Public listing metadata differs from package: '+filename
        assert p['titleId']==TITLE and p['contentVersion']==v and p['contentId']=='UP9000-PPSA99257_00-PS5BROWSER000001'
        assert m['title_id']==TITLE and m['content_version']==v and m['release_repository']==REPOSITORY and m['core_version']==doc['core_version']
        helper=z.read(TITLE+'/assets/native-recovery.elf')
        assert len(helper)==m['helper_size'] and sha(helper)==m['helper_sha256'] and helper.startswith(b'\x7fELF\2\1\1')
        assert m['native_self_update_ready'] is True
        core=z.read(TITLE+'/assets/ps5browser.elf')
        assert len(core)==m['core_size'] and sha(core)==m['core_sha256'] and core.startswith(b'\x7fELF\2\1\1')
        assert z.read(TITLE+'/eboot.bin').startswith(bytes.fromhex('4f153d1d'))
        assert sha(z.read(TITLE+'/sce_module/libc.prx'))=='e6ff45d16adf687855cc3b33b0c8a4132b6504360b221e0a34c7e99fb3ba0036'
    assert (root/'SHA256SUMS.txt').read_text()==doc['sha256']+'  '+name+'\n'
    return doc,asset

def gh(*args):
    p=subprocess.run(['gh',*args],capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr.strip())
    return p.stdout

def api(path):return json.loads(gh('api',path))
def write_api(path,method,body):
    with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
        json.dump(body,f);f.flush()
        return json.loads(gh('api','--method',method,path,'--input',f.name))
def find_release(tag):
    # Drafts may not yet have a Git tag and the releases/tags endpoint can 404.
    # Listing releases with this repository's write token includes its drafts.
    pages=json.loads(gh('api','--paginate','--slurp','repos/'+REPOSITORY+'/releases?per_page=100'))
    matches=[r for page in pages for r in page if r['tag_name']==tag]
    assert len(matches)<=1,'Duplicate releases for native version'
    return matches[0] if matches else None
def publish(root,doc,asset):
    # GITHUB_TOKEN is scoped to this public release repository. No source token.
    assert os.environ.get('GITHUB_REPOSITORY',REPOSITORY)==REPOSITORY
    repo=api('repos/'+REPOSITORY)
    assert not repo['private'],'Release repository must be public'
    files=[asset,root/'SHA256SUMS.txt']
    expected={p.name:('sha256:'+sha(p.read_bytes()),p.stat().st_size) for p in files}
    tag=doc['tag'];release=find_release(tag)
    if release is None:
        body={'tag_name':tag,'name':'PS5 Browser native '+doc['version'],
              'body':(root/'RELEASE-NOTES.txt').read_text(),'draft':True,'prerelease':False}
        if os.environ.get('GITHUB_SHA'):body['target_commitish']=os.environ['GITHUB_SHA']
        # Use the creation response ID; release listings can lag behind writes.
        release=write_api('repos/'+REPOSITORY+'/releases','POST',body)
    endpoint='repos/'+REPOSITORY+'/releases/'+str(release['id'])
    if release['draft']:
        existing={a['name']:a for a in release['assets']}
        assert not(set(existing)-set(expected)),'Unexpected draft assets'
        for p in files:
            if p.name in existing:
                a=existing[p.name];assert (a.get('digest'),a['size'])==expected[p.name],'Existing draft differs; use a new version'
            else:
                uploaded=json.loads(gh('api','--method','POST',
                    'https://uploads.github.com/repos/'+REPOSITORY+'/releases/'+str(release['id'])+'/assets?name='+quote(p.name),
                    '-H','Content-Type: application/octet-stream','--input',str(p)))
                assert (uploaded.get('digest'),uploaded['size'])==expected[p.name],'Uploaded asset differs; draft retained'
        release=api(endpoint)
    actual={a['name']:(a.get('digest'),a['size']) for a in release['assets']}
    assert actual==expected,'GitHub asset digest/size verification failed; draft retained'
    if release['draft']:write_api(endpoint,'PATCH',{'draft':False,'prerelease':False,'make_latest':'true'})
    latest={}
    for attempt in range(6):
        latest=api('repos/'+REPOSITORY+'/releases/latest')
        if latest['tag_name']==tag:break
        time.sleep(1)
    assert latest['tag_name']==tag,'Published release is not latest'
    print('Published and verified '+latest['html_url'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--publish',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parent;doc,asset=validate(root)
    print(json.dumps({'version':doc['version'],'asset':asset.name,'sha256':doc['sha256'],'validated':True}))
    if a.publish:publish(root,doc,asset)
