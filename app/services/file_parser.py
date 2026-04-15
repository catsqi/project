"""简历文件解析模块 - 支持 PDF 和 Word 文档的文本提取"""

import io
from fastapi import UploadFile, HTTPException
import PyPDF2
from docx import Document


async def extract_text_from_pdf(file: UploadFile) -> str:
    """从 PDF 文件提取文本内容"""
    try:
        content = await file.read()
        pdf_file = io.BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_parts = []
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        return "\n".join(text_parts)
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"PDF 文件解析失败，文件可能已损坏: {str(e)}"
        )


async def extract_text_from_docx(file: UploadFile) -> str:
    """从 Word 文档提取文本内容"""
    try:
        content = await file.read()
        doc_file = io.BytesIO(content)
        doc = Document(doc_file)
        
        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        return "\n".join(text_parts)
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Word 文档解析失败，文件可能已损坏: {str(e)}"
        )


async def extract_text(file: UploadFile) -> str:
    """统一文件解析入口，根据文件类型自动分发"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    filename = file.filename.lower()
    
    if filename.endswith('.pdf'):
        text = await extract_text_from_pdf(file)
    elif filename.endswith('.docx') or filename.endswith('.doc'):
        text = await extract_text_from_docx(file)
    else:
        raise HTTPException(
            status_code=400, 
            detail="不支持的文件格式，请上传 PDF 或 Word 文档"
        )
    
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空，请检查文件")
    
    return text
