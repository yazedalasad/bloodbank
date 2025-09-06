# utils/pdf_generator.py
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from datetime import datetime
from django.conf import settings
import os

def generate_pdf(template_src, context_dict={}):
    """Generate PDF from HTML template"""
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    
    # Create PDF
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return result.getvalue()
    return None

def save_pdf_to_file(pdf_content, filename):
    """Save PDF to a file"""
    filepath = os.path.join(settings.MEDIA_ROOT, 'pdf_reports', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'wb') as f:
        f.write(pdf_content)
    
    return filepath

def get_pdf_url(filename):
    """Get URL for PDF file"""
    return f"{settings.MEDIA_URL}pdf_reports/{filename}"