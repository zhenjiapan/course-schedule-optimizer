"""Date-aware timetable with exact time boundaries; never move a class."""
from datetime import timedelta
from html import escape

DAYS=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
def hhmm(n):return f'{n//60:02d}:{n%60:02d}'

def weekly_rows(cat,selections,monday):
    rows=[]
    for code,sec in selections:
        s=next(s for s in cat.sections[code] if s.code==sec)
        for m in s.meetings:
            d=monday+timedelta(days=m.weekday-1)
            if not m.first<=d<=m.last:continue
            rows.append({'Date':d.isoformat(),'Weekday':DAYS[m.weekday-1],'Course code':code,'Course name':cat.courses[code]['name'],'Section':sec,'Type':s.component,'Start':hhmm(m.start),'End':hhmm(m.end),'Instructor':' / '.join(m.teachers) or 'TBA','Room':' / '.join(m.rooms),'weekday':m.weekday,'start':m.start,'end':m.end})
    return sorted(rows,key=lambda r:(r['weekday'],r['start']))


def render(rows):
    if not rows:return '<p>No classes this week (Filtered by teaching start and end dates).</p>'
    palette=['#e8f1fc','#edf4e9','#fff2df','#f0ebfa','#e5f3f1','#fbecef']
    colors={c:palette[sum(map(ord,c))%len(palette)] for c in {r['Course code'] for r in rows}}
    bounds=sorted({r[k] for r in rows for k in ('start','end')})
    html=['<style>.schedule{border-collapse:collapse;width:100%;table-layout:fixed;min-width:850px}.schedule th,.schedule td{border:1px solid #dce5eb;padding:10px;vertical-align:top;font-size:12px;line-height:1.6}.schedule th{background:#f3f6fa;color:#203347}.schedule .lesson{background:#eaf3ee;color:#173d30}.schedule .time{width:95px}</style><div style="overflow-x:auto"><table class="schedule"><thead><tr><th class="time">Time</th>']
    html += [f'<th>{d}</th>' for d in DAYS]+['</tr></thead><tbody>']
    for i,t in enumerate(bounds[:-1]):
        html.append(f'<tr><td>{hhmm(t)}–{hhmm(bounds[i+1])}</td>')
        for wd in range(1,8):
            matches=[r for r in rows if r['weekday']==wd and r['start']==t]
            if matches:
                r=matches[0];span=bounds.index(r['end'])-i
                text='<br>'.join(escape(str(r[k])) for k in ('Course code','Section','Type'))
                text+=f"<br>{r['Start']}–{r['End']}<br>"+escape(r['Instructor'])+'<br>'+escape(r['Room'])
                html.append(f'<td class="lesson" style="background:{colors[r["Course code"]]}" rowspan="{span}">{text}</td>')
            elif not any(r['weekday']==wd and r['start']<t<r['end'] for r in rows):html.append('<td></td>')
        html.append('</tr>')
    return ''.join(html)+ '</tbody></table></div>'
