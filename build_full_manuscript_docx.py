from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from build_sections_docx import add_page_number, parse_markdown, set_default_font


ROOT = Path(__file__).resolve().parent
EARLY_SOURCE = ROOT / "sections_1_3_title_abstract_introduction_literature_review.md"
LATER_SOURCE = ROOT / "sections_4_5_6_methodology_results_discussion.md"
OUTPUT = ROOT / "basket_aware_inventory_full_manuscript_sections_1_to_10.docx"


def build() -> None:
    doc = Document()
    set_default_font(doc)
    section = doc.sections[0]
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.70)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)
    section.header_distance = Inches(0.3)
    section.footer_distance = Inches(0.35)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.space_before = Pt(0)
    footer.paragraph_format.space_after = Pt(0)
    run = footer.add_run("Basket Aware Inventory Research | Full Manuscript Sections 1 to 10 | Page ")
    run.font.name = "Arial"
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(100, 100, 100)
    add_page_number(footer)

    title = doc.add_paragraph(style="Title")
    title.add_run("Basket Aware Inventory Research")
    subtitle = doc.add_paragraph(style="Subtitle")
    subtitle.add_run("Full Manuscript Sections 1 to 10")
    intro = doc.add_paragraph()
    intro.add_run("Scope. ").bold = True
    intro.add_run(
        "This manuscript integrates the completed evidence-based Sections 1 to 3 with "
        "the methodology, executed results, discussion, implications, limitations, "
        "conclusion, references, and appendices. Forecast and inventory-policy outcomes "
        "are reported with their simulation boundary, matched-baseline comparison, "
        "placebo test, and robustness analyses."
    )
    doc.add_paragraph()

    parse_markdown(doc, EARLY_SOURCE.read_text(encoding="utf-8"))
    parse_markdown(doc, LATER_SOURCE.read_text(encoding="utf-8"))

    doc.core_properties.title = "Basket Aware Inventory Research Full Manuscript Sections 1 to 10"
    doc.core_properties.subject = "Complete evidence-bounded manuscript for basket-aware inventory research"
    doc.core_properties.author = "Research Project"
    doc.core_properties.comments = "Prepared from the project research data package and literature review."
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
