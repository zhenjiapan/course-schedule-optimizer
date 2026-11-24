import unittest,itertools,random
from datetime import date
from app.optimization.model import Catalog,Meeting,Section,Preferences
from app.optimization.optimizer import solve,scoring,make_groups,overlap
from app.optimization.checker import check

D=date(2026,9,7)
def mt(w=1,start=510,end=560,first=D,last=date(2026,9,21),room=()):return Meeting(w,start,end,first,last,room,('Alice',))
def fixture():
    sections={}
    for i,c in enumerate('ABCD'):
        sections[c]=[Section(c,'L1','LEC',(mt(i+1),),('Alice',)),Section(c,'L2','LEC',(mt(i+1,900,950),),('Bob',))]
    return Catalog({c:{'credits':3,'name':c} for c in sections},sections,{c:{'LEC'} for c in sections},[])

class Tests(unittest.TestCase):
    def test_full_enumeration(self):
        cat=fixture();rng=random.Random(8)
        for _ in range(25):
            p=Preferences(rng.randrange(6),{1:rng.randrange(6),2:rng.randrange(6)},{'A':{'Alice':rng.randrange(6)}})
            groups=make_groups(cat,list('ABCD'),p);scores,base,_=scoring(groups,p)
            exact=sorted([base+sum(scores[s] for s in combo) for combo in itertools.product(*groups) if check(cat,list('ABCD'),[(s.course,s.code) for s in combo],p)['passed']],reverse=True)[:3]
            result=solve(cat,list('ABCD'),p)
            self.assertEqual(result.status,'optimal')
            for a,b in zip(exact,[s['score'] for s in result.solutions]):self.assertAlmostEqual(a,b)
    def test_early_reversal(self):
        cat=fixture()
        for rating,wanted in [(0,'L2'),(5,'L1')]:
            r=solve(cat,list('ABCD'),Preferences(early=rating))
            self.assertTrue(all(s==wanted for _,s in r.solutions[0]['selections']))
    def test_teacher(self):
        r=solve(fixture(),list('ABCD'),Preferences(teachers={'A':{'Bob':5}}))
        self.assertIn(('A','L2'),r.solutions[0]['selections'])
    def test_day_preference(self):
        cat=fixture();s=cat.sections['A'][1]
        cat.sections['A'][1]=Section('A','L2','LEC',(mt(5,900,950),),s.teachers)
        for rating,wanted in [(0,'L2'),(5,'L1')]:
            r=solve(cat,list('ABCD'),Preferences(weekdays={1:rating}))
            self.assertIn(('A',wanted),r.solutions[0]['selections'])
    def test_hard_ban(self):
        p=Preferences(early=5,ban_early=True)
        r=solve(fixture(),list('ABCD'),p)
        self.assertTrue(check(fixture(),list('ABCD'),r.solutions[0]['selections'],p)['passed'])
        self.assertTrue(all(s=='L2' for _,s in r.solutions[0]['selections']))
    def test_infeasible(self):
        self.assertEqual(solve(fixture(),list('ABCD'),Preferences(banned_days=(1,))).status,'infeasible')
    def test_timeout(self):
        self.assertEqual(solve(fixture(),list('ABCD'),Preferences(),timeout=0).status,'timeout_no_solution')
    def test_credit(self):
        self.assertEqual(solve(fixture(),['A'],Preferences()).status,'invalid')
        cat=fixture();cat.courses['A']['credits']=12
        result=solve(cat,list('ABCD'),Preferences())
        self.assertEqual(result.status,'optimal')
        self.assertTrue(check(cat,list('ABCD'),result.solutions[0]['selections'],Preferences())['passed'])
    def test_unknown_teacher(self):
        self.assertEqual(solve(fixture(),list('ABCD'),Preferences(teachers={'A':{'Wrong':5}})).status,'invalid')
    def test_dates_and_adjacency(self):
        self.assertFalse(overlap(mt(),mt(start=560,end=600)))
        self.assertFalse(overlap(mt(last=D),mt(first=date(2026,9,14))))
        self.assertTrue(overlap(mt(),mt(start=550,end=600)))
        # Date intervals intersect, but contain no shared Monday.
        self.assertFalse(overlap(mt(last=date(2026,9,9)),mt(first=date(2026,9,8))))
    def test_independent_rejection(self):
        cat=fixture();cat.sections['B'][0]=Section('B','L1','LEC',(mt(),),('Alice',))
        r=check(cat,list('ABCD'),[(c,'L1') for c in 'ABCD'],Preferences())
        self.assertFalse(r['passed']);self.assertTrue(any('conflict' in x.lower() for x in r['errors']))
    def test_components(self):
        r=check(fixture(),list('ABCD'),[('A','L1'),('A','L2'),('B','L1'),('C','L1')],Preferences())
        self.assertFalse(r['passed'])
