from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame, PageTemplate
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import datetime as dtt

def generate_sluzhebka(room, date, time_start, time_finish, event, num_participants, responsible):
    # Register a font that supports Cyrillic characters
    pdfmetrics.registerFont(TTFont('OpenSans', 'static\OpenSans-VariableFont_wdth,wght.ttf'))

    # Create a PDF document
    pdf_file = "sluzhebka.pdf"
    doc = SimpleDocTemplate(pdf_file, pagesize=A4)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Russian', fontName='OpenSans', fontSize=12))
    styles['Title'].fontName = 'OpenSans'

    elements = []
    # Add text on the right side
    right_text = [
        ["", "Начальнику Культурно-массового отдела"],
        ["", "Л.Ф. Мхитарян"]
    ]
    right_table = Table(right_text, colWidths=[350, 150])
    right_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (1, 0), (1, -1), 'OpenSans'),
        ('FONTSIZE', (1, 0), (1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12)
    ]))
    elements.append(right_table)
    elements.append(Spacer(1, 12))

    # Title
    elements.append(Paragraph("СЛУЖЕБНАЯ ЗАПИСКА", styles['Title']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(
        (
            f"Прошу вас предоставить {room} с {time_start} {date} до {time_finish} {date} {dtt.date.today().year}"
            +f" для проведения мероприятия «{event}»"
        )
        , styles['Russian']))
    elements.append(Paragraph(
        f"Прошу разрешить доступ в {room} следующим лицам:", styles['Russian']
        +f"",
        styles['Russian']
    ))
    elements.append(Spacer(1, 12))
    participants = Table([
        ["ФИО", "Группа/Должность"],
        ["", ""]*num_participants
    ])
    participants.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'OpenSans'),
    ]))
    # Add the signature table at the bottom of the page
    signature_table = Table([
        [role, "", responsible]
    ], colWidths=[100, 300, 100])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, 0), 'OpenSans'),
        ('FONTNAME', (2, 0), (2, 0), 'OpenSans'),
    ]))

    elements.append(Spacer(1, A4[1] / 3))
    elements.append(signature_table)

    # Build the PDF with a custom page template to position the signature at the bottom
    def on_page(canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 2 * doc.bottomMargin, id='normal')
    template = PageTemplate(id='test', frames=frame, onPage=on_page)
    doc.addPageTemplates([template])

    doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)

    return pdf_file

# Example usage
pdf_path = generate_sluzhebka("101", "01.01.2023", "10:00", "12:00", "проведение экзамена", "Ответственный:", "Иван Иванович")
print(f"PDF generated: {pdf_path}")