import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { login, ask, credentials } from "./helpers";

test("Admin A: nhập tri thức, Preview, publish, chat có nguồn và không lộ sang B", async ({
  page,
  context,
}) => {
  const a = await login(page);
  const marker = "MAY-BAC-" + randomBytes(3).toString("hex"),
    title = "Mây bạc kiểm thử " + marker;
  await page
    .getByRole("button", { name: "Kho tri thức", exact: false })
    .click();
  await page.getByLabel("Tiêu đề tài liệu").fill(title);
  await page
    .getByLabel("Nội dung văn bản")
    .fill(`DỮ LIỆU GIẢ. Mây bạc có mã xác minh thử nghiệm ${marker}.`);
  await page.getByRole("button", { name: "Lưu văn bản", exact: true }).click();
  const row = page.locator(".document-row").filter({ hasText: title });
  await expect(row).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await row.getByRole("button", { name: "Xác nhận công khai" }).click();
  await expect(
    row.getByText("Đã xác nhận công khai", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Cấu hình chatbot", exact: false })
    .click();
  await page
    .locator(".document-choice")
    .filter({ hasText: title })
    .getByRole("checkbox")
    .check();
  await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu bản nháp" })).toBeVisible();
  const preview = page.getByRole("region", { name: "Xem thử bản nháp" });
  await preview.getByLabel("Câu hỏi", { exact: true }).fill("Mây bạc");
  await preview.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await expect(preview.locator(".answer-text")).toContainText(marker, {
    timeout: 30000,
  });
  const publicPage = await context.newPage();
  await publicPage.goto(`/chat/${a.public_key}`);
  await ask(publicPage, "Mây bạc");
  await expect(publicPage.locator(".assistant-message").last()).toContainText(
    "Chưa tìm thấy nguồn",
  );
  await page
    .getByRole("button", { name: "Kiểm tra & xuất bản", exact: false })
    .click();
  await page.getByRole("button", { name: /Kiểm tra bản nháp/ }).click();
  await expect(page.locator(".check-list")).toBeVisible();
  await page
    .getByLabel("Lý do xuất bản")
    .fill("Xuất bản tri thức giả phục vụ kiểm thử E2E");
  await page.getByRole("button", { name: /Xuất bản nội dung/ }).click();
  await expect(page.getByRole("status")).toContainText("Đã xuất bản");
  await publicPage.reload();
  await ask(publicPage, "Mây bạc");
  await expect(publicPage.locator(".answer-text")).toContainText(marker);
  await publicPage.locator(".source-card").first().click();
  await expect(publicPage.getByRole("dialog")).toContainText(marker);
  await publicPage.getByRole("button", { name: "Đóng nguồn" }).click();
  await publicPage
    .getByRole("button", { name: "Hữu ích", exact: true })
    .click();
  await expect(publicPage.getByRole("status")).toContainText(
    "Đã ghi nhận đánh giá",
  );
  const b = Object.entries(credentials()).find(([k]) => k.endsWith("-b"))![1];
  const bPage = await context.newPage();
  await bPage.goto(`/chat/${b.public_key}`);
  await ask(bPage, "Mây bạc");
  await expect(bPage.locator(".assistant-message").last()).not.toContainText(
    marker,
  );
  mkdirSync(".local/evidence", { recursive: true });
  await page.screenshot({
    path: ".local/evidence/admin-published.png",
    fullPage: true,
  });
  await publicPage.screenshot({
    path: ".local/evidence/chat-with-source.png",
    fullPage: true,
  });
});
test("Admin API từ chối model injection, UI giữ tenant cố định", async ({
  page,
}) => {
  await login(page);
  const me = await (await page.request.get("/api/v1/auth/me")).json();
  const current = await (
    await page.request.get("/api/v1/admin/assistant")
  ).json();
  const response = await page.request.patch("/api/v1/admin/assistant/draft", {
    headers: {
      Origin: new URL(page.url()).origin,
      "X-CSRF-Token": me.csrf_token,
      "If-Match": `"${current.revision}"`,
    },
    data: { ...current.config, model: "must-not-echo" },
  });
  expect(response.status()).toBe(422);
  expect(await response.text()).not.toContain("must-not-echo");
  await expect(page.getByRole("combobox", { name: /model|provider|mô hình|nhà cung cấp|tenant|đơn vị|phường/i })).toHaveCount(0);
  await expect(page.getByText("Model Selection", { exact: true })).toHaveCount(
    0,
  );
});
test("Chat mobile không tràn ngang và mở được nguồn", async ({ page }) => {
  const a = Object.entries(credentials()).find(([k]) => k.endsWith("-a"))![1];
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/chat/${a.public_key}`);
  await ask(page, "Thủ tục minh họa");
  await expect(page.locator(".answer-text")).toContainText("LAM-A-482");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.locator(".source-card").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Đóng nguồn" }).click();
  mkdirSync(".local/evidence", { recursive: true });
  await page.screenshot({
    path: ".local/evidence/mobile-chat.png",
    fullPage: true,
  });
});

test("Widget cùng nguồn mở iframe và nhận câu trả lời có nguồn", async ({
  page,
}) => {
  const a = Object.entries(credentials()).find(([k]) => k.endsWith("-a"))![1];
  await page.goto("/");
  await page.evaluate((key) => {
    const script = document.createElement("script");
    script.src = `${window.location.origin}/widget.js`;
    script.dataset.assistant = key;
    document.body.append(script);
  }, a.public_key);
  await page.getByRole("button", { name: "Hỏi trợ lý", exact: true }).click();
  const frame = page.frameLocator('iframe[title="Trợ lý thông tin phường"]');
  await frame.getByLabel("Câu hỏi", { exact: true }).fill("Thủ tục minh họa");
  await frame.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await expect(frame.locator(".answer-text")).toContainText("LAM-A-482", {
    timeout: 30000,
  });
  await expect(frame.locator(".source-card")).toHaveCount(1);
  await page.getByRole("button", { name: "Đóng trợ lý", exact: true }).click();
  await expect(
    page.locator('iframe[title="Trợ lý thông tin phường"]'),
  ).toBeHidden();
});
