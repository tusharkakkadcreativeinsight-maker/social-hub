import os, sqlite3, json, hashlib
from pathlib import Path
root=Path('SocialHub')
candidates=[Path('socialhub.db'), root/'socialhub.db', root/'backups'/'pre_fullstack_fix'/'socialhub.db', root/'backups'/'SocialHub_backup_audit_20260710_153627'/'socialhub.db', Path('SocialHub_backup_before_restore_20260703_165046')/'socialhub.db', root/'backend'/'test_socialhub.db']
important=['users','posts','reels','stories','notifications','chats','messages','followers','comments','marketplace_products','reports','alembic_version']
rows=[]
for p in candidates:
    if not p.exists():
        continue
    info={'path':str(p),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.stat().st_size else None}
    if p.stat().st_size==0:
        info.update({'valid':False,'reason':'zero-byte database skipped'})
        rows.append(info); continue
    uri=f"file:{p.resolve().as_posix()}?mode=ro"
    try:
        con=sqlite3.connect(uri, uri=True)
        cur=con.cursor()
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        info['table_count']=cur.fetchone()[0]
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables={r[0] for r in cur.fetchall()}
        info['counts']={}
        for t in important:
            if t in tables:
                try:
                    cur.execute(f'SELECT count(*) FROM "{t}"')
                    info['counts'][t]=cur.fetchone()[0]
                except Exception as e:
                    info['counts'][t]=f'ERR:{e}'
        if 'alembic_version' in tables:
            try:
                cur.execute('SELECT version_num FROM alembic_version')
                info['alembic_revision']=[r[0] for r in cur.fetchall()]
            except Exception as e: info['alembic_revision']=f'ERR:{e}'
        cur.execute('PRAGMA integrity_check')
        info['integrity_check']=cur.fetchall()
        cur.execute('PRAGMA foreign_key_check')
        fk=cur.fetchall(); info['foreign_key_issues']=len(fk); info['foreign_key_sample']=fk[:5]
        info['valid']=True
        con.close()
    except Exception as e:
        info.update({'valid':False,'reason':repr(e)})
    rows.append(info)
print(json.dumps(rows, indent=2, default=str))
