#!/usr/bin/env python3
"""
Sales Pipeline PDF Report Generator — AI Sales Team for Claude Code

Generates a professional, multi-page PDF sales pipeline report with score gauges,
bar charts, prospect cards, pipeline summary tables, and prioritized action plans.

Usage:
    python3 generate_pdf_report.py <json_data_file> [output_pdf_file]
    python3 generate_pdf_report.py  # generates a sample report in demo mode
"""

import json
import math
import sys
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Circle, String, Line, Rect, Wedge
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics import renderPDF

# --- Color Palette (Sales-focused) ---
PRIMARY = colors.HexColor("#1B2A4A")       # dark navy
ACCENT = colors.HexColor("#0EA5E9")        # sales blue
HIGHLIGHT = colors.HexColor("#F59E0B")     # amber/gold for scores
SUCCESS = colors.HexColor("#10B981")       # green
WARNING = colors.HexColor("#F59E0B")       # amber
DANGER = colors.HexColor("#EF4444")        # red
LIGHT_BG = colors.HexColor("#F0F9FF")      # light blue tint
BODY_TEXT = colors.HexColor("#1E293B")
SECONDARY_TEXT = colors.HexColor("#64748B")
BORDER = colors.HexColor("#CBD5E1")
WHITE = colors.white
GRADE_A_BG = colors.HexColor("#ECFDF5")
GRADE_B_BG = colors.HexColor("#EFF6FF")
GRADE_C_BG = colors.HexColor("#FFFBEB")
GRADE_D_BG = colors.HexColor("#FEF2F2")


def score_color(score):
    """Return color based on score value."""
    if score >= 80:
        return SUCCESS
    elif score >= 60:
        return ACCENT
    elif score >= 40:
        return WARNING
    else:
        return DANGER


def grade_color(grade):
    """Return color based on letter grade."""
    grade_map = {"A": SUCCESS, "B": ACCENT, "C": WARNING, "D": DANGER}
    return grade_map.get(grade, SECONDARY_TEXT)


def grade_bg(grade):
    """Return background color for grade."""
    bg_map = {"A": GRADE_A_BG, "B": GRADE_B_BG, "C": GRADE_C_BG, "D": GRADE_D_BG}
    return bg_map.get(grade, LIGHT_BG)


