import hashlib, json, os, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
entries = {}
for p in sorted(root.rglob('*')):
    if p.is_symlink():
        value = ['link', os.readlink(p)]
    elif p.is_dir():
        value = ['directory']
    elif p.is_file():
        value = ['file', hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()]
    else:
        value = ['special', p.lstat().st_mode]
    entries[str(p.relative_to(root))] = value
status = subprocess.check_output(['git','--no-optional-locks','-C',str(root),'status','--porcelain=v1','--branch','-uall']).decode()
print(json.dumps({'entries':entries,'git_status':status},sort_keys=True,indent=2))
