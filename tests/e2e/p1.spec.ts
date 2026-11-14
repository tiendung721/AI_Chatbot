import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test("P1: tìm và phân trang kho, giữ lựa chọn bản nháp qua các trang", async ({ page }) => {
  await login(page);
  const profile = await (await page.request.get("/api/v1/auth/me")).json();
  const assistant = await (await page.request.get("/api/v1/admin/assistant")).json();
  const prefix = `P1-CATALOG-${Date.now()}`;
  for (let i = 0; i < 26; i++) {
    const response = await page.request.post("/api/v1/admin/knowledge/texts", {
      headers: { "X-CSRF-Token": profile.csrf_token, Origin: new URL(page.url()).origin },
      data: { title: `${prefix}-${i}`, body: `DỮ LIỆU GIẢ. Nội dung phân trang ${i}.` },
    });
    expect(response.status()).toBe(201);
  }
  await page.getByLabel("Tìm tài liệu", { exact: true }).fill(prefix);
  await expect(page.locator(".document-choice")).toHaveCount(20);
  const title = await page.locator(".document-choice strong").first().innerText();
  await page.locator(".document-choice").first().getByRole("checkbox").check();
  await page.getByRole("button", { name: "Trang sau", exact: true }).click();
  await expect(page.locator(".document-choice")).toHaveCount(6);
  await page.locator(".document-choice").first().getByRole("checkbox").check();
  await expect(page.getByText(`${assistant.config.knowledge_version_ids.length + 2} phiên bản đã chọn trên toàn bộ kho. Đổi trang không bỏ lựa chọn.`)).toBeVisible();
  await page.getByRole("button", { name: "Trang trước", exact: true }).click();
  await expect(page.locator(".document-choice").filter({ hasText: title }).getByRole("checkbox")).toBeChecked();
  await page.getByRole("button", { name: "Kho tri thức", exact: false }).click();
  await page.getByLabel("Tìm tài liệu", { exact: true }).fill(prefix);
  await expect(page.locator(".document-row")).toHaveCount(20);
  await page.getByRole("button", { name: "Trang sau", exact: true }).click();
  await expect(page.locator(".document-row")).toHaveCount(6);
  await page.screenshot({ path: ".local/evidence/p1-catalog.png", fullPage: true });
});

test("P1: metadata nguồn và so sánh phiên bản hiển thị trong kho", async ({ page }) => {
  await login(page);
  const profile = await (await page.request.get("/api/v1/auth/me")).json();
  const title = `P1-DIFF-${Date.now()}`;
  const firstResponse = await page.request.post("/api/v1/admin/knowledge/texts", {
    headers: { "X-CSRF-Token": profile.csrf_token, Origin: new URL(page.url()).origin },
    data: { title, body: "DỮ LIỆU GIẢ. Nội dung phiên bản cũ P1-OLD." },
  });
  expect(firstResponse.status()).toBe(201);
  const first = await firstResponse.json();
  const response = await page.request.post(`/api/v1/admin/knowledge/documents/${first.document_id}/versions`, {
    headers: { "X-CSRF-Token": profile.csrf_token, Origin: new URL(page.url()).origin },
    data: { title, body: "DỮ LIỆU GIẢ. Nội dung phiên bản mới P1-NEW." },
  });
  expect(response.status()).toBe(201);
  const current = await response.json();
  await page.getByRole("button", { name: "Kho tri thức", exact: false }).click();
  await page.getByLabel("Tìm tài liệu", { exact: true }).fill(title);
  await expect(page.locator(".document-row")).toHaveCount(2);
  await page.locator(".document-row").filter({ hasText: "V2" }).getByRole("button", { name: "Xem nội dung", exact: true }).click();
  await page.getByLabel("URL trang công bố").fill("https://congbao.chinhphu.vn/");
  await page.getByLabel("Nhãn chủ đề, phân cách bằng dấu phẩy").fill("Kiểm thử, Nguồn");
  await page.getByRole("combobox", { name: /Thay thế phiên bản/ }).selectOption(first.version_id);
  await page.getByRole("button", { name: "Lưu thông tin văn bản", exact: true }).click();
  await expect.poll(async () => (await (await page.request.get(`/api/v1/admin/knowledge/versions/${current.version_id}`)).json()).metadata_json.source_url).toBe("https://congbao.chinhphu.vn/");
  await page.getByLabel("So sánh với phiên bản", { exact: true }).selectOption(first.version_id);
  await expect(page.getByRole("region", { name: "Đối chiếu phiên bản", exact: true })).toContainText("P1-NEW");
  await expect(page.getByRole("region", { name: "Đối chiếu phiên bản", exact: true })).toContainText("P1-OLD");
  await page.screenshot({ path: ".local/evidence/p1-version-diff.png", fullPage: true });
});
