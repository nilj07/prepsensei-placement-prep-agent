import fitz  # pymupdf - reads PDFs
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import os


def read_resume(pdf_path):
    # open the PDF and extract all text
    # fitz opens the PDF in binary format
    # then we loop through each page and get text
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    
    # clean up extra whitespace
    # resumes often have weird spacing after PDF extraction
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)


def generate_pdf_report(student_name, company, role, readiness_score,
                         skills_found, skills_missing, feedback_list,
                         study_plan, plan_days, output_path="report.pdf"):
    try:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch
        )
        styles = getSampleStyleSheet()
        story = []

        def safe_text(text):
            # remove characters that reportlab cant handle
            if not text:
                return ""
            return str(text).encode('ascii', 'ignore').decode('ascii')

        story.append(Paragraph("AI Placement Prep Report", styles['Title']))
        story.append(Spacer(1, 0.2*inch))

        story.append(Paragraph(f"Student: {safe_text(student_name)}", styles['Heading2']))
        story.append(Paragraph(f"Target: {safe_text(company)} - {safe_text(role)}", styles['Normal']))
        story.append(Paragraph(f"Readiness Score: {readiness_score}/100", styles['Normal']))
        story.append(Paragraph(f"Study Plan Duration: {plan_days} days", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))

        story.append(Paragraph("Skills You Have", styles['Heading2']))
        if skills_found:
            for skill in skills_found:
                story.append(Paragraph(f"+ {safe_text(skill)}", styles['Normal']))
        else:
            story.append(Paragraph("No skills extracted", styles['Normal']))
        story.append(Spacer(1, 0.15*inch))

        story.append(Paragraph("Skills to Build", styles['Heading2']))
        if skills_missing:
            for skill in skills_missing:
                story.append(Paragraph(f"- {safe_text(skill)}", styles['Normal']))
        else:
            story.append(Paragraph("No skill gaps identified", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))

        story.append(Paragraph("Interview Feedback", styles['Heading2']))
        if feedback_list:
            for i, feedback in enumerate(feedback_list):
                story.append(Paragraph(f"Q{i+1}:", styles['Heading3']))
                story.append(Paragraph(safe_text(feedback), styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
        else:
            story.append(Paragraph("No interview feedback available", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))

        story.append(Paragraph(f"Your {plan_days}-Day Study Plan", styles['Heading2']))
        if study_plan:
            # split study plan into paragraphs to avoid one huge block
            for para in study_plan.split('\n'):
                if para.strip():
                    story.append(Paragraph(safe_text(para.strip()), styles['Normal']))
                    story.append(Spacer(1, 0.05*inch))
        else:
            story.append(Paragraph("Study plan not generated", styles['Normal']))

        doc.build(story)
        print(f"PDF generated successfully at: {output_path}")
        return output_path

    except Exception as e:
        print(f"PDF generation error: {e}")
        import traceback
        traceback.print_exc()
        raise e