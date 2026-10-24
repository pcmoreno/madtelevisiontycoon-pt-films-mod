"""Rebuild the handoff page's DATA genres, genre tables and counts from data/genre_review.csv + data/data_overrides.json.
Usage: python3 tools/apply_genres.py [page.html]   (default: data/pacote-portugues.html). Also rewrites data/films.json."""
import sys,re,json,csv,collections
import os
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
page=sys.argv[1] if len(sys.argv)>1 else os.path.join(root,'data','pacote-portugues.html')
proj=os.path.join(root,'data')
s=open(page,encoding='utf-8').read()
rows={r['title']:r for r in csv.DictReader(open(proj+'/genre_review.csv',encoding='utf-8-sig'))}
ov={k:v for k,v in json.load(open(proj+'/data_overrides.json')).items() if not k.startswith('_')}
m=re.search(r'const DATA = (\[.*?\]);\n',s); data=json.loads(m.group(1))
OLD={r['title']:r['old_genre'] for r in rows.values()}
for d in data:
    r=rows[d['pt']]
    d['genre']=r['genre']; d['gcode']=int(r['genre_code'])
    d['subgenre']=r['subgenre'] or None; d['sgcode']=int(r['subgenre_code']) if r['subgenre_code'] else None
    d['src']['genre']='owner' if r['confidence']=='confirmed' else 'review'
    # Chance is a rarity in vanilla: the higher the Potential, the lower the Chance
    d['chance']=next((v for lo,v in ((80,1.0),(70,3.0),(60,5.0),(50,8.0)) if d['pot']>=lo),15.0)
    if d['pt'] in ov:
        o=ov[d['pt']]
        for k,v in o.items():
            if k=='src': d['src'].update(v)
            elif k!='why': d[k]=v
s=s[:m.start(1)]+json.dumps(data,ensure_ascii=False,separators=(',',':'))+s[m.end(1):]
main=collections.Counter(d['genre'] for d in data); sub=collections.Counter(d['subgenre'] for d in data if d['subgenre'])
owner=sum(d['src']['genre']=='owner' for d in data); nsub=sum(1 for d in data if d['subgenre'])
FOLD={'Action':'ACTION','Drama':'DRAMA','Science Fiction':'SCIFI','Romantic':'ROMANTIC','Fantasy':'FANTASY','Crime':'CRIME','Thriller':'THRILLER','Horror':'HORROR','Mystery':'MYSTERY','Adventure':'ADVENTURE','Family':'FAMILY','Documentary':'DOCU','Antiwar':'ANTIWAR','Western':'WESTERN','Comedy':'COMEDY','Cartoon':'CARTOON','Erotic':'EROTIC','Historical':'HISTORICAL'}
CODE={'Action':0,'Drama':1,'Science Fiction':2,'Romantic':3,'Fantasy':4,'Crime':5,'Thriller':6,'Horror':7,'Mystery':8,'Adventure':9,'Family':10,'Documentary':11,'Antiwar':14,'Western':15,'Comedy':16,'Cartoon':27,'Erotic':28,'Historical':29}
IMG={'ACTION':86,'DRAMA':78,'SCIFI':102,'ROMANTIC':16,'FANTASY':23,'CRIME':25,'THRILLER':40,'HORROR':44,'MYSTERY':11,'ADVENTURE':45,'FAMILY':81,'DOCU':34,'ANTIWAR':13,'WESTERN':15,'COMEDY':73,'CARTOON':29,'EROTIC':12,'HISTORICAL':19}
lab=lambda g:'Sci-fi' if g=='Science Fiction' else g
# genre table rows
trs='\n'.join(f'<tr><td>{lab(g)}</td><td class="num">{c}</td><td><code>{FOLD[g]}</code></td><td class="num">{main.get(g) or "–"}</td><td class="num">{sub.get(g) or "–"}</td><td class="num">{IMG[FOLD[g]]}</td></tr>' for g,c in sorted(CODE.items(),key=lambda x:x[1]))
s=re.sub(r'(<tr><th>Genre</th><th>Code</th><th>Image folder</th><th>Main</th><th>Sub</th><th>Vanilla images</th></tr>\n).*?(\n</table>)',lambda mm:mm.group(1)+trs+mm.group(2),s,flags=re.S)
s=re.sub(r'so the final call is editorial\. \d+ films were checked one by one',f'so the final call is editorial. {owner} films were checked one by one',s)
s=re.sub(r'\(<code>review</code>\)\. \d+ films carry a subgenre\.',f'(<code>review</code>). {nsub} films carry a subgenre.',s)
# change table
ch=''
for d in data:
    old=OLD[d['pt']]
    if old==d['genre'] or (old=='Romance' and d['genre']=='Romantic'): continue
    now=lab(d['genre'])+(' / '+lab(d['subgenre']) if d['subgenre'] else '')
    ch+=f"<tr><td><em>{d['pt']}</em> ({d['year']})</td><td>{old}</td><td>{now}</td><td>{d['src']['genre']}</td></tr>\n"
s=re.sub(r'(<tr><th>Film</th><th>Was</th><th>Now</th><th>Checked</th></tr>\n).*?(</table>)',lambda mm:mm.group(1)+ch+mm.group(2),s,flags=re.S)
s=re.sub(r'<td>\d+ checked one by one with the mod\'s owner · \d+ reviewed proposals</td>',f"<td>{owner} checked one by one with the mod's owner · {80-owner} reviewed proposals</td>",s)
open(page,'w',encoding='utf-8').write(s)
print('owner',owner,'sub',nsub,'changes',ch.count('<tr>'))
print(main.most_common())
json.dump(data,open(os.path.join(proj,'films.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
