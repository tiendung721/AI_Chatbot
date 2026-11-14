import { expect, test } from "@playwright/test";
import { randomBytes } from "node:crypto";
import { mkdirSync } from "node:fs";
import { ask, login } from "./helpers";

test("Upload CSV qua scanner/worker, Preview có vị trí dòng và phiên bản file mới", async ({
  page,
}) => {
  await login(page);
  const suffix = randomBytes(4).toString("hex"),
    name = `sen-${suffix}.csv`,
    marker = `SEN-${suffix}`;
  await page
    .getByRole("button", { name: "Kho tri thức", exact: false })
    .click();
  await page.getByLabel("Tải tài liệu tri thức").setInputFiles({
    name,
    mimeType: "text/csv",
    buffer: Buffer.from(`Thủ tục,Mã\nSen tím,${marker}\nHoa mai,MAI-739`),
  });
  const row = page.locator(".document-row").filter({ hasText: name });
  await expect(row.getByText("Sẵn sàng", { exact: true })).toBeVisible({
    timeout: 90000,
  });
  await row.getByRole("button", { name: "Xem nội dung", exact: true }).click();
  const extraction = page.getByRole("region", {
    name: "Kiểm tra bản trích xuất",
  });
  await expect(extraction).toContainText("Dòng 1–3");
  await expect(extraction.getByLabel("Nội dung phần 1", { exact: true })).toHaveValue(new RegExp(marker));
  await extraction
    .getByLabel("Số văn bản", { exact: true })
    .fill("FIXTURE-482");
  await extraction
    .getByRole("button", { name: "Lưu thông tin văn bản" })
    .click();
  await expect(extraction.getByRole("status")).toContainText("Đã lưu metadata");
  page.once("dialog", (d) => d.accept());
  await row.getByRole("button", { name: "Xác nhận công khai" }).click();
  await expect(row).toContainText("Đã xác nhận công khai");
  await page
    .getByRole("button", { name: "Cấu hình chatbot", exact: false })
    .click();
  await page
    .locator(".document-choice")
    .filter({ hasText: name })
    .getByRole("checkbox")
    .check();
  await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản nháp" })).toBeVisible();
  const preview = page.getByRole("region", { name: "Xem thử bản nháp" });
  await ask(preview, "Sen tím");
  await expect(preview.locator(".answer-text")).toContainText(marker);
  const citation = preview.locator(".source-card").filter({ hasText: name });
  await expect(citation).toContainText("Dòng 1–3");
  await citation.click();
  await expect(page.getByRole("dialog")).toContainText(marker);
  await page.getByRole("dialog").getByRole("button", { name: /Đóng/ }).click();
  await page
    .getByRole("button", { name: "Kho tri thức", exact: false })
    .click();
  await row.getByRole("button", { name: "Thêm phiên bản file" }).click();
  await page.getByLabel("Tải tài liệu tri thức").setInputFiles({
    name,
    mimeType: "text/csv",
    buffer: Buffer.from("Thủ tục,Mã\nSen tím,NEW-VERSION"),
  });
  const second = page
    .locator(".document-row")
    .filter({ hasText: name })
    .filter({ hasText: "V2" });
  await expect(second).toContainText("Sẵn sàng", { timeout: 90000 });
  await expect(
    second.getByRole("button", { name: "Xác nhận công khai" }),
  ).toBeVisible();
  mkdirSync(".local/evidence", { recursive: true });
  await page.screenshot({
    path: ".local/evidence/m2-upload-version.png",
    fullPage: true,
  });
});

test("Excel: cảnh báo công thức, sheet ẩn không mặc định chọn; duyệt và purge thật", async ({
  page,
}) => {
  await login(page);
  const name = `review-${randomBytes(4).toString("hex")}.xlsx`;
  const fs = await import("node:fs");
  await page
    .getByRole("button", { name: "Kho tri thức", exact: false })
    .click();
  await page.getByLabel("Tải tài liệu tri thức").setInputFiles({
    name,
    mimeType:
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: fs.readFileSync(".local/e2e-files/review.xlsx"),
  });
  const row = page.locator(".document-row").filter({ hasText: name });
  await expect(row).toContainText("Cần kiểm tra nội dung", { timeout: 90000 });
  await expect(
    row.getByRole("button", { name: "Xác nhận công khai" }),
  ).toHaveCount(0);
  await row.getByRole("button", { name: "Xem nội dung" }).click();
  const panel = page.getByRole("region", { name: "Kiểm tra bản trích xuất" });
  await expect(panel).toContainText("formula_cache_missing:C2");
  const hidden = panel.locator("details").filter({ hasText: "Sheet Nội bộ" });
  await hidden.locator("summary").click();
  await expect(hidden.getByRole("checkbox")).not.toBeChecked();
  await expect(hidden.getByRole("textbox")).toBeDisabled();
  await panel
    .getByLabel("Tôi đã kiểm tra cảnh báo và nội dung được chọn.")
    .check();
  mkdirSync(".local/evidence", { recursive: true });
  await page.screenshot({
    path: ".local/evidence/m2-extraction-review.png",
    fullPage: true,
  });
  await panel
    .getByRole("button", { name: "Duyệt nội dung và lập chỉ mục" })
    .click();
  await expect(row).toContainText("Sẵn sàng");
  page.once("dialog", (d) => d.accept("Xóa fixture E2E M2"));
  await row.getByRole("button", { name: "Xóa dữ liệu", exact: true }).click();
  await expect(
    page.getByText(
      "Đã xóa file và nội dung dẫn xuất khỏi kho đang hoạt động.",
      { exact: true },
    ),
  ).toBeVisible({ timeout: 90000 });
  await expect(
    page.locator(".document-row").filter({ hasText: name }),
  ).toHaveCount(0);
});
