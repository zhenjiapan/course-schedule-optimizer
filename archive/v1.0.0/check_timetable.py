"""Validate timetable grid boundaries, row spans, and conflict-free rendering."""
import sys
from datetime import date
from html.parser import HTMLParser

from query_courses import build_weekly_schedule

sys.path.insert(0, r'D:\CUHK-Shenzhen\Classes\AIE1901\Course selectionproject\Course Schedule Optimization')
import app as appmod   


class TableParser(HTMLParser):
    """Collect table cells and row spans for structural validation."""

    def __init__(self):
        super().__init__()
        self.rows = []          # [(row_index, [cells])]
        self.current = None
        self.in_body = False
        self.cell_text = None
        self.cells = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'tbody':
            self.in_body = True
        elif tag == 'tr' and self.in_body:
            self.current = []
        elif tag in ('td', 'th') and self.current is not None:
            self.cell_text = {'tag': tag, 'rowspan': int(a.get('rowspan', 1)),
                              'cls': a.get('class', ''), 'text': ''}
            self.current.append(self.cell_text)

    def handle_endtag(self, tag):
        if tag == 'tr' and self.current is not None:
            self.rows.append(self.current)
            self.current = None
        elif tag == 'tbody':
            self.in_body = False

    def handle_data(self, data):
        if self.cell_text is not None:
            self.cell_text['text'] += data


def check(selection, label):
    rows = build_weekly_schedule(selection)
    html = appmod.build_timetable_html(rows, date(2026, 10, 26))
    p = TableParser()
    p.feed(html)

    print(f'--- {label} ---')
    print(f'  Number of meetings(Card count) = {len(rows)}')


    carry = {}    
    grid = []
    for row in p.rows:
        line = [''] * 8
        col = 0
        new_carry = {}   
        for c in row:
            while col in carry:      
                line[col] = 'SPAN'
                col += 1
            if col >= 8:
                break
            if c['cls'] == 'tt-time':
                line[col] = 'TIME'
            elif c['cls'] == 'tt-class':
                line[col] = 'CLASS'
                for k in range(1, c['rowspan']):
                    if col + k < 8:
                        new_carry[col + k] = c['rowspan'] - k
            else:
                line[col] = 'EMPTY'
            col += 1
        
        for c2 in range(8):
            if line[c2] == '':
                line[c2] = 'SPAN' if c2 in carry else 'MISSING'
        grid.append(line)
        
        for k in list(carry):
            carry[k] -= 1
            if carry[k] <= 0:
                del carry[k]
        for k, v in new_carry.items():
            carry[k] = v

    ok = True
    for i, line in enumerate(grid):
        if 'MISSING' in line:
            print(f'  !! No. {i} row has unoccupied columns: {line}')
            ok = False
    n_class = sum(line.count('CLASS') for line in grid)
    if n_class != len(rows):
        print(f'  !! Card count {n_class} != Number of meetings {len(rows)}')
        ok = False
    n_span = sum(line.count('SPAN') for line in grid)
    print(f'  Row count = {len(grid)}, Card count = {n_class}(should={len(rows)}), Cells continued from earlier rows = {n_span}, '
          f'Each row 8 Column coverage check = {"OK" if ok else "FAIL"}')
    assert ok, 'HTML Structure validation failed'
    return html


sel1 = [('AIE1001', 'L01'), ('AIE1001', 'T01'), ('AIE1901', 'S01'), ('MAT1001', 'L02'),
        ('MAT1001', 'T03'), ('ENG1001', 'L01'), ('CHI1000', 'L02'), ('PED1101', 'L04')]
html1 = check(sel1, 'Scenario1: Multiple courses + LEC/TUT/SUP')


html2 = check([('MAT1001', 'L01')], 'Scenario2: Single course')


html3 = appmod.build_timetable_html([], date(2026, 10, 26))
assert 'No classes to display' in html3
print('--- Scenario3: Empty timetable OK ---')


standalone = (
    '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
    '<title>Timetable preview</title>'
    '<style>body{font-family:"Segoe UI","Microsoft YaHei",sans-serif;background:#fff;padding:16px;}'
    'h2{color:#1F3864;font-size:18px;}</style></head><body>'
    '<h2>Intelligent Course Planner — Weekly timetable (Time × Weekday)</h2>' + html1 + '</body></html>'
)
out = r'D:\CUHK-Shenzhen\Classes\AIE1901\Course selectionproject\Course Schedule Optimization\_timetable_preview.html'
with open(out, 'w', encoding='utf-8') as f:
    f.write(standalone)
print('\nPreview file generated:', out)
print('ALL HTML CHECKS PASSED')
