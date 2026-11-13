"""UI regressions: a single preview, persistent manual edits and invalidation."""
import sys
from pathlib import Path
from datetime import timedelta
p=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(p))
from streamlit.testing.v1 import AppTest
at=AppTest.from_file(str(p/'app.py'),default_timeout=30).run()
assert not at.exception
assert at.button(key='generate').disabled
at.multiselect(key='courses_2026-27 Term 1').set_value(['AIE1001','AIE1901','MAT1001','ENG1001','CHI1000','PED1113']).run()
at.selectbox(key='early_mode').set_value('Avoid where possible').run()
at.button(key='generate').click().run()
assert not at.exception,at.exception
assert any('Independent validation passed' in s.value for s in at.success),[e.value for e in at.error]
assert len(at.dataframe)==2  # One editable time grid plus one timetable detail table.
at.button(key='load_manual').click().run()
assert at.toggle(key='editing').value
assert any('Independent validation passed' in s.value for s in at.success)
week=at.selectbox(key='week').value
at.selectbox(key='week').set_value(week-timedelta(days=7)).run()
assert not at.exception and len(at.dataframe)==2
assert any('Independent validation passed' in s.value for s in at.success)
manual=next(x for x in at.selectbox if x.key and x.key.startswith('manual_'))
original=manual.value
manual.set_value('— Not selected —').run()
assert len(at.error)>0 and len(at.dataframe)==1
at.selectbox(key=manual.key).set_value(original).run()
assert any('Independent validation passed' in s.value for s in at.success)
at.toggle(key='editing').set_value(False).run()
assert len(at.dataframe)==2
at.radio(key='solution').set_value(1).run()
at.button(key='load_manual').click().run()
assert not at.exception and len(at.dataframe)==2
at.multiselect(key='banned_days').set_value([1,2,3,4,5,6,7]).run()
assert any('Regenerate' in s.value for s in at.info)
at.button(key='generate').click().run()
assert not at.exception and len(at.error)>0
at.multiselect(key='courses_2026-27 Term 1').set_value(['MAT1001']).run()
assert at.button(key='generate').disabled
assert any('credits' in s.value.lower() for s in at.warning)
at.selectbox(key='semester').set_value('2026-27 Term 2').run()
assert not at.exception
term2_codes = at.multiselect(key='courses_2026-27 Term 2').options
assert all(any(option.startswith(code + ' · ') for option in term2_codes)
           for code in ('MAT1002', 'STA2001', 'ENG1002', 'PED1214'))
assert not any(option.startswith('AIE1901 · ') for option in term2_codes)
print('PASS: generate, one preview, manual persistence, missing component, switch solution, stale, infeasible, credits')
