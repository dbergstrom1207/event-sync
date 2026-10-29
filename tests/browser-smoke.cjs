// Optional UI integration check. Requires Playwright and Chromium; app must be running.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || undefined,
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1280, height: 900 },
    });
    async function waitForCount(selector, count) {
      const deadline = Date.now() + 10000;
      while ((await page.locator(selector).count()) !== count) {
        if (Date.now() > deadline)
          throw new Error(`Timed out waiting for ${count} ${selector}`);
        await new Promise((resolve) => setTimeout(resolve, 50));
      }
    }
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(process.env.BASE_URL || "http://127.0.0.1:8000");
    await page.waitForSelector(".meeting");
    assert.equal(await page.locator(".meeting").count(), 29);
    assert.equal(await page.locator(".meeting-status").count(), 29);
    assert.ok(
      await page.evaluate(
        () => parseFloat(getComputedStyle(document.body).fontSize) >= 17,
      ),
    );
    assert.ok(
      await page.evaluate(
        () =>
          parseFloat(
            getComputedStyle(document.querySelector("#search")).fontSize,
          ) >= 17,
      ),
    );
    async function chooseFilter(label) {
      await page.locator("#filter-toggle").click();
      const trigger = await page.locator("#filter-toggle").boundingBox();
      const panel = await page.locator(".filter-options").boundingBox();
      assert.ok(
        panel.y > trigger.y + trigger.height,
        "The open list must not cover the button border",
      );
      await page
        .locator(".filter-options")
        .getByText(label, { exact: true })
        .click();
      assert.equal(
        await page.locator("#filter-menu").evaluate((menu) => menu.open),
        false,
      );
    }
    await chooseFilter("All meetings");
    await page.locator("#filter-toggle").focus();
    await page.keyboard.press("Enter");
    await page
      .getByRole("radio", { name: "All meetings", exact: true })
      .focus();
    await page.keyboard.press("ArrowDown");
    await waitForCount(".meeting", 14);
    assert.equal(
      await page.locator("#filter-label").textContent(),
      "Needs review",
    );
    await page.locator("#filter-toggle").click();
    await page.keyboard.press("Escape");
    assert.equal(
      await page.locator("#filter-menu").evaluate((menu) => menu.open),
      false,
    );
    await page.locator("#filter-toggle").click();
    await page.locator("h1").click();
    assert.equal(
      await page.locator("#filter-menu").evaluate((menu) => menu.open),
      false,
    );
    await chooseFilter("CRM");
    await waitForCount(".meeting", 20);
    await chooseFilter("Calendar");
    await waitForCount(".meeting", 22);
    await chooseFilter("All meetings");
    await waitForCount(".meeting", 29);
    const alignment = await page.evaluate(() => {
      const clients = [...document.querySelectorAll(".meeting-client")].map(
        (element) => element.getBoundingClientRect().x,
      );
      const statuses = [...document.querySelectorAll(".meeting-status")].map(
        (element) => element.getBoundingClientRect().x,
      );
      return {
        clients: Math.max(...clients) - Math.min(...clients),
        statuses: Math.max(...statuses) - Math.min(...statuses),
      };
    });
    assert.ok(
      alignment.clients <= 1 && alignment.statuses <= 1,
      "Client and status columns must align",
    );
    assert.ok(
      await page.evaluate(
        () =>
          parseFloat(
            getComputedStyle(document.querySelector(".totals strong")).fontSize,
          ) >
          parseFloat(
            getComputedStyle(document.querySelector(".totals")).fontSize,
          ),
      ),
    );
    await page.locator(".meeting > summary").first().click();
    assert.ok(
      await page
        .getByText("Reconciliation decision", { exact: true })
        .first()
        .isVisible(),
    );
    assert.equal(await page.locator("table").first().isVisible(), false);
    await page.locator(".field-details > summary").first().click();
    assert.ok(await page.locator("table").first().isVisible());
    await page.locator(".observations > summary").first().click();
    assert.ok(
      await page
        .getByText("Prefer calendar; fall back to other source", {
          exact: true,
        })
        .first()
        .isVisible(),
    );
    await chooseFilter("Conflicting values");
    await waitForCount(".meeting", 13);
    await page.fill("#search", "CRM-1002");
    await waitForCount(".meeting", 1);
    await page.locator(".meeting > summary").click();
    await page.locator(".field-details > summary").click();
    assert.ok(
      await page
        .locator("td")
        .filter({ hasText: "Zoom - https://zoom.us/j/98765432100" })
        .first()
        .isVisible(),
    );
    await page.locator(".raw > summary").click();
    assert.equal(await page.locator(".raw pre").count(), 2);
    await page.fill("#search", "no-such-meeting");
    await page.waitForSelector(".empty");
    await page.fill("#search", "");
    await chooseFilter("All meetings");
    await waitForCount(".meeting", 29);
    // Candidate navigation clears filters and opens the requested related record.
    await page.fill("#search", "CAL-A5");
    await waitForCount(".meeting", 1);
    await page.locator(".meeting > summary").click();
    await page
      .getByRole("button", { name: "Inspect CAL-A6", exact: true })
      .click();
    await waitForCount(".meeting", 29);
    assert.ok(
      await page
        .locator(".meeting[open] h2")
        .filter({ hasText: "Pinnacle Group - Q1 Update" })
        .isVisible(),
    );
    // Hostile source text must be rendered as text, never executed as markup.
    await page.route("**/api/meetings?*", async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      body.meetings[0].fields.title.value =
        '<img src=x onerror="window.pwned=true">';
      await route.fulfill({ json: body });
    });
    await page.click("#refresh");
    await page
      .getByRole("heading", {
        name: '<img src=x onerror="window.pwned=true">',
        exact: true,
      })
      .waitFor();
    assert.equal(await page.locator("img").count(), 0);
    assert.equal(await page.evaluate(() => window.pwned), undefined);
    await page.unroute("**/api/meetings?*");
    await page.click("#refresh");
    await page
      .getByRole("heading", {
        name: "Q1 Portfolio Review - Meridian Capital",
        exact: true,
      })
      .waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    );
    await page.locator(".meeting > summary").first().click();
    await page.locator(".field-details > summary").first().click();
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    );
    await page.setViewportSize({ width: 320, height: 700 });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    );
    await page.locator("#filter-toggle").click();
    const mobilePanel = await page.locator(".filter-options").boundingBox();
    assert.ok(mobilePanel.x >= 0 && mobilePanel.x + mobilePanel.width <= 320);
    await page.keyboard.press("Escape");
    if (process.env.SCREENSHOT)
      await page.screenshot({ path: process.env.SCREENSHOT, fullPage: true });
    await page.route("**/api/meetings?*", (route) =>
      route.fulfill({ status: 500, body: "error" }),
    );
    await page.click("#refresh");
    await page.getByText(/Unable to load meetings/).waitFor();
    assert.equal(await page.locator(".meeting").count(), 0);
    assert.deepEqual(errors, []);
    console.log(
      "Browser checks passed: list, details, provenance, filters, search, raw records, XSS, mobile width, error state.",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
