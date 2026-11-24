"""Append SIS-verified Term 2 data to the user's original seven-page guide."""
from io import BytesIO
from pathlib import Path
import sqlite3
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from pypdf import PdfReader, PdfWriter

ROOT=Path(__file__).parent
SOURCE=Path('/Users/stevenpan/Desktop/大一下选课指南.pdf')
OUTPUT=ROOT/'docs'/'大一下选课指南_更新版.pdf'
DB=ROOT/'data'/'term1_2026_2027.sqlite'
pdfmetrics.registerFont(TTFont('CJK', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Ctitle',fontName='CJK',fontSize=17,leading=23,textColor=colors.HexColor('#213f6b'),spaceAfter=13))
styles.add(ParagraphStyle(name='Chead',fontName='CJK',fontSize=11,leading=16,textColor=colors.HexColor('#213f6b'),spaceBefore=13,spaceAfter=7))
styles.add(ParagraphStyle(name='Cbody',fontName='CJK',fontSize=8.5,leading=13,spaceAfter=5))
styles.add(ParagraphStyle(name='Csmall',fontName='CJK',fontSize=7.1,leading=9))
def p(text,style='Cbody'):return Paragraph(str(text).replace('&','&amp;').replace('<','&lt;'),styles[style])
def section_table(con,code):
    rows=[[p(x,'Csmall') for x in ('区段 / 课号','组件','星期','时间','教室')]]
    q='''SELECT s.section_code,s.class_number,s.component,m.days_raw,m.start_time,m.end_time,m.room
         FROM sections s JOIN meetings m ON m.section_id=s.id
         WHERE s.course_code=? AND s.term='2026-27 Term 2'
         ORDER BY s.id,m.sequence'''
    for section,num,comp,days,a,b,room in con.execute(q,(code,)):
        days=days.replace('星期','周')
        rows.append([p(f'{section} ({num})','Csmall'),p('讲演' if comp=='LEC' else '指导教学','Csmall'),p(days,'Csmall'),p(f'{a}-{b}','Csmall'),p(room or '未公布','Csmall')])
    table=Table(rows,colWidths=[82,52,72,75,204],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dbe5f1')),('GRID',(0,0),(-1,-1),.25,colors.HexColor('#bbc8d7')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7f9fc')]),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    return table
def build():
    con=sqlite3.connect(DB)
    story=[p('2026-27 Term 2 补充核验','Ctitle'),p('本附录接在你上传的原版七页 PDF 后。资料来自学校 SIS「浏览课程目录」中 2026-27 Term 2 的课程详情和“显示时段／全部查看”，核验日期：2026-11-13。原版内容保留；如原版标注“待核”，请以本附录为准。'),p('四门新增课程共 125 个区段，日期均为 2027-01-11 至 2027-05-14，期次 1。SIS 讲师栏均显示“员工”，未公布具体教师。区段可选性及教室可能变化，正式选课前再核对 SIS。')]
    for code in ('MAT1002','STA2001','ENG1002','PED1214'):
        row=con.execute('SELECT name,credits,prerequisites_raw,description FROM courses WHERE code=?',(code,)).fetchone()
        count=con.execute("SELECT count(*) FROM sections WHERE course_code=? AND term='2026-27 Term 2'",(code,)).fetchone()[0]
        story += [p(f'{code} {row[0]} · {row[1]:g} 学分 · {count} 区段','Chead'),p('课程内容：'+row[3]),p('先修／限选：'+(row[2] or 'SIS 未列明。')),section_table(con,code),Spacer(1,9)]
    story += [p('AIE1901 学期核对','Chead'),p('SIS 课程目录中的 AIE1901 当前仅提供 2026-27 Term 1，没有 2026-27 Term 2 可选择的时段。因此本附录和数据库没有为它编造 Term 2 区段。你原计划中的 AI 探索实践课若是 AIE1902，请以该代码重新核对。'),p('数据来源：香港中文大学（深圳）SIS 课程目录；https://sis.cuhk.edu.cn/ 。本附录保留原 PDF 的 MIT OCW 对应与自学建议。')]
    buf=BytesIO();doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=40)
    doc.build(story)
    writer=PdfWriter()
    for page in PdfReader(str(SOURCE)).pages:writer.add_page(page)
    for page in PdfReader(BytesIO(buf.getvalue())).pages:writer.add_page(page)
    with OUTPUT.open('wb') as f:writer.write(f)
    con.close();print(OUTPUT,len(PdfReader(str(OUTPUT)).pages),'pages')
if __name__=='__main__':build()