def build_styles():
    """Build all paragraph styles for the report."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CoverTitle",
        fontName="Helvetica-Bold",
        fontSize=28,
        textColor=PRIMARY,
        alignment=TA_LEFT,
        spaceAfter=6,
        leading=34,
    ))
    styles.add(ParagraphStyle(
        name="CoverSubtitle",
        fontName="Helvetica",
        fontSize=14,
        textColor=SECONDARY_TEXT,
        alignment=TA_LEFT,
        spaceAfter=4,
        leading=18,
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=PRIMARY,
        spaceBefore=12,
        spaceAfter=10,
        leading=26,
    ))
    styles.add(ParagraphStyle(
        name="SubSection",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=6,
        leading=17,
    ))
    styles.add(ParagraphStyle(
        name="BodyText2",
        fontName="Helvetica",
        fontSize=10,
        textColor=BODY_TEXT,
        spaceAfter=6,
        leading=14,
    ))
    styles.add(ParagraphStyle(
        name="SmallText",
        fontName="Helvetica",
        fontSize=8,
        textColor=SECONDARY_TEXT,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=9,
        textColor=BODY_TEXT,
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=WHITE,
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name="ActionItem",
        fontName="Helvetica",
        fontSize=10,
        textColor=BODY_TEXT,
        leftIndent=20,
        spaceAfter=4,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        name="ProspectName",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=PRIMARY,
        spaceAfter=2,
        leading=15,
    ))
    styles.add(ParagraphStyle(
        name="ProspectDetail",
        fontName="Helvetica",
        fontSize=9,
        textColor=BODY_TEXT,
        leading=12,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="FooterText",
        fontName="Helvetica",
        fontSize=7,
        textColor=SECONDARY_TEXT,
        alignment=TA_CENTER,
    ))
    return styles


def draw_score_gauge(score, size=180):
    """Draw a circular score gauge with colored ring and score number in center."""
    d = Drawing(size, size + 20)
    cx, cy = size / 2, size / 2 + 10
    radius = size / 2 - 10

    # Background circle (track)
    d.add(Circle(cx, cy, radius, fillColor=LIGHT_BG, strokeColor=BORDER, strokeWidth=2))

    # Score arc
    col = score_color(score)
    angle_extent = (score / 100) * 360
    if angle_extent > 0:
        d.add(Wedge(cx, cy, radius, 90, 90 - angle_extent,
                     fillColor=col, strokeColor=col, strokeWidth=0))

    # Inner white circle to create donut effect
    inner_r = radius * 0.65
    d.add(Circle(cx, cy, inner_r, fillColor=WHITE, strokeColor=WHITE, strokeWidth=0))

    # Score number
    d.add(String(cx, cy + 8, str(score),
                 fontSize=36, fontName="Helvetica-Bold",
                 fillColor=PRIMARY, textAnchor="middle"))
    d.add(String(cx, cy - 12, "Pipeline Score",
                 fontSize=9, fontName="Helvetica",
                 fillColor=SECONDARY_TEXT, textAnchor="middle"))

    # Grade label
    if score >= 75:
        grade = "A"
    elif score >= 50:
        grade = "B"
    elif score >= 25:
        grade = "C"
    else:
        grade = "D"

    d.add(String(cx, cy - 30, f"Grade: {grade}",
                 fontSize=12, fontName="Helvetica-Bold",
                 fillColor=col, textAnchor="middle"))

    return d


def create_bar_chart(categories, width=480, height=200):
    """Draw a horizontal bar chart for category scores."""
    d = Drawing(width, height)

    names = list(categories.keys())
    scores = [categories[n]["score"] for n in names]

    chart = HorizontalBarChart()
    chart.x = 160
    chart.y = 10
    chart.width = width - 180
    chart.height = height - 20
    chart.data = [scores]
    chart.categoryAxis.categoryNames = names
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fillColor = BODY_TEXT
    chart.categoryAxis.visibleGrid = False
    chart.categoryAxis.visibleAxis = False
    chart.categoryAxis.visibleTicks = False

    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 20
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = SECONDARY_TEXT
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.gridStrokeColor = BORDER
    chart.valueAxis.gridStrokeWidth = 0.5
    chart.valueAxis.visibleAxis = False
    chart.valueAxis.visibleTicks = False

    chart.bars[0].fillColor = ACCENT
    chart.barWidth = 14
    chart.barSpacing = 6

    # Color each bar by score
    bar_colors = [score_color(s) for s in scores]
    for i, col in enumerate(bar_colors):
        chart.bars[(0, i)].fillColor = col

    d.add(chart)

    # Add score labels at end of each bar
    bar_total_height = len(names) * (chart.barWidth + chart.barSpacing)
    start_y = chart.y + (chart.height - bar_total_height) / 2
    for i, s in enumerate(scores):
        bar_y = start_y + i * (chart.barWidth + chart.barSpacing) + chart.barWidth / 2
        bar_end_x = chart.x + (s / 100) * chart.width + 4
        d.add(String(bar_end_x, bar_y - 3, str(s),
                     fontSize=8, fontName="Helvetica-Bold",
                     fillColor=score_color(s), textAnchor="start"))

    return d


def add_header_footer(canvas, doc, report_title=""):
    """Add header and footer to each page."""
    canvas.saveState()
    # Header line
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(2)
    canvas.line(54, letter[1] - 40, letter[0] - 54, letter[1] - 40)

    # Header text
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(PRIMARY)
    canvas.drawString(54, letter[1] - 35, f"Sales Pipeline Report — {report_title}")

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SECONDARY_TEXT)
    canvas.drawRightString(letter[0] - 54, letter[1] - 35, f"Page {doc.page}")

    # Footer line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(54, 40, letter[0] - 54, 40)

    # Footer text
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(SECONDARY_TEXT)
    canvas.drawCentredString(letter[0] / 2, 28,
                              "Generated by AI Sales Team for Claude Code")
    canvas.restoreState()


def generate_report(data, output_path):
    """Generate the full PDF report from data dict."""
    styles = build_styles()
    report_date = data.get("date", "")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    story = []

    # ==================== PAGE 1: COVER ====================
    story.append(Spacer(1, 1.2 * inch))
    story.append(Paragraph("Sales Pipeline Report", styles["CoverTitle"]))
    story.append(Spacer(1, 40))
    story.append(Paragraph(f"<b>{report_date}</b>", styles["CoverSubtitle"]))

    pipeline_health = data.get("pipeline_health", {})
    total_prospects = pipeline_health.get("total_prospects", 0)
    if total_prospects:
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"{total_prospects} Prospects Analyzed", styles["CoverSubtitle"]))
    story.append(Spacer(1, 60))

    # Overall pipeline score gauge
    overall_score = data.get("overall_pipeline_score", 0)
    gauge = draw_score_gauge(overall_score)
    story.append(gauge)
    story.append(Spacer(1, 40))

    # Executive Summary
    summary = data.get("executive_summary", "")
    if summary:
        story.append(Paragraph("Executive Summary", styles["SubSection"]))
        story.append(Paragraph(summary, styles["BodyText2"]))

    story.append(PageBreak())

    # ==================== PAGE 2: SCORE BREAKDOWN ====================
    story.append(Paragraph("Score Breakdown", styles["SectionTitle"]))
    story.append(Spacer(1, 6))

    categories = data.get("categories", {})
    if categories:
        chart = create_bar_chart(categories)
        story.append(chart)
        story.append(Spacer(1, 16))

        # Score comparison table
        header = [
            Paragraph("<b>Category</b>", styles["TableHeader"]),
            Paragraph("<b>Score</b>", styles["TableHeader"]),
            Paragraph("<b>Status</b>", styles["TableHeader"]),
        ]
        table_data = [header]

        for cat_name, cat_info in categories.items():
            s = cat_info.get("score", 0)
            col = score_color(s)
            hex_col = col.hexval() if hasattr(col, 'hexval') else str(col)
            if s >= 80:
                label = "Strong"
            elif s >= 60:
                label = "Good"
            elif s >= 40:
                label = "Needs Work"
            else:
                label = "Critical"

            table_data.append([
                Paragraph(cat_name, styles["TableCell"]),
                Paragraph(f"<b>{s}/100</b>", styles["TableCell"]),
                Paragraph(f'<font color="{hex_col}"><b>{label}</b></font>', styles["TableCell"]),
            ])

        # Overall row
        overall_col = score_color(overall_score)
        hex_overall = overall_col.hexval() if hasattr(overall_col, 'hexval') else str(overall_col)
        table_data.append([
            Paragraph("<b>OVERALL PIPELINE</b>", styles["TableCell"]),
            Paragraph(f"<b>{overall_score}/100</b>", styles["TableCell"]),
            Paragraph(f'<font color="{hex_overall}"><b>Pipeline Score</b></font>', styles["TableCell"]),
        ])

        col_widths = [200, 100, 100]
        t = Table(table_data, colWidths=col_widths)
        t_style = [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("BACKGROUND", (0, -1), (-1, -1), LIGHT_BG),
        ]
        for i in range(1, len(table_data) - 1):
            if i % 2 == 0:
                t_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BG))
        t.setStyle(TableStyle(t_style))
        story.append(t)

    story.append(PageBreak())

    # ==================== PAGE 3: TOP PROSPECTS ====================
    prospects = data.get("prospects", [])
    if prospects:
        story.append(Paragraph("Top Prospects", styles["SectionTitle"]))
        story.append(Spacer(1, 6))

        # Show top 5 as detailed cards
        for i, prospect in enumerate(prospects[:5]):
            name = prospect.get("name", "Unknown")
            p_score = prospect.get("score", 0)
            p_grade = prospect.get("grade", "?")
            stage = prospect.get("stage", "Unknown")
            url = prospect.get("url", "")
            next_action = prospect.get("next_action", "")

            col = score_color(p_score)
            hex_col = col.hexval() if hasattr(col, 'hexval') else str(col)
            g_col = grade_color(p_grade)
            hex_g = g_col.hexval() if hasattr(g_col, 'hexval') else str(g_col)

            # Prospect card as a mini table
            card_data = [
                [
                    Paragraph(f'<b>{i+1}. {name}</b>', styles["ProspectName"]),
                    Paragraph(f'<font color="{hex_col}" size="14"><b>{p_score}</b></font>', styles["TableCell"]),
                    Paragraph(f'<font color="{hex_g}" size="12"><b>{p_grade}</b></font>', styles["TableCell"]),
                ],
                [
                    Paragraph(f'Stage: <b>{stage}</b> &nbsp;&nbsp; {url}', styles["ProspectDetail"]),
                    Paragraph("Score", styles["SmallText"]),
                    Paragraph("Grade", styles["SmallText"]),
                ],
            ]
            if next_action:
                card_data.append([
                    Paragraph(f'Next: <i>{next_action}</i>', styles["ProspectDetail"]),
                    Paragraph("", styles["SmallText"]),
                    Paragraph("", styles["SmallText"]),
                ])

            card = Table(card_data, colWidths=[340, 50, 50])
            card_style = [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("SPAN", (0, -1), (-1, -1)) if next_action else ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), grade_bg(p_grade)),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
            card.setStyle(TableStyle(card_style))
            story.append(KeepTogether([card, Spacer(1, 8)]))

    story.append(PageBreak())

    # ==================== PAGE 4: PIPELINE SUMMARY ====================
    if prospects:
        story.append(Paragraph("Pipeline Summary", styles["SectionTitle"]))
        story.append(Spacer(1, 6))

        header = [
            Paragraph("<b>Company</b>", styles["TableHeader"]),
            Paragraph("<b>Score</b>", styles["TableHeader"]),
            Paragraph("<b>Grade</b>", styles["TableHeader"]),
            Paragraph("<b>Stage</b>", styles["TableHeader"]),
            Paragraph("<b>Next Action</b>", styles["TableHeader"]),
        ]
        table_data = [header]

        for prospect in prospects:
            p_score = prospect.get("score", 0)
            p_grade = prospect.get("grade", "?")
            col = score_color(p_score)
            hex_col = col.hexval() if hasattr(col, 'hexval') else str(col)
            g_col = grade_color(p_grade)
            hex_g = g_col.hexval() if hasattr(g_col, 'hexval') else str(g_col)

            table_data.append([
                Paragraph(prospect.get("name", ""), styles["TableCell"]),
                Paragraph(f'<font color="{hex_col}"><b>{p_score}</b></font>', styles["TableCell"]),
                Paragraph(f'<font color="{hex_g}"><b>{p_grade}</b></font>', styles["TableCell"]),
                Paragraph(prospect.get("stage", ""), styles["TableCell"]),
                Paragraph(prospect.get("next_action", ""), styles["TableCell"]),
            ])

        col_widths = [110, 45, 40, 80, 225]
        t = Table(table_data, colWidths=col_widths)
        t_style = [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ALIGN", (1, 0), (2, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ]
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                t_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BG))
        t.setStyle(TableStyle(t_style))
        story.append(t)

        # Pipeline health summary
        if pipeline_health:
            story.append(Spacer(1, 16))
            story.append(Paragraph("Pipeline Health", styles["SubSection"]))

            health_data = [
                [
                    Paragraph("<b>Total Prospects</b>", styles["TableCell"]),
                    Paragraph("<b>Avg Score</b>", styles["TableCell"]),
                    Paragraph("<b>A-Grade</b>", styles["TableCell"]),
                    Paragraph("<b>B-Grade</b>", styles["TableCell"]),
                    Paragraph("<b>C-Grade</b>", styles["TableCell"]),
                    Paragraph("<b>D-Grade</b>", styles["TableCell"]),
                ],
                [
                    Paragraph(str(pipeline_health.get("total_prospects", 0)), styles["TableCell"]),
                    Paragraph(str(pipeline_health.get("avg_score", 0)), styles["TableCell"]),
                    Paragraph(str(pipeline_health.get("a_grade", 0)), styles["TableCell"]),
                    Paragraph(str(pipeline_health.get("b_grade", 0)), styles["TableCell"]),
                    Paragraph(str(pipeline_health.get("c_grade", 0)), styles["TableCell"]),
                    Paragraph(str(pipeline_health.get("d_grade", 0)), styles["TableCell"]),
                ],
            ]
            ht = Table(health_data, colWidths=[83, 83, 83, 83, 83, 83])
            ht_style = [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ]
            ht.setStyle(TableStyle(ht_style))
            story.append(ht)

    story.append(PageBreak())

    # ==================== PAGE 5: ACTION PLAN ====================
    story.append(Paragraph("Action Plan", styles["SectionTitle"]))
    story.append(Spacer(1, 8))

    action_items = data.get("action_items", {})

    # Quick Wins
    quick_wins = action_items.get("quick_wins", [])
    if quick_wins:
        story.append(Paragraph("Quick Wins (Immediate)", styles["SubSection"]))
        for i, item in enumerate(quick_wins, 1):
            col_hex = SUCCESS.hexval() if hasattr(SUCCESS, 'hexval') else str(SUCCESS)
            story.append(Paragraph(
                f'<font color="{col_hex}"><b>{i}.</b></font> {item}', styles["ActionItem"]
            ))
        story.append(Spacer(1, 12))

    # This Week
    this_week = action_items.get("this_week", [])
    if this_week:
        story.append(Paragraph("This Week", styles["SubSection"]))
        for i, item in enumerate(this_week, 1):
            col_hex = ACCENT.hexval() if hasattr(ACCENT, 'hexval') else str(ACCENT)
            story.append(Paragraph(
                f'<font color="{col_hex}"><b>{i}.</b></font> {item}', styles["ActionItem"]
            ))
        story.append(Spacer(1, 12))

    # This Month
    this_month = action_items.get("this_month", [])
    if this_month:
        story.append(Paragraph("This Month", styles["SubSection"]))
        for i, item in enumerate(this_month, 1):
            col_hex = WARNING.hexval() if hasattr(WARNING, 'hexval') else str(WARNING)
            story.append(Paragraph(
                f'<font color="{col_hex}"><b>{i}.</b></font> {item}', styles["ActionItem"]
            ))

    story.append(PageBreak())

    # ==================== PAGE 6: METHODOLOGY ====================
    story.append(Paragraph("Scoring Methodology", styles["SectionTitle"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "This sales pipeline report uses a BANT + MEDDIC scoring framework to evaluate and rank "
        "prospects. Each prospect is scored 0-100 based on four BANT dimensions (Budget, Authority, "
        "Need, Timeline), each weighted equally at 25 points. MEDDIC completeness is assessed "
        "as a supplementary qualification metric across six dimensions.",
        styles["BodyText2"]
    ))
    story.append(Spacer(1, 10))

    # Methodology table
    method_header = [
        Paragraph("<b>Dimension</b>", styles["TableHeader"]),
        Paragraph("<b>Weight</b>", styles["TableHeader"]),
        Paragraph("<b>Signals Measured</b>", styles["TableHeader"]),
    ]
    method_data = [method_header]

    method_rows = [
        ("Budget", "25 pts", "Funding amount, employee count, pricing visibility, tech spend indicators, enterprise tool usage"),
        ("Authority", "25 pts", "Decision makers identified, C-suite contacts found, org chart completeness, buying committee mapped"),
        ("Need", "25 pts", "Pain points detected, relevant job postings, review complaints, competitor dissatisfaction signals"),
        ("Timeline", "25 pts", "Active hiring for relevant roles, recent funding events, contract renewal timing, urgency mentions"),
    ]

    for dim, weight, desc in method_rows:
        method_data.append([
            Paragraph(f"<b>{dim}</b>", styles["TableCell"]),
            Paragraph(weight, styles["TableCell"]),
            Paragraph(desc, styles["TableCell"]),
        ])

    t = Table(method_data, colWidths=[100, 60, 340])
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
    ]
    for i in range(1, len(method_data)):
        if i % 2 == 0:
            t_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BG))
    t.setStyle(TableStyle(t_style))
    story.append(t)

    story.append(Spacer(1, 16))

    # Grade scale
    story.append(Paragraph("Grade Scale", styles["SubSection"]))

    grade_header = [
        Paragraph("<b>Score Range</b>", styles["TableHeader"]),
        Paragraph("<b>Grade</b>", styles["TableHeader"]),
        Paragraph("<b>Interpretation</b>", styles["TableHeader"]),
        Paragraph("<b>Recommended Action</b>", styles["TableHeader"]),
    ]
    grade_data = [grade_header]
    grade_rows = [
        ("75-100", "A", "High-value prospect", "Schedule discovery call immediately"),
        ("50-74", "B", "Promising prospect", "Nurture with targeted content"),
        ("25-49", "C", "Needs development", "Research and multi-thread outreach"),
        ("0-24", "D", "Low priority", "Add to long-term nurture sequence"),
    ]
    for score_range, grade, interp, action in grade_rows:
        g_col = grade_color(grade)
        hex_g = g_col.hexval() if hasattr(g_col, 'hexval') else str(g_col)
        grade_data.append([
            Paragraph(score_range, styles["TableCell"]),
            Paragraph(f'<font color="{hex_g}"><b>{grade}</b></font>', styles["TableCell"]),
            Paragraph(interp, styles["TableCell"]),
            Paragraph(action, styles["TableCell"]),
        ])

    t = Table(grade_data, colWidths=[80, 50, 130, 240])
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ALIGN", (0, 0), (1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
    ]
    t.setStyle(TableStyle(t_style))
    story.append(t)

    # Build PDF
    doc.build(
        story,
        onFirstPage=lambda c, d: add_header_footer(c, d, report_date),
        onLaterPages=lambda c, d: add_header_footer(c, d, report_date),
    )

    return output_path


def main():
    if len(sys.argv) < 2:
        # Demo mode — generate sample report with realistic fake data
        sample_data = {
            "date": "March 6, 2026",
            "overall_pipeline_score": 72,
            "executive_summary": (
                "Our pipeline shows strong momentum with 12 active prospects across multiple stages. "
                "Three A-grade prospects are ready for immediate engagement, while five B-grade "
                "prospects show strong potential with targeted nurturing. Key areas for improvement "
                "include deepening contact access and strengthening competitive positioning intelligence."
            ),
            "prospects": [
                {"name": "TechFlow Inc", "url": "https://techflow.io", "score": 92, "grade": "A", "stage": "Discovery Call", "next_action": "Schedule demo with VP Engineering"},
                {"name": "DataBridge Corp", "url": "https://databridge.com", "score": 85, "grade": "A", "stage": "Qualified", "next_action": "Send proposal with 3-tier pricing"},
                {"name": "CloudScale AI", "url": "https://cloudscale.ai", "score": 78, "grade": "A", "stage": "Engaged", "next_action": "Connect with CTO via warm intro"},
                {"name": "FinanceHub Pro", "url": "https://financehub.pro", "score": 71, "grade": "B", "stage": "Researching", "next_action": "Send cold outreach sequence"},
                {"name": "RetailEdge", "url": "https://retailedge.com", "score": 68, "grade": "B", "stage": "Nurturing", "next_action": "Share case study from similar company"},
                {"name": "SecureNet Labs", "url": "https://securenet.io", "score": 65, "grade": "B", "stage": "Qualified", "next_action": "Prepare meeting brief for next call"},
                {"name": "EduPlatform", "url": "https://eduplatform.co", "score": 62, "grade": "B", "stage": "Engaged", "next_action": "Follow up on pricing discussion"},
                {"name": "GreenEnergy AI", "url": "https://greenenergy.ai", "score": 58, "grade": "B", "stage": "Researching", "next_action": "Identify decision makers"},
                {"name": "MediaStack", "url": "https://mediastack.io", "score": 45, "grade": "C", "stage": "Initial Research", "next_action": "Complete prospect analysis"},
                {"name": "LogiTrack", "url": "https://logitrack.com", "score": 42, "grade": "C", "stage": "Cold", "next_action": "Research company and find contacts"},
                {"name": "HealthFirst", "url": "https://healthfirst.com", "score": 38, "grade": "C", "stage": "Cold", "next_action": "Validate ICP fit before outreach"},
                {"name": "BuildCo Tools", "url": "https://buildco.tools", "score": 22, "grade": "D", "stage": "Unqualified", "next_action": "Add to long-term nurture list"},
            ],
            "categories": {
                "Company Fit": {"score": 75},
                "Contact Access": {"score": 68},
                "Need Alignment": {"score": 82},
                "Budget Signals": {"score": 70},
                "Timeline Signals": {"score": 58},
                "Competitive Position": {"score": 63},
            },
            "action_items": {
                "quick_wins": [
                    "Send personalized outreach to TechFlow VP Engineering (A-grade, ready for demo)",
                    "Prepare and send 3-tier proposal to DataBridge Corp",
                    "Request warm intro to CloudScale CTO via mutual connection",
                ],
                "this_week": [
                    "Launch cold outreach sequence for FinanceHub Pro",
                    "Create tailored case study for RetailEdge (retail vertical)",
                    "Complete meeting prep brief for SecureNet Labs call",
                    "Map decision-making committee at EduPlatform",
                ],
                "this_month": [
                    "Run full prospect analysis on MediaStack and LogiTrack",
                    "Build competitive battle cards for top 3 competitors",
                    "Develop vertical-specific value props for Healthcare and Education",
                    "Review and refresh ICP based on pipeline learnings",
                    "Establish referral network for warm introductions",
                ],
            },
            "pipeline_health": {
                "total_prospects": 12,
                "avg_score": 65,
                "a_grade": 3,
                "b_grade": 5,
                "c_grade": 3,
                "d_grade": 1,
            },
        }
        output = "SALES-REPORT-sample.pdf"
        generate_report(sample_data, output)
        print(f"Sample report generated: {output}")
        return

    json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "SALES-REPORT.pdf"

    with open(json_path, "r") as f:
        data = json.load(f)

    generate_report(data, output_path)
    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    main()
