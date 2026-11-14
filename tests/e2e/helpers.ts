import { expect, type Locator, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { randomBytes } from "node:crypto";
type Credential = { email: string; password: string; public_key: string };
export function credentials(): Record<string, Credential> {
  return JSON.parse(readFileSync(".local/e2e-admins.json", "utf8"));
}
export async function login(page: Page) {
  const all = credentials(),
    key = Object.keys(all).find((k) => k.endsWith("-a"))!,
    a = all[key];
  await page.goto("/admin");
  await page.getByLabel("Email", { exact: true }).fill(a.email);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(a.password);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: /Đổi mật khẩu lần đầu|Cấu hình chatbot/,
    }),
  ).toBeVisible();
  if (
    await page
      .getByRole("heading", { name: "Đổi mật khẩu lần đầu" })
      .isVisible()
  ) {
    await page
      .getByLabel("Mật khẩu được cấp", { exact: true })
      .fill(a.password);
    const password = randomBytes(22).toString("hex");
    await page.getByLabel("Mật khẩu mới", { exact: false }).fill(password);
    await page.getByRole("button", { name: "Lưu mật khẩu mới" }).click();
    all[key].password = password;
    writeFileSync(".local/e2e-admins.json", JSON.stringify(all, null, 2));
  }
  await expect(
    page.getByRole("heading", { name: "Cấu hình chatbot", exact: true }),
  ).toBeVisible();
  return a;
}
export async function ask(page: Page | Locator, question: string) {
  await page.getByLabel("Câu hỏi", { exact: true }).fill(question);
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await expect(
    page.getByRole("button", { name: "Gửi câu hỏi" }),
  ).toBeDisabled();
  await expect(page.getByLabel("Câu hỏi", { exact: true })).toBeEnabled({
    timeout: 30000,
  });
}
