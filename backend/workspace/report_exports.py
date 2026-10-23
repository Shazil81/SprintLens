"""Render only curated report fields and their frozen project snapshot."""
import csv
from html import escape
from io import BytesIO, StringIO
from pathlib import Path
from reportlab import __file__ as reportlab_file
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, CondPageBreak


def csv_cell(value):
    text = str(value)
    # A quoted CSV cell can still execute a spreadsheet formula when opened.
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')) else text


def csv_report(report):
    stream = StringIO(newline='')
    writer = csv.writer(stream)
    snapshot = report.snapshot
    rows = [['SprintLens project report', report.title], ['Status', report.status],
            ['Captured at', snapshot['captured_at']], ['Period', snapshot['period']['start'], snapshot['period']['end']],
            ['Summary', report.summary], ['Achievements', report.achievements], ['Risks', report.risks], ['Next steps', report.next_steps],
            [], ['Task code', 'Task title', 'Status', 'Due', 'Signals']]
    rows += [[t['code'], t['title'], t['status'], t['due'], '; '.join(t['signals'])] for t in snapshot['tasks']]
    rows += [[], ['Omitted task rows', snapshot['omitted_tasks']]]
    for row in rows:
        writer.writerow([csv_cell(value) for value in row])
    return ('\ufeff' + stream.getvalue()).encode('utf-8')


def pdf_report(report):
    stream = BytesIO()
    font_dir = Path(reportlab_file).parent / 'fonts'
    if 'SprintLens' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('SprintLens', str(font_dir/'Vera.ttf')))
        pdfmetrics.registerFont(TTFont('SprintLensBold', str(font_dir/'VeraBd.ttf')))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportBody', fontName='SprintLens', fontSize=9, leading=14, spaceAfter=9))
    styles.add(ParagraphStyle(name='ReportTitle', fontName='SprintLensBold', fontSize=22, leading=28, textColor=colors.HexColor('#245bd1'), spaceAfter=12))
    styles.add(ParagraphStyle(name='ReportHeading', fontName='SprintLensBold', fontSize=12, leading=17, spaceBefore=15, spaceAfter=8, keepWithNext=True))
    styles.add(ParagraphStyle(name='ReportTableHeading', parent=styles['ReportHeading'], keepWithNext=False))
    styles.add(ParagraphStyle(name='ReportCell', parent=styles['ReportBody'], fontSize=8, leading=12, spaceAfter=0, alignment=TA_LEFT))

    def paragraph(value, style='ReportBody'):
        # Titles and narratives are text, never ReportLab markup supplied by a user.
        return Paragraph(escape(str(value)).replace('\n', '<br/>'), styles[style])

    snapshot = report.snapshot
    story = [paragraph('SprintLens', 'ReportTitle'), paragraph(report.title, 'ReportHeading'),
             paragraph(f"{report.status.upper()} | {snapshot['project']['name']} | Snapshot {snapshot['captured_at']}"),
             paragraph(f"Observed history: {snapshot['period']['start']} to {snapshot['period']['end']}. Current state is as of snapshot capture.")]
    current, observed = snapshot['current'], snapshot['observed']
    story.append(paragraph(f"{current['open']} open | {current['done']} currently done | {current['blocked']} blocked | {current['overdue']} overdue"))
    story.append(paragraph(f"Recorded completions in period: {observed['completion_events']} events across {observed['unique_completed_tasks']} tasks."))
    for title, text in [('Summary',report.summary), ('Achievements',report.achievements), ('Risks and dependencies',report.risks), ('Next steps',report.next_steps)]:
        story += [paragraph(title,'ReportHeading'), paragraph(text or 'Not recorded.')]
    # Let the long table split into the remaining space instead of pushing it to a fresh page.
    story += [CondPageBreak(110), paragraph('Task snapshot','ReportTableHeading')]
    rows = [[paragraph(value,'ReportCell') for value in ['Code','Task','Status','Due','Signals']]]
    rows += [[paragraph(value,'ReportCell') for value in [t['code'],t['title'],t['status'],t['due'],'; '.join(t['signals']) or 'None recorded']] for t in snapshot['tasks']]
    if len(rows) > 1:
        table = LongTable(rows, colWidths=[82,162,65,65,125], repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf3ff')),
                                   ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),0.3,colors.HexColor('#e2e8f0')),
                                   ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(table)
    else:
        story.append(paragraph('No tasks captured.'))
    story += [Spacer(1,10), paragraph(f"Omitted task rows: {snapshot['omitted_tasks']}. No private reviews, employee ratings or note bodies are included automatically.")]
    for note in snapshot['limitations']:
        story.append(paragraph(note))

    def footer(canvas, document):
        canvas.setFont('SprintLens',8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(42,25,'SprintLens | Project progress report')
        canvas.drawRightString(A4[0]-42,25,f'Page {document.page}')

    SimpleDocTemplate(stream, pagesize=A4, rightMargin=42,leftMargin=42,topMargin=34,bottomMargin=42,
                      title=report.title, author='SprintLens').build(story,onFirstPage=footer,onLaterPages=footer)
    return stream.getvalue()
