export type Locator = Record<string, unknown>;
export function locationLabel(
  locator?: Locator | null,
  section?: number,
): string {
  if (locator?.kind === "pdf_page")
    return `Trang ${locator.page_start}${locator.page_end !== locator.page_start ? `–${locator.page_end}` : ""}`;
  if (locator?.kind === "xlsx_cells")
    return `Sheet ${locator.sheet} · ${locator.cell_range}`;
  if (locator?.kind === "pptx_slide") return `Slide ${locator.slide}`;
  if (locator?.kind === "docx_section")
    return `${locator.section}${locator.table ? ` · Bảng ${locator.table}` : ""}`;
  if (locator?.kind === "csv_rows")
    return `Dòng ${locator.row_start}–${locator.row_end}`;
  if (locator?.kind === "image_ocr") return "Ảnh · nội dung OCR";
  return `Mục ${locator?.section ?? section ?? 1}`;
}
