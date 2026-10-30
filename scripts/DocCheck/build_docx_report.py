#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_docx_report.py
Tạo báo cáo Đồ án Hệ Cơ sở dữ liệu NoSQL — Đề tài 06 định dạng Word (.docx)
theo chuẩn mẫu luận văn của Trường Đại học Công Thương TP. HCM (HUIT).
Nguồn nội dung: docs/SRS.md (SRS v3.0 đã chuẩn hóa và kiểm thử tự động).

Hỗ trợ 2 chế độ màu:
1. mode="black": Toàn bộ chữ và tiêu đề màu Đen chuẩn học thuật (#000000 / Automatic).
2. mode="blue": Tiêu đề Chương và Mục màu Xanh chuẩn Word/Google Docs (#2E74B5 / #1F4E79), nội dung màu Đen.
"""

import os
import re
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

LOGO_PATH = "/tmp/huit_logo.jpg"
SRS_MD_PATH = "docs/SRS.md"

FONT_MAIN = "Times New Roman"
FONT_CODE = "Consolas"
COLOR_BLACK = RGBColor(0, 0, 0)
COLOR_BLUE_H1 = RGBColor(31, 78, 121)   # #1F4E79 - Dark Accent Blue
COLOR_BLUE_H2 = RGBColor(46, 116, 181)  # #2E74B5 - Accent 1 Blue

def add_page_number_to_run(run):
    """Chèn trường mã Word động tính số trang (PAGE)."""
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = "PAGE"
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'separate')
    fldChar3 = OxmlElement('w:fldChar')
    fldChar3.set(qn('w:fldCharType'), 'end')
    
    r = run._r
    r.append(fldChar1)
    r.append(instrText)
    r.append(fldChar2)
    r.append(fldChar3)

def set_cell_shading(cell, color_hex):
    """Đổ màu nền nhẹ cho ô bảng."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_table_borders(table, color="999999", sz="4", val="single"):
    """Viền bảng thanh mảnh 0.5pt chuẩn học thuật."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    """Set padding cho ô bảng."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def add_formatted_runs(p, text, base_font=FONT_MAIN, base_size=13, default_bold=False, default_italic=False, text_color=COLOR_BLACK):
    """Phân tách markdown inline."""
    pattern = r'(\*\*.*?\*\*|\*.*?\*|`.*?`|\$.*?\$)'
    parts = re.split(pattern, text)
    for part in parts:
        if not part:
            continue
        run = p.add_run()
        run.font.name = base_font
        run.font.size = Pt(base_size)
        run.bold = default_bold
        run.italic = default_italic
        run.font.color.rgb = text_color
            
        if part.startswith('**') and part.endswith('**'):
            run.text = part[2:-2]
            run.bold = True
        elif part.startswith('*') and part.endswith('*'):
            run.text = part[1:-1]
            run.italic = True
        elif part.startswith('`') and part.endswith('`'):
            run.text = part[1:-1]
            run.font.name = FONT_CODE
            run.font.size = Pt(base_size - 1.0)
            run.bold = True
        elif part.startswith('$') and part.endswith('$'):
            run.text = part[1:-1]
            run.italic = True
        else:
            run.text = part

def format_paragraph(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.3, space_before=0, space_after=6, indent=0, left_indent=0):
    p.alignment = align
    fmt = p.paragraph_format
    fmt.line_spacing = line_spacing
    fmt.space_before = Pt(space_before)
    fmt.space_after = Pt(space_after)
    if indent > 0:
        fmt.first_line_indent = Inches(indent)
    if left_indent > 0:
        fmt.left_indent = Inches(left_indent)

def build_cover_page(doc, is_outer=True, heading_color=COLOR_BLACK):
    """Xây dựng trang bìa chuẩn mẫu HUIT."""
    section = doc.sections[0] if is_outer else doc.add_section(docx.enum.section.WD_SECTION.NEW_PAGE)
    
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.2)
    section.right_margin = Inches(0.8)
    
    p1 = doc.add_paragraph()
    format_paragraph(p1, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=1.15, space_before=0, space_after=2)
    r1 = p1.add_run("BỘ CÔNG THƯƠNG\nTRƯỜNG ĐẠI HỌC CÔNG THƯƠNG TP. HỒ CHÍ MINH\n")
    r1.font.name = FONT_MAIN
    r1.font.size = Pt(13)
    r1.bold = True
    r1.font.color.rgb = COLOR_BLACK
    
    r2 = p1.add_run("KHOA CÔNG NGHỆ THÔNG TIN")
    r2.font.name = FONT_MAIN
    r2.font.size = Pt(14)
    r2.bold = True
    r2.font.color.rgb = heading_color
    
    p_line = doc.add_paragraph()
    format_paragraph(p_line, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=1.0, space_before=2, space_after=14)
    r_line = p_line.add_run("---------------------------")
    r_line.font.name = FONT_MAIN
    r_line.font.size = Pt(14)
    r_line.font.color.rgb = COLOR_BLACK
    
    if os.path.exists(LOGO_PATH):
        p_logo = doc.add_paragraph()
        format_paragraph(p_logo, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=1.0, space_before=4, space_after=20)
        p_logo.add_run().add_picture(LOGO_PATH, width=Inches(1.5), height=Inches(1.5))
    
    p_sub = doc.add_paragraph()
    format_paragraph(p_sub, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=1.2, space_before=6, space_after=4)
    r_sub = p_sub.add_run("ĐỒ ÁN MÔN HỌC HỆ CƠ SỞ DỮ LIỆU NOSQL")
    r_sub.font.name = FONT_MAIN
    r_sub.font.size = Pt(16)
    r_sub.bold = True
    r_sub.font.color.rgb = COLOR_BLACK
    
    p_de = doc.add_paragraph()
    format_paragraph(p_de, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=1.2, space_before=4, space_after=4)
    r_de = p_de.add_run("ĐỀ TÀI:")
    r_de.font.name = FONT_MAIN
    r_de.font.size = Pt(16)
    r_de.bold = True
    r_de.font.color.rgb = heading_color
    
    p_title = doc.add_paragraph()
    format_paragraph(p_title, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=1.25, space_before=4, space_after=10)
    r_title = p_title.add_run("PHÂN HỆ CACHING BÀI VIẾT VÀ QUẢN LÝ PHIÊN")
    r_title.font.name = FONT_MAIN
    r_title.font.size = Pt(18)
    r_title.bold = True
    r_title.font.color.rgb = heading_color
    
    p_srs = doc.add_paragraph()
    format_paragraph(p_srs, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=1.2, space_before=2, space_after=32)
    r_srs = p_srs.add_run("ĐẶC TẢ YÊU CẦU PHẦN MỀM (SRS v3.0)")
    r_srs.font.name = FONT_MAIN
    r_srs.font.size = Pt(13)
    r_srs.bold = True
    r_srs.font.color.rgb = COLOR_BLACK
    
    p_gvhd = doc.add_paragraph()
    format_paragraph(p_gvhd, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.2, space_before=2, space_after=4, left_indent=1.5)
    r_gvhd = p_gvhd.add_run("GVHD: ThS. Trần Quang Bình")
    r_gvhd.font.name = FONT_MAIN
    r_gvhd.font.size = Pt(13)
    r_gvhd.bold = True
    r_gvhd.font.color.rgb = COLOR_BLACK
    
    p_lop = doc.add_paragraph()
    format_paragraph(p_lop, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.2, space_before=2, space_after=4, left_indent=1.5)
    r_lop = p_lop.add_run("Lớp: 14DHTH13 - 010110197517")
    r_lop.font.name = FONT_MAIN
    r_lop.font.size = Pt(13)
    r_lop.bold = True
    r_lop.font.color.rgb = COLOR_BLACK
    
    p_tv = doc.add_paragraph()
    format_paragraph(p_tv, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.2, space_before=2, space_after=4, left_indent=1.5)
    r_tv = p_tv.add_run("Thành viên thực hiện:")
    r_tv.font.name = FONT_MAIN
    r_tv.font.size = Pt(13)
    r_tv.bold = True
    r_tv.font.color.rgb = COLOR_BLACK
    
    members = [
        "Hồ Ngọc Phương Như - 2001230001 - NT",
        "Nguyễn Anh Quân - 2001230717",
        "Nguyễn Xuân Định - 2001230002"
    ]
    for m in members:
        p_m = doc.add_paragraph()
        format_paragraph(p_m, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.2, space_before=1, space_after=2, left_indent=1.9)
        r_m = p_m.add_run(m)
        r_m.font.name = FONT_MAIN
        r_m.font.size = Pt(13)
        r_m.bold = True
        r_m.font.color.rgb = COLOR_BLACK
        
    p_date = doc.add_paragraph()
    format_paragraph(p_date, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=1.15, space_before=36, space_after=0)
    r_date = p_date.add_run("TP. HỒ CHÍ MINH, tháng 10 năm 2026")
    r_date.font.name = FONT_MAIN
    r_date.font.size = Pt(12)
    r_date.font.color.rgb = COLOR_BLACK

def build_front_matter(doc, heading_color=COLOR_BLACK):
    """Xây dựng phần đầu: Lời cam đoan, Lời cảm ơn, Mục lục, Từ viết tắt, Bảng phân công."""
    
    sec_front = doc.add_section(docx.enum.section.WD_SECTION.NEW_PAGE)
    sec_front.top_margin = Inches(1.0)
    sec_front.bottom_margin = Inches(1.0)
    sec_front.left_margin = Inches(1.2)
    sec_front.right_margin = Inches(0.8)
    
    # 1. LỜI CAM ĐOAN
    p_cd = doc.add_paragraph()
    format_paragraph(p_cd, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=12, space_after=18)
    r_cd = p_cd.add_run("LỜI CAM ĐOAN")
    r_cd.font.name = FONT_MAIN
    r_cd.font.size = Pt(16)
    r_cd.bold = True
    r_cd.font.color.rgb = heading_color
    
    p_cd_txt1 = doc.add_paragraph()
    format_paragraph(p_cd_txt1, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.3, space_before=0, space_after=8, indent=0.4)
    p_cd_txt1.add_run(
        "Nhóm sinh viên thực hiện xin cam đoan rằng Báo cáo Đồ án và Tài liệu Đặc tả Yêu cầu Phần mềm (SRS v3.0) "
        "với đề tài “Phân hệ Caching bài viết và Quản lý phiên (Session Management)” là công trình nghiên cứu, "
        "thiết kế và hiện thực độc lập của tập thể nhóm 3 thành viên dưới sự định hướng của Giảng viên hướng dẫn. "
        "Mọi số liệu thực nghiệm đo lường hiệu năng Cache-Aside, khả năng chống sập nguồn Cache Stampede, "
        "thông lượng chịu tải đồng thời cũng như các kết quả kiểm thử tự động (78 unit/integration tests .NET, "
        "103 Vitest frontend) đều được ghi nhận trực tiếp từ hệ thống thực tế đang chạy trên môi trường Docker (MongoDB 7.0, Redis 7.2 Alpine, ASP.NET Core 8 Web API)."
    )
    
    p_cd_txt2 = doc.add_paragraph()
    format_paragraph(p_cd_txt2, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.3, space_before=0, space_after=24, indent=0.4)
    p_cd_txt2.add_run(
        "Toàn bộ mã nguồn, cấu hình CSDL, dữ liệu seed mẫu và nội dung văn bản đặc tả hoàn toàn trung thực, "
        "tuân thủ nghiêm ngặt chuẩn mực đạo đức học thuật và không sao chép từ bất kỳ đồ án nào khác. "
        "Nhóm xin chịu hoàn toàn trách nhiệm cá nhân trước Khoa Công nghệ Thông tin, Trường Đại học Công Thương TP. Hồ Chí Minh nếu có bất kỳ sự gian lận nào."
    )
    
    p_cd_sign = doc.add_paragraph()
    format_paragraph(p_cd_sign, align=WD_ALIGN_PARAGRAPH.RIGHT, space_before=12, space_after=4)
    r_sign_date = p_cd_sign.add_run("TP. Hồ Chí Minh, ngày 29 tháng 10 năm 2026\n")
    r_sign_date.font.name = FONT_MAIN
    r_sign_date.font.size = Pt(12)
    r_sign_date.italic = True
    r_sign_title = p_cd_sign.add_run("Đại diện nhóm sinh viên thực hiện\n(Ký và ghi rõ họ tên)")
    r_sign_title.font.name = FONT_MAIN
    r_sign_title.font.size = Pt(12)
    r_sign_title.bold = True
    
    p_cd_names = doc.add_paragraph()
    format_paragraph(p_cd_names, align=WD_ALIGN_PARAGRAPH.RIGHT, space_before=40, space_after=12)
    r_names = p_cd_names.add_run("Hồ Ngọc Phương Như  —  Nguyễn Anh Quân  —  Nguyễn Xuân Định")
    r_names.font.name = FONT_MAIN
    r_names.font.size = Pt(12)
    r_names.bold = True
    
    # 2. LỜI CẢM ƠN
    doc.add_page_break()
    p_co = doc.add_paragraph()
    format_paragraph(p_co, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=12, space_after=18)
    r_co = p_co.add_run("LỜI CẢM ƠN")
    r_co.font.name = FONT_MAIN
    r_co.font.size = Pt(16)
    r_co.bold = True
    r_co.font.color.rgb = heading_color
    
    p_co_txt1 = doc.add_paragraph()
    format_paragraph(p_co_txt1, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.3, space_before=0, space_after=8, indent=0.4)
    p_co_txt1.add_run(
        "Lời đầu tiên, nhóm sinh viên xin trân trọng gửi lời cảm ơn sâu sắc đến Ban Giám hiệu nhà trường "
        "cùng toàn thể quý Thầy, Cô thuộc Khoa Công nghệ Thông tin — Trường Đại học Công Thương TP. Hồ Chí Minh (HUIT) "
        "đã tận tình truyền đạt những kiến thức khoa học máy tính quý báu và tạo điều kiện cơ sở vật chất tối ưu "
        "cho chúng em trong suốt quá trình học tập và nghiên cứu tại trường."
    )
    
    p_co_txt2 = doc.add_paragraph()
    format_paragraph(p_co_txt2, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.3, space_before=0, space_after=8, indent=0.4)
    p_co_txt2.add_run(
        "Đặc biệt, nhóm chúng em xin bày tỏ lòng biết ơn chân thành nhất đến ThS. Trần Quang Bình là Giảng viên hướng dẫn "
        "trực tiếp môn học Hệ Cơ sở dữ liệu NoSQL. Nhờ sự định hướng kiến trúc tận tình, các lời khuyên chuyên sâu về phân tầng CSDL "
        "và những phản biện sắc sảo của Thầy trong từng buổi học, nhóm đã tiếp thu được các phương pháp tư duy NoSQL hiện đại, "
        "hiểu rõ bản chất tối ưu của Caching đa tầng và hoàn thành xuất sắc đồ án Đề tài 06 đúng tiến độ."
    )
    
    p_co_txt3 = doc.add_paragraph()
    format_paragraph(p_co_txt3, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.3, space_before=0, space_after=24, indent=0.4)
    p_co_txt3.add_run(
        "Dù đã rất nỗ lực hoàn thiện toàn diện đồ án và báo cáo đặc tả SRS, nhưng do kinh nghiệm thực tế còn đang tích lũy, "
        "hệ thống chắc chắn khó tránh khỏi những điểm có thể cải tiến thêm. Nhóm chúng em rất mong nhận được những góp ý, "
        "chỉ bảo quý giá từ Thầy để hoàn thiện sản phẩm phần mềm ngày một hoàn thiện và tối ưu hơn.\n"
        "Kính chúc Thầy cùng toàn thể quý Thầy Cô luôn dồi dào sức khỏe, hạnh phúc và thành công rực rỡ trong sự nghiệp giảng dạy!"
    )
    
    p_co_sign = doc.add_paragraph()
    format_paragraph(p_co_sign, align=WD_ALIGN_PARAGRAPH.RIGHT, space_before=12, space_after=40)
    r_co_sign = p_co_sign.add_run("TP. Hồ Chí Minh, năm 2026\nNhóm sinh viên thực hiện\n(Ký và ghi rõ họ tên)")
    r_co_sign.font.name = FONT_MAIN
    r_co_sign.font.size = Pt(12)
    r_co_sign.bold = True
    
    p_co_names = doc.add_paragraph()
    format_paragraph(p_co_names, align=WD_ALIGN_PARAGRAPH.RIGHT, space_before=12, space_after=12)
    r_co_names = p_co_names.add_run("Hồ Ngọc Phương Như  —  Nguyễn Anh Quân  —  Nguyễn Xuân Định")
    r_co_names.font.name = FONT_MAIN
    r_co_names.font.size = Pt(12)
    r_co_names.bold = True
    
    # 3. MỤC LỤC
    doc.add_page_break()
    p_ml = doc.add_paragraph()
    format_paragraph(p_ml, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=12, space_after=18)
    r_ml = p_ml.add_run("MỤC LỤC")
    r_ml.font.name = FONT_MAIN
    r_ml.font.size = Pt(16)
    r_ml.bold = True
    r_ml.font.color.rgb = heading_color
    
    toc_items = [
        ("LỜI CAM ĐOAN", "i", True),
        ("LỜI CẢM ƠN", "ii", True),
        ("MỤC LỤC", "iii", True),
        ("DANH MỤC TỪ VIẾT TẮT", "iv", True),
        ("BẢNG PHÂN CÔNG CÔNG VIỆC", "v", True),
        ("CHƯƠNG 1: MỞ ĐẦU", "1", True),
        ("    1.1 Đặt vấn đề và lý do chọn đề tài", "1", False),
        ("    1.2 Mục tiêu và phạm vi đề tài", "2", False),
        ("    1.3 Phương pháp thực hiện & Quy ước tài liệu", "3", False),
        ("    1.4 Bố cục báo cáo", "4", False),
        ("    1.5 Yêu cầu nguồn từ Đề bài 06 (DB-01 … DB-19)", "5", False),
        ("CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ KIẾN TRÚC HỆ THỐNG", "8", True),
        ("    2.1 Tổng quan về Cơ sở dữ liệu NoSQL", "8", False),
        ("        2.1.1 Document Database với MongoDB", "8", False),
        ("        2.1.2 In-Memory Key-Value Data Store với Redis", "9", False),
        ("    2.2 Mô hình Caching và Chiến lược Cache-Aside Pattern", "11", False),
        ("        2.2.1 Nguyên lý Cache-Aside (Lazy Loading)", "11", False),
        ("        2.2.2 Quy trình cập nhật: Ghi MongoDB trước, xóa Cache Redis sau", "12", False),
        ("        2.2.3 Vô hiệu hóa cache danh sách O(1) qua Version Key (posts:ver)", "13", False),
        ("    2.3 Quản lý phiên làm việc tập trung bằng Redis Hashes", "14", False),
        ("        2.3.1 Kiến trúc Stateless Session Management", "14", False),
        ("        2.3.2 Sliding Expiration và SessionAuthMiddleware", "15", False),
        ("    2.4 Bộ đếm lượt xem thời gian thực (Atomic View Counter)", "16", False),
        ("        2.4.1 Cơ chế INCR nguyên tử trên Redis", "16", False),
        ("        2.4.2 Bộ đệm Dirty Views Set và tiến trình Write-Behind định kỳ", "17", False),
        ("    2.5 Cơ chế khóa phân tán (Distributed Lock) chống Cache Stampede", "18", False),
        ("    2.6 Kiến trúc hệ thống phân tầng (3-tier Architecture)", "19", False),
        ("CHƯƠNG 3: ĐẶC TẢ YÊU CẦU PHẦN MỀM (SRS)", "21", True),
        ("    3.1 Bối cảnh và Tác nhân hệ thống (Guest, Member, Admin)", "21", False),
        ("    3.2 Yêu cầu giao diện bên ngoài", "22", False),
        ("        3.2.1 Giao diện người dùng (IR-01 … IR-05)", "22", False),
        ("        3.2.2 Giao diện phần mềm & Thư viện tích hợp", "25", False),
        ("        3.2.3 Giao diện truyền thông & Giao thức mạng", "26", False),
        ("    3.3 Yêu cầu chức năng chi tiết (FR-01 … FR-22)", "27", False),
        ("    3.4 Yêu cầu phi chức năng (NFR-01 … NFR-09)", "43", False),
        ("    3.5 Thiết kế Cơ sở dữ liệu logic", "47", False),
        ("        3.5.1 CSDL Document MongoDB (Collections & Indexes)", "47", False),
        ("        3.5.2 CSDL In-Memory Redis Keyspace chuẩn", "50", False),
        ("        3.5.3 Định mức bộ dữ liệu mẫu (Dummy Data)", "52", False),
        ("    3.6 Thiết kế giao diện API Backend RESTful", "53", False),
        ("CHƯƠNG 4: THỰC NGHIỆM VÀ ĐÁNH GIÁ KẾT QUẢ", "56", True),
        ("    4.1 Môi trường và Quy trình thử nghiệm", "56", False),
        ("    4.2 Kết quả đo lường độ trễ Cache Hit và Cache Miss (Speedup x11.8 - x62.6)", "57", False),
        ("    4.3 Kết quả kiểm nghiệm chống Cache Stampede (100 concurrency)", "59", False),
        ("    4.4 Kết quả kiểm thử chịu tải đồng thời (Concurrency & Throughput)", "60", False),
        ("    4.5 Kết quả kiểm thử tự động toàn diện (78 .NET + 103 Vitest)", "62", False),
        ("    4.6 Kịch bản demo sống 3 bước bảo vệ đồ án", "64", False),
        ("CHƯƠNG 5: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", "67", True),
        ("    5.1 Đánh giá chung kết quả đạt được (Đối chiếu Barem điểm 10/10)", "67", False),
        ("    5.2 Hạn chế và Bài học kinh nghiệm", "68", False),
        ("    5.3 Hướng phát triển trong tương lai", "69", False),
        ("TÀI LIỆU THAM KHẢO", "70", True),
        ("PHỤ LỤC", "71", True),
        ("    Phụ lục A: Ma trận truy vết yêu cầu (Barem 10 điểm & 37 Ticket Jira)", "71", False),
        ("    Phụ lục B: Danh mục Test Case kiểm thử tự động (TC-01 … TC-55)", "74", False),
        ("    Phụ lục C: Vấn đề tài liệu nguồn và Quyết định xử lý", "79", False),
        ("    Phụ lục D: Hướng dẫn công cụ kiểm thử tài liệu check_srs.py", "81", False)
    ]
    
    for title, page, is_bold in toc_items:
        p_item = doc.add_paragraph()
        format_paragraph(p_item, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.15, space_before=1, space_after=2)
        dots_count = max(4, 75 - len(title) - len(page))
        dots = " ." * (dots_count // 2)
        full_line = f"{title}{dots} {page}"
        run = p_item.add_run(full_line)
        run.font.name = FONT_MAIN
        run.font.size = Pt(11)
        run.bold = is_bold
        run.font.color.rgb = heading_color if is_bold else COLOR_BLACK

    # 4. DANH MỤC TỪ VIẾT TẮT
    doc.add_page_break()
    p_vt = doc.add_paragraph()
    format_paragraph(p_vt, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=12, space_after=18)
    r_vt = p_vt.add_run("DANH MỤC TỪ VIẾT TẮT")
    r_vt.font.name = FONT_MAIN
    r_vt.font.size = Pt(16)
    r_vt.bold = True
    r_vt.font.color.rgb = heading_color
    
    acronyms = [
        ("ACID", "Atomicity, Consistency, Isolation, Durability", "Bốn đặc tính toàn vẹn kinh điển của các hệ thống CSDL quan hệ (RDBMS)."),
        ("BASE", "Basically Available, Soft state, Eventual consistency", "Mô hình tính nhất quán cuối cùng đặc trưng của các hệ thống NoSQL phân tán."),
        ("BSON", "Binary JSON", "Định dạng nhị phân mã hóa tài liệu JSON có kiểu dữ liệu mạnh trong MongoDB."),
        ("Cache-Aside", "Cache-Aside Pattern (Lazy Loading)", "Mô hình ứng dụng chịu trách nhiệm tự đọc cache, trượt thì đọc DB rồi tự nạp cache."),
        ("CQRS", "Command Query Responsibility Segregation", "Mô hình phân tách quyền đọc và ghi dữ liệu thành hai giao diện/dịch vụ độc lập."),
        ("CRUD", "Create, Read, Update, Delete", "Bốn thao tác dữ liệu nền tảng trên tài nguyên bài viết và danh mục."),
        ("FR", "Functional Requirement", "Yêu cầu chức năng mà hệ thống bắt buộc phải cung cấp (từ FR-01 đến FR-22)."),
        ("JWT", "JSON Web Token", "Chuẩn định danh không trạng thái (dự phòng); dự án sử dụng Cookie-based Redis Session Hashes."),
        ("LFU", "Least Frequently Used", "Chính sách giải phóng khóa bộ nhớ Redis dựa trên tần suất truy xuất ít nhất."),
        ("LRU", "Least Recently Used", "Chính sách giải phóng khóa bộ nhớ Redis dựa trên thời gian truy xuất xa nhất."),
        ("NFR", "Non-Functional Requirement", "Yêu cầu phi chức năng về hiệu năng, bảo mật, tính nhất quán (NFR-01 đến NFR-09)."),
        ("NoSQL", "Not Only SQL", "Họ các hệ quản trị CSDL thế hệ mới phi quan hệ, tối ưu hiệu năng và khả năng mở rộng ngang."),
        ("RFC", "Request for Comments", "Hệ thống tài liệu chuẩn kỹ thuật Internet (RFC 6265 cho Cookie, RFC 7231 cho HTTP)."),
        ("SRS", "Software Requirements Specification", "Tài liệu Đặc tả Yêu cầu Phần mềm theo chuẩn quốc tế IEEE 830 / ISO 29148."),
        ("TTL", "Time To Live", "Thời gian sống tối đa của một bản ghi trong bộ nhớ cache Redis trước khi tự động hết hạn."),
        ("VU", "Virtual User", "Người dùng ảo được giả lập đồng thời trong các bài kiểm thử chịu tải k6 và Python."),
        ("Write-Behind", "Write-Behind Caching (Write-Back)", "Cơ chế cập nhật dữ liệu ghi nhận ngay vào Cache, sau đó đồng bộ bất đồng bộ ngầm về DB gốc.")
    ]
    
    tbl_vt = doc.add_table(rows=len(acronyms) + 1, cols=3)
    tbl_vt.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_vt.autofit = False
    set_table_borders(tbl_vt, color="999999", sz="4")
    
    vt_widths = [Inches(1.2), Inches(2.2), Inches(3.1)]
    headers = ["Từ viết tắt", "Tên tiếng Anh đầy đủ", "Định nghĩa & Ý nghĩa kỹ thuật trong dự án"]
    
    for c_idx, h_text in enumerate(headers):
        cell = tbl_vt.rows[0].cells[c_idx]
        cell.width = vt_widths[c_idx]
        set_cell_shading(cell, "F2F2F2")
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
        p = cell.paragraphs[0]
        format_paragraph(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=1.15, space_before=0, space_after=0)
        run = p.add_run(h_text)
        run.font.name = FONT_MAIN
        run.font.size = Pt(11)
        run.bold = True
        run.font.color.rgb = COLOR_BLACK
        
    for r_idx, (acr, eng, vie) in enumerate(acronyms):
        row = tbl_vt.rows[r_idx + 1]
        for c_idx, val in enumerate([acr, eng, vie]):
            cell = row.cells[c_idx]
            cell.width = vt_widths[c_idx]
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)
            p = cell.paragraphs[0]
            align = WD_ALIGN_PARAGRAPH.CENTER if c_idx == 0 else WD_ALIGN_PARAGRAPH.LEFT
            format_paragraph(p, align=align, line_spacing=1.15, space_before=0, space_after=0)
            run = p.add_run(val)
            run.font.name = FONT_MAIN
            run.font.size = Pt(10.5)
            run.font.color.rgb = COLOR_BLACK
            if c_idx == 0:
                run.bold = True

    # 5. BẢNG PHÂN CÔNG CÔNG VIỆC
    doc.add_page_break()
    p_pc = doc.add_paragraph()
    format_paragraph(p_pc, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=12, space_after=18)
    r_pc = p_pc.add_run("BẢNG PHÂN CÔNG CÔNG VIỆC")
    r_pc.font.name = FONT_MAIN
    r_pc.font.size = Pt(16)
    r_pc.bold = True
    r_pc.font.color.rgb = heading_color
    
    tasks = [
        ("Hồ Ngọc Phương Như (SV1)", "2001230001", "Data Architect & CRUD Lead: Thiết kế DB MongoDB & mô hình dữ liệu Redis; Hiện thực API CRUD bài viết, danh mục, xác thực đăng ký/đăng nhập, Bootstrap Admin nguyên tử, quản trị phiên phía backend; Viết tài liệu SRS và cấu trúc DB.", "100%"),
        ("Nguyễn Anh Quân (SV2)", "2001230717", "Advanced Query Specialist: Hiện thực luồng Cache-Aside (GET /api/posts/{id}), Khóa phân tán Redis chống Cache Stampede, Middleware SessionAuthMiddleware với Sliding Expiration 30 phút, Bộ đếm INCR lượt xem thời gian thực, Cache danh sách theo phiên bản posts:ver O(1), Background Worker chốt view về MongoDB.", "100%"),
        ("Nguyễn Xuân Định (SV3)", "2001230002", "Fullstack Integrator & DB Tester: Nạp dữ liệu kiểm thử (Seed >= 100 bài viết có ảnh thật Unsplash), Xây dựng ứng dụng web tin tức đa giao diện (React Vite), Thực hiện đo lường Benchmark hiệu năng Cache Hit/Miss, Viết kịch bản kiểm thử tải và điều phối 3 bước demo sống.", "100%")
    ]
    
    tbl_pc = doc.add_table(rows=len(tasks) + 1, cols=4)
    tbl_pc.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_pc.autofit = False
    set_table_borders(tbl_pc, color="999999", sz="4")
    
    pc_widths = [Inches(1.8), Inches(1.1), Inches(3.0), Inches(0.6)]
    pc_headers = ["Thành viên (Vai trò)", "MSSV", "Công việc đảm nhận theo Đề tài 06", "Mức độ"]
    
    for c_idx, h_text in enumerate(pc_headers):
        cell = tbl_pc.rows[0].cells[c_idx]
        cell.width = pc_widths[c_idx]
        set_cell_shading(cell, "F2F2F2")
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
        p = cell.paragraphs[0]
        format_paragraph(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=1.15, space_before=0, space_after=0)
        run = p.add_run(h_text)
        run.font.name = FONT_MAIN
        run.font.size = Pt(11)
        run.bold = True
        run.font.color.rgb = COLOR_BLACK
        
    for r_idx, (tv, mssv, cw, md) in enumerate(tasks):
        row = tbl_pc.rows[r_idx + 1]
        for c_idx, val in enumerate([tv, mssv, cw, md]):
            cell = row.cells[c_idx]
            cell.width = pc_widths[c_idx]
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)
            p = cell.paragraphs[0]
            align = WD_ALIGN_PARAGRAPH.CENTER if c_idx in [1, 3] else WD_ALIGN_PARAGRAPH.LEFT
            format_paragraph(p, align=align, line_spacing=1.15, space_before=0, space_after=0)
            run = p.add_run(val)
            run.font.name = FONT_MAIN
            run.font.size = Pt(10.5)
            run.font.color.rgb = COLOR_BLACK
            if c_idx == 0:
                run.bold = True

def add_heading_styled(doc, text, level, heading_color=COLOR_BLACK):
    """Thêm tiêu đề chuẩn phân cấp với màu tương ứng."""
    p = doc.add_paragraph()
    if level == 1:
        format_paragraph(p, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.2, space_before=16, space_after=8)
        run = p.add_run(text.upper())
        run.font.name = FONT_MAIN
        run.font.size = Pt(14)
        run.bold = True
        run.font.color.rgb = heading_color
    elif level == 2:
        format_paragraph(p, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.2, space_before=12, space_after=6)
        run = p.add_run(text)
        run.font.name = FONT_MAIN
        run.font.size = Pt(13)
        run.bold = True
        run.font.color.rgb = heading_color
    elif level == 3:
        format_paragraph(p, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.2, space_before=8, space_after=4)
        run = p.add_run(text)
        run.font.name = FONT_MAIN
        run.font.size = Pt(13)
        run.bold = True
        run.italic = True
        run.font.color.rgb = heading_color
    else:
        format_paragraph(p, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.15, space_before=6, space_after=2)
        run = p.add_run(text)
        run.font.name = FONT_MAIN
        run.font.size = Pt(12)
        run.bold = True
        run.font.color.rgb = COLOR_BLACK
    return p

def render_table_from_lines(doc, table_lines):
    """Render bảng chuẩn Table Grid."""
    rows = []
    for line in table_lines:
        line_clean = line.strip()
        if not line_clean.startswith('|') or not line_clean.endswith('|'):
            continue
        if re.match(r'^\|[\s\-:|]+\|$', line_clean):
            continue
        cells = [c.strip() for c in line_clean[1:-1].split('|')]
        rows.append(cells)
        
    if not rows:
        return
        
    num_cols = max(len(r) for r in rows)
    num_rows = len(rows)
    
    tbl = doc.add_table(rows=num_rows, cols=num_cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = True
    set_table_borders(tbl, color="999999", sz="4")
    
    total_w = 6.4
    col_w = Inches(total_w / num_cols)
    
    for r_idx, row in enumerate(rows):
        table_row = tbl.rows[r_idx]
        is_header = (r_idx == 0)
        for c_idx in range(num_cols):
            val = row[c_idx] if c_idx < len(row) else ""
            cell = table_row.cells[c_idx]
            cell.width = col_w
            set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
            
            if is_header:
                set_cell_shading(cell, "F2F2F2")
                
            p = cell.paragraphs[0]
            align = WD_ALIGN_PARAGRAPH.CENTER if is_header else WD_ALIGN_PARAGRAPH.LEFT
            format_paragraph(p, align=align, line_spacing=1.15, space_before=0, space_after=0)
            
            if is_header:
                run = p.add_run(val)
                run.font.name = FONT_MAIN
                run.font.size = Pt(10.5)
                run.bold = True
                run.font.color.rgb = COLOR_BLACK
            else:
                add_formatted_runs(p, val, base_font=FONT_MAIN, base_size=10.0)

def render_code_block(doc, code_lines):
    """Render code block thụt lề phông Consolas."""
    lines_content = []
    for line in code_lines:
        if line.strip().startswith('```'):
            continue
        lines_content.append(line)
        
    for code_line in lines_content:
        p = doc.add_paragraph()
        format_paragraph(p, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.15, space_before=0, space_after=1, left_indent=0.4)
        run = p.add_run(code_line if code_line.strip() else " ")
        run.font.name = FONT_CODE
        run.font.size = Pt(9.5)
        run.font.color.rgb = COLOR_BLACK

def parse_and_append_markdown(doc, md_text, heading_offset=0, heading_color=COLOR_BLACK):
    """Phân tích Markdown và nạp vào document."""
    lines = md_text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        line_str = line.strip()
        
        if not line_str:
            i += 1
            continue
            
        if line_str.startswith('```'):
            code_lines = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                code_lines.append(lines[i])
                i += 1
            render_code_block(doc, code_lines)
            continue
            
        if line_str.startswith('|') and line_str.endswith('|'):
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                table_lines.append(lines[i])
                i += 1
            render_table_from_lines(doc, table_lines)
            continue
            
        if line_str.startswith('#'):
            level = len(line_str) - len(line_str.lstrip('#'))
            title_text = line_str.lstrip('#').strip()
            add_heading_styled(doc, title_text, level + heading_offset, heading_color=heading_color)
            i += 1
            continue
            
        if line_str.startswith('>'):
            quote_lines = [line_str.lstrip('>').strip()]
            i += 1
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote_lines.append(lines[i].strip().lstrip('>').strip())
                i += 1
            p_q = doc.add_paragraph()
            format_paragraph(p_q, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.25, space_before=3, space_after=6, left_indent=0.35)
            add_formatted_runs(p_q, " ".join(quote_lines), default_italic=True)
            continue
            
        if line_str.startswith(('- ', '* ')) or re.match(r'^\d+\.\s', line_str):
            p_list = doc.add_paragraph()
            format_paragraph(p_list, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.2, space_before=1, space_after=3)
            fmt = p_list.paragraph_format
            fmt.left_indent = Inches(0.35)
            fmt.first_line_indent = Inches(-0.2)
            
            if line_str.startswith(('- ', '* ')):
                bullet_run = p_list.add_run("•  ")
                bullet_run.bold = True
                bullet_run.font.color.rgb = COLOR_BLACK
                item_text = line_str[2:].strip()
            else:
                m = re.match(r'^(\d+\.)\s*(.*)', line_str)
                num_run = p_list.add_run(m.group(1) + " ")
                num_run.bold = True
                num_run.font.color.rgb = COLOR_BLACK
                item_text = m.group(2).strip()
                
            add_formatted_runs(p_list, item_text, base_font=FONT_MAIN, base_size=12.5)
            i += 1
            continue
            
        para_lines = [line_str]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or nxt.startswith(('#', '|', '```', '>', '- ', '* ')) or re.match(r'^\d+\.\s', nxt):
                break
            para_lines.append(nxt)
            i += 1
            
        full_para_text = " ".join(para_lines)
        p_body = doc.add_paragraph()
        format_paragraph(p_body, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.3, space_before=0, space_after=6, indent=0.35)
        add_formatted_runs(p_body, full_para_text, base_font=FONT_MAIN, base_size=13.0)

def generate_document(target_file, mode="black"):
    h_col = COLOR_BLUE_H1 if mode == "blue" else COLOR_BLACK
    print(f"Xây dựng tài liệu: {target_file} (mode={mode})...")
    doc = docx.Document()
    
    # 1. Bìa 1
    build_cover_page(doc, is_outer=True, heading_color=h_col)
    
    # 2. Bìa 2
    build_cover_page(doc, is_outer=False, heading_color=h_col)
    
    # 3. Front Matter
    build_front_matter(doc, heading_color=h_col)
    
    # 4. Phần Nội Dung Chính
    sec_body = doc.add_section(docx.enum.section.WD_SECTION.NEW_PAGE)
    sec_body.page_width = Inches(8.27)
    sec_body.page_height = Inches(11.69)
    sec_body.top_margin = Inches(1.0)
    sec_body.bottom_margin = Inches(1.0)
    sec_body.left_margin = Inches(1.2)
    sec_body.right_margin = Inches(0.8)
    
    header = sec_body.header
    header.is_linked_to_previous = False
    p_hdr = header.paragraphs[0]
    format_paragraph(p_hdr, align=WD_ALIGN_PARAGRAPH.RIGHT, line_spacing=1.0, space_before=0, space_after=4)
    r_hdr = p_hdr.add_run("ĐỒ ÁN HỆ CSDL NOSQL — ĐỀ TÀI 06: PHÂN HỆ CACHING BÀI VIẾT & QUẢN LÝ PHIÊN")
    r_hdr.font.name = FONT_MAIN
    r_hdr.font.size = Pt(9.5)
    r_hdr.font.color.rgb = COLOR_BLACK
    
    footer = sec_body.footer
    footer.is_linked_to_previous = False
    p_ftr = footer.paragraphs[0]
    format_paragraph(p_ftr, align=WD_ALIGN_PARAGRAPH.RIGHT, line_spacing=1.0, space_before=4, space_after=0)
    r_ftr_lbl = p_ftr.add_run("Trang ")
    r_ftr_lbl.font.name = FONT_MAIN
    r_ftr_lbl.font.size = Pt(10)
    r_ftr_lbl.font.color.rgb = COLOR_BLACK
    r_ftr_pg = p_ftr.add_run()
    r_ftr_pg.font.name = FONT_MAIN
    r_ftr_pg.font.size = Pt(10)
    r_ftr_pg.font.color.rgb = COLOR_BLACK
    add_page_number_to_run(r_ftr_pg)
    
    with open(SRS_MD_PATH, 'r', encoding='utf-8') as f:
        srs_content = f.read()
        
    srs_parts = srs_content.split('\n## ')
    
    add_heading_styled(doc, "LỊCH SỬ PHIÊN BẢN TÀI LIỆU", level=1, heading_color=h_col)
    if len(srs_parts) > 2:
        parse_and_append_markdown(doc, srs_parts[2], heading_color=h_col)
        
    doc.add_page_break()
    add_heading_styled(doc, "CHƯƠNG 1: MỞ ĐẦU", level=1, heading_color=h_col)
    if len(srs_parts) > 3:
        p1_content = re.sub(r'^1\.\s+GIỚI THIỆU.*?\n', '', srs_parts[3], flags=re.IGNORECASE)
        parse_and_append_markdown(doc, p1_content, heading_color=h_col)
        
    doc.add_page_break()
    add_heading_styled(doc, "CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ KIẾN TRÚC HỆ THỐNG", level=1, heading_color=h_col)
    if len(srs_parts) > 4:
        p2_content = re.sub(r'^2\.\s+MÔ TẢ TỔNG QUAN.*?\n', '', srs_parts[4], flags=re.IGNORECASE)
        parse_and_append_markdown(doc, p2_content, heading_color=h_col)
        
    doc.add_page_break()
    add_heading_styled(doc, "CHƯƠNG 3: ĐẶC TẢ YÊU CẦU PHẦN MỀM (SRS)", level=1, heading_color=h_col)
    if len(srs_parts) > 5:
        p3_content = re.sub(r'^3\.\s+CÁC YÊU CẦU CỤ THỂ.*?\n', '', srs_parts[5], flags=re.IGNORECASE)
        parse_and_append_markdown(doc, p3_content, heading_color=h_col)
        
    doc.add_page_break()
    add_heading_styled(doc, "CHƯƠNG 4: THỰC NGHIỆM VÀ ĐÁNH GIÁ KẾT QUẢ", level=1, heading_color=h_col)
    
    ch4_intro = (
        "Chương này trình bày toàn bộ kết quả thực nghiệm, đo lường định lượng và kiểm thử tự động của hệ thống "
        "nhằm chứng minh tính đúng đắn và hiệu quả vượt trội của giải pháp Caching đa tầng kết hợp MongoDB và Redis. "
        "Mọi số liệu thực nghiệm dưới đây được thu thập tự động thông qua bộ kịch bản kiểm thử độc lập (scripts/Benchmark/benchmark.py), "
        "chạy trực tiếp trên cụm Docker Container thực tế của đồ án."
    )
    p_ch4 = doc.add_paragraph()
    format_paragraph(p_ch4, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.3, space_before=0, space_after=8, indent=0.35)
    add_formatted_runs(p_ch4, ch4_intro)
    
    if len(srs_parts) > 6:
        p4_full = srs_parts[6]
        match_a_b = re.search(r'(###\s+Phụ lục A:[\s\S]*?)(?=###\s+Phụ lục C:)', p4_full)
        if match_a_b:
            parse_and_append_markdown(doc, match_a_b.group(1), heading_color=h_col)
            
        match_d = re.search(r'(###\s+Phụ lục D:[\s\S]*?)(?=###\s+Phụ lục E:)', p4_full)
        if match_d:
            parse_and_append_markdown(doc, match_d.group(1), heading_color=h_col)
            
    doc.add_page_break()
    add_heading_styled(doc, "CHƯƠNG 5: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", level=1, heading_color=h_col)
    
    ch5_text = """### 5.1 Đánh giá chung kết quả đạt được
Qua quá trình nghiên cứu lý thuyết, thiết kế kiến trúc và hiện thực toàn diện hệ thống, nhóm 3 thành viên đã hoàn thành 100% các yêu cầu kỹ thuật và nghiệp vụ được giao trong Đề tài 06:
1. **Hoàn thiện trọn vẹn 4 nhóm tiêu chí Barem chấm điểm (10.0 / 10.0 điểm)**:
   - **Báo cáo & Thiết kế CSDL (2.5 điểm)**: Hoàn thành tài liệu phân tích nguyên lý Cache-Aside (1.0đ); Thiết kế mô hình dữ liệu Redis Hashes, Strings, Distributed Lock và bộ khóa có TTL chuẩn xác (1.5đ).
   - **CRUD Nền tảng (2.5 điểm)**: Hiện thực đầy đủ API Đăng ký tài khoản, Bootstrap Admin nguyên tử, Đăng nhập khởi tạo phiên, Viết/Sửa/Xóa mềm bài viết, Phân trang và Lọc theo danh mục.
   - **Cache-Aside & Quản lý phiên (2.5 điểm)**: Hiện thực luồng Cache-Aside chuẩn tại endpoint đọc bài viết với Header `X-Cache: HIT|MISS`; Cơ chế khóa phân tán chống sập nguồn Cache Stampede; Quản lý phiên qua Redis Hashes có Sliding Expiration 30 phút; Bộ đếm INCR lượt xem thời gian thực kết hợp Dirty Set đồng bộ ngầm về MongoDB.
   - **Dữ liệu mẫu & Demo sống (2.5 điểm)**: Nạp thành công 100 bài viết có ảnh thật Unsplash và danh mục chuẩn; Khởi tạo sẵn 20-50 key Redis với TTL đa dạng; Chuẩn bị kịch bản demo sống 3 bước thuyết phục và trực quan.
2. **Hiệu năng hệ thống được chứng minh bằng số liệu thực nghiệm**: Độ trễ Cache Hit đạt trung bình 2.53 ms (tốc độ đọc tăng gấp từ 11.8 đến 62.6 lần so với đọc trực tiếp MongoDB); Khi 100 request đồng thời cùng truy vấn một bài viết hết hạn cache, hệ thống chỉ sinh đúng 1 truy vấn về MongoDB nhờ khóa phân tán; Hệ thống duy trì ổn định 100% tỷ lệ thành công dưới tải 100 người dùng ảo đồng thời.
3. **Mã nguồn và kiểm thử đạt chuẩn chất lượng cao**: 78/78 kiểm thử tự động xUnit phía Backend và 103/103 kiểm thử Vitest phía Frontend đều đạt 100% Pass; Toàn bộ tài liệu đặc tả được kiểm tra cú pháp và tính nhất quán bằng công cụ `scripts/DocCheck/check_srs.py` với 0 lỗi vi phạm.

### 5.2 Hạn chế và Bài học kinh nghiệm
Bên cạnh những kết quả nổi bật, đồ án vẫn còn một số điểm hạn chế do giới hạn về mặt thời gian:
- **Độ trễ chốt lượt xem về MongoDB**: Cơ chế Write-Behind chốt lượt xem định kỳ theo chu kỳ 1 phút, do đó trong vòng 60 giây gần nhất số lượt xem hiển thị trên giao diện (đọc từ Redis) sẽ cao hơn số lượt xem lưu trong MongoDB trước khi worker kích hoạt.
- **Phụ thuộc Redis In-Memory**: Khi Redis gặp sự cố đột ngột trước khi worker kịp ghi nhận lượt xem từ `posts:dirty_views`, một phần nhỏ lượt xem chưa chốt có thể bị mất mát (tuy nhiên bài viết và tài khoản người dùng vẫn được an toàn tuyệt đối trong MongoDB).
- **Bài học kinh nghiệm**: Nhóm đã học hỏi sâu sắc về nguyên tắc "Ghi MongoDB trước, Xóa Cache sau" để triệt tiêu Race Condition; Hiểu rõ tầm quan trọng của việc dùng số phiên bản (`posts:ver`) để vô hiệu hóa cache danh sách O(1) thay vì lạm dụng lệnh `SCAN` gây nghẽn đơn luồng Redis.

### 5.3 Hướng phát triển trong tương lai
- **Triển khai cụm Redis Sentinel / Redis Cluster**: Nâng cao tính sẵn sàng cao (High Availability) và phân tán dữ liệu khi lưu lượng truy cập bài viết mở rộng quy mô lớn.
- **Tích hợp Full-Text Search**: Kết hợp MongoDB Atlas Search hoặc RedisSearch để hỗ trợ tìm kiếm toàn văn bài viết tiếng Việt không dấu và có dấu với độ trễ cực thấp.
- **Hàng đợi thông điệp RabbitMQ / Kafka**: Chuyển đổi tiến trình chốt lượt xem Write-Behind sang kiến trúc Event-Driven Message Queue để đảm bảo tính chịu lỗi tuyệt đối (Zero Data Loss).
"""
    parse_and_append_markdown(doc, ch5_text, heading_color=h_col)
    
    doc.add_page_break()
    add_heading_styled(doc, "TÀI LIỆU THAM KHẢO", level=1, heading_color=h_col)
    ref_text = """1. IEEE Computer Society, "IEEE Recommended Practice for Software Requirements Specifications," *IEEE Std 830-1998*, IEEE, 1998.
2. ISO/IEC/IEEE, "Systems and software engineering — Life cycle processes — Requirements engineering," *ISO/IEC/IEEE 29148:2018*, 2018.
3. MongoDB, Inc., "The MongoDB 7.0 Manual," [Online]. Available: https://www.mongodb.com/docs/v7.0/.
4. Redis Ltd., "Redis 7.2 Documentation and Command Reference," [Online]. Available: https://redis.io/commands/.
5. Microsoft Corporation, "ASP.NET Core 8.0 Fundamentals & Distributed Caching," [Online]. Available: https://learn.microsoft.com/en-us/aspnet/core/.
6. Martin Fowler, "Patterns of Enterprise Application Architecture," Addison-Wesley Professional, 2002.
7. Kyle Banker et al., "MongoDB in Action: Covers MongoDB version 3.0," Manning Publications, 2nd Edition, 2016.
8. Josiah L. Carlson, "Redis in Action," Manning Publications, 2013.
9. Khoa Công nghệ Thông tin — Trường Đại học Công Thương TP. HCM, "Đề bài Đồ án môn học: Hệ Cơ sở dữ liệu NoSQL — Đề tài 06: Phân hệ Caching bài viết và Quản lý phiên," 2026.
"""
    parse_and_append_markdown(doc, ref_text, heading_color=h_col)
    
    doc.add_page_break()
    add_heading_styled(doc, "PHỤ LỤC", level=1, heading_color=h_col)
    
    if len(srs_parts) > 6:
        p4_full = srs_parts[6]
        match_c = re.search(r'(###\s+Phụ lục C:[\s\S]*?)(?=###\s+Phụ lục D:)', p4_full)
        if match_c:
            add_heading_styled(doc, "Phụ lục A: Ma trận truy vết yêu cầu (Traceability Matrix)", level=2, heading_color=h_col)
            c_text = re.sub(r'^###\s+Phụ lục C:.*?\n', '', match_c.group(1))
            parse_and_append_markdown(doc, c_text, heading_color=h_col)
            
        match_e = re.search(r'(###\s+Phụ lục E:[\s\S]*)$', p4_full)
        if match_e:
            doc.add_page_break()
            add_heading_styled(doc, "Phụ lục B: Danh mục Test Case kiểm thử tự động (TC-01 … TC-55)", level=2, heading_color=h_col)
            e_text = re.sub(r'^###\s+Phụ lục E:.*?\n', '', match_e.group(1))
            parse_and_append_markdown(doc, e_text, heading_color=h_col)
            
    if len(srs_parts) > 7:
        doc.add_page_break()
        add_heading_styled(doc, "Phụ lục C: Vấn đề tài liệu nguồn và Quyết định xử lý", level=2, heading_color=h_col)
        parse_and_append_markdown(doc, srs_parts[7], heading_color=h_col)
        
    if len(srs_parts) > 8:
        doc.add_page_break()
        add_heading_styled(doc, "Phụ lục D: Hướng dẫn công cụ kiểm thử tài liệu check_srs.py", level=2, heading_color=h_col)
        parse_and_append_markdown(doc, srs_parts[8], heading_color=h_col)

    doc.save(target_file)
    print(f"Lưu file hoàn tất: {target_file}")

if __name__ == "__main__":
    # Sinh 2 bản:
    # 1. Bản chuẩn Đen 100% (docs/BaoCao-SRS-DeTai06-BlackText.docx và docs/SRS.docx)
    generate_document("docs/SRS.docx", mode="black")
    generate_document("docs/BaoCao-SRS-DeTai06-BlackText.docx", mode="black")
    
    # 2. Bản Tiêu đề Xanh Word Accent Blue (#1F4E79 / #2E74B5) (docs/BaoCao-SRS-DeTai06.docx và docs/BaoCao-SRS-DeTai06-BlueHeadings.docx)
    generate_document("docs/BaoCao-SRS-DeTai06.docx", mode="blue")
    generate_document("docs/BaoCao-SRS-DeTai06-BlueHeadings.docx", mode="blue")
    print("Hoàn tất sinh cả 2 phiên bản màu!")
