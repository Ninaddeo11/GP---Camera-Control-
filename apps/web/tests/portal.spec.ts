import { test, expect } from "@playwright/test";

import { coordinates, registryDiagnostics } from "../lib/camera-registry";

import type { CameraOut } from "../lib/types";

// Synthetic edge cases are isolated to tests. Production always requests /cameras.

const cameras: CameraOut[] = Array.from({ length: 30 }, (_, i) => ({
  id: `record-${i}`,
  camera_id: `cam${i + 1}`,
  name: `Test camera ${i + 1}`,
  department: i % 2 ? "Traffic" : "Security",
  jurisdiction_id: "region",
  lat: 22.3,
  lon: 70.8,
  protocol: "rtsp",
  resolution: "1920x1080",
  codec: "h264",
  fps: 25,
  status: i === 0 ? "offline" : i === 1 ? "reconnecting" : "live",
  is_active: true,
  updated_at: "2026-09-28T00:00:00Z",
}));

async function setup(page: import("@playwright/test").Page, dataset = cameras) {
  await page.addInitScript(() =>
    localStorage.setItem("sentinelgrid.access_token", "browser-test-only"),
  );

  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;

    let data: unknown = [];

    if (path.endsWith("/auth/me"))
      data = {
        id: "test",
        username: "tester",
        full_name: "Test Operator",
        role_code: "T1",
        role_name: "State Command",
        department: "Traffic",
        permissions: [
          "camera:read",
          "vehicle_trace:read",
          "watchlist:read",
          "audit_log:read",
        ],
        jurisdictions: [
          {
            id: "region",
            name: "Test Region",
            code: "TEST",
            scope_type: "state",
          },
        ],
      };
    else if (path.endsWith("/cameras")) data = dataset;
    else if (path.includes("/tracking/plate/"))
      data = {
        plate_text: "TEST",
        stops: [],
        omitted_out_of_jurisdiction_stops: 0,
      };

    await route.fulfill({ json: data });
  });

  await page.routeWebSocket("**/alerts/stream*", () => {});
}

test("coordinate validation and diagnostics preserve data integrity", () => {
  expect(coordinates("22.3", "70.8")).toEqual([22.3, 70.8]);

  for (const [lat, lon] of [
    [null, 1],
    [1, null],
    ["", 1],
    ["  ", 1],
    [91, 0],
    [0, 181],
    [Infinity, 0],
    [true, 1],
    ["oops", 1],
  ])
    expect(coordinates(lat, lon)).toBeNull();

  expect(coordinates(0, 0)).toEqual([0, 0]);

  expect(registryDiagnostics(cameras)).toMatchObject({
    total: 30,
    valid: 30,
    unavailable: 0,
    entities: 30,
    duplicateCoordinates: 29,
    duplicateIds: 0,
  });

  expect(registryDiagnostics([cameras[0]!, cameras[0]!])).toMatchObject({
    total: 2,
    duplicateIds: 1,
    entities: 2,
  });
});

test("30 coincident entities cluster, filter and select in both directions", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (message) => {
    if (
      /Warning:|Each child in a list|hydration|React does not recognize/.test(
        message.text(),
      )
    )
      errors.push(message.text());
  });

  await setup(page);
  await page.goto("/registry", { waitUntil: "domcontentloaded" });

  await expect(
    page.getByText("30 camera entities represented", { exact: false }),
  ).toBeVisible();

  await expect(page.locator(".camera-cluster")).toHaveText("30");

  const originalMap = await page
    .locator(".leaflet-container")
    .evaluate((el) => {
      el.setAttribute("data-lifecycle-test", "stable");
      return true;
    });

  expect(originalMap).toBe(true);

  await page.getByLabel("Search cameras", { exact: true }).fill("cam18");

  await expect(
    page.getByText("1 camera entities represented", { exact: false }),
  ).toBeVisible();

  await expect(page.locator(".leaflet-popup")).toContainText("cam18");

  await expect(page.locator(".leaflet-container")).toHaveAttribute(
    "data-lifecycle-test",
    "stable",
  );

  await page.getByRole("button", { name: "Clear filters" }).click();

  await page.getByLabel("Status", { exact: true }).selectOption("offline");

  await expect(
    page.getByText("1 camera entities represented", { exact: false }),
  ).toBeVisible();

  await page.locator(".camera-marker").click();

  await expect(
    page.locator('[aria-label="Camera results"] button[aria-pressed="true"]'),
  ).toContainText("cam1");

  await page.getByRole("button", { name: "Clear filters" }).click();

  await page.getByLabel("Department", { exact: true }).selectOption("Traffic");

  await expect(
    page.getByText("15 camera entities represented", { exact: false }),
  ).toBeVisible();

  await page.getByLabel("Location", { exact: true }).selectOption("region");

  await page.getByRole("button", { name: "Fit All Cameras" }).click();

  await page.getByLabel("Sort by").selectOption("id");

  await page.getByRole("button", { name: "Clear filters" }).click();

  await page
    .locator('[aria-label="Camera results"] button')
    .filter({ hasText: "Test camera 18" })
    .click();

  await expect(page.locator(".leaflet-popup")).toContainText("cam18");

  expect(errors).toEqual([]);
});

test("missing locations, no matches, and API failures are explicit", async ({
  page,
}) => {
  await setup(page, [
    { ...cameras[0]!, lat: null },
    { ...cameras[1]!, lon: 200 },
  ]);

  await page.goto("/registry", { waitUntil: "domcontentloaded" });

  await expect(
    page.getByText("0 camera entities represented · 2 locations unavailable"),
  ).toBeVisible();

  await expect(page.locator(".camera-marker")).toHaveCount(0);

  await page
    .getByLabel("Location", { exact: true })
    .selectOption("unavailable");

  await page.locator('[aria-label="Camera results"] button').first().click();

  await expect(
    page.getByText("Camera location unavailable.", { exact: true }),
  ).toBeVisible();

  await page
    .getByLabel("Search cameras", { exact: true })
    .fill("does-not-exist");

  await expect(page.getByText("No cameras match your filters.")).toBeVisible();

  await page.route("**/api/cameras", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Service unavailable", code: "unavailable" },
    }),
  );

  await page.reload({ waitUntil: "domcontentloaded" });

  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "Unable to load camera registry" }),
  ).toContainText("Unable to load camera registry");
});

test("all portal and public routes render; mobile navigation and map fit", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (message) => {
    if (
      /Warning:|Each child in a list|hydration|React does not recognize/.test(
        message.text(),
      )
    )
      errors.push(message.text());
  });

  await setup(page, []);

  for (const [path, title] of [
    ["/video-wall", "Video Wall"],
    ["/trace", "Vehicle Trace"],
    ["/watchlist", "Watchlist & Alerts"],
    ["/audit", "Audit Log"],
  ] as const) {
    await page.goto(path, { waitUntil: "domcontentloaded" });
    await expect(
      page.getByRole("heading", { name: title, exact: true }),
    ).toBeVisible();

    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }

  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/video-wall", "/trace", "/watchlist", "/audit"]) {
    await page.goto(path, { waitUntil: "domcontentloaded" });
    await expect(page.locator("main h1")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }

  await page.goto("/registry", { waitUntil: "domcontentloaded" });
  await expect(page.locator(".leaflet-container")).toBeVisible();

  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);

  await page.getByRole("button", { name: "Open navigation" }).click();

  await page.getByRole("link", { name: "Audit Log", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Audit Log" })).toBeVisible();

  for (const path of [
    "/",
    "/login",
    "/forgot-password",
    "/reset-password",
    "/request-access",
  ]) {
    await page.goto(path, { waitUntil: "domcontentloaded" });
    await expect(page.locator("h1").first()).toBeVisible();
  }

  expect(errors).toEqual([]);
});

test("audit filters operate on loaded records and preserve verification", async ({ page }) => {
  await setup(page, []);
  await page.route("**/api/admin/audit-log?*", route => route.fulfill({json:[
    {id:"a",ts:"2026-09-27T12:00:00Z",username:"operator-a",action:"camera.read",resource_type:"camera",resource_id:"cam1",outcome:"allow",reason:"",ip_address:"127.0.0.1",request_path:"/cameras"},
    {id:"b",ts:"2026-09-28T12:00:00Z",username:"operator-b",action:"trace.read",resource_type:"vehicle",resource_id:"test",outcome:"deny",reason:"Scope denied",ip_address:"127.0.0.1",request_path:"/tracking"}
  ]}));
  await page.route("**/api/admin/audit-log/verify", route => route.fulfill({json:{intact:true,row_count:2}}));
  await page.goto("/audit",{waitUntil:"domcontentloaded"});
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await page.getByLabel("Search audit entries").fill("operator-b");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByLabel("Search audit entries").fill("");
  await page.getByRole("combobox").filter({has:page.locator('option[value="deny"]')}).selectOption("deny");
  await expect(page.locator("tbody")).toContainText("Scope denied");
  await page.getByLabel("From",{exact:true}).fill("2026-09-29");
  await expect(page.getByText("No audit entries match this view.")).toBeVisible();
  await page.getByRole("button",{name:"Verify chain integrity"}).click();
  await expect(page.getByText("Chain intact",{exact:false})).toBeVisible();
});

test("mobile camera detail sheet and video expansion support keyboard dismissal", async ({ page }) => {
  await setup(page,[cameras[0]!]);
  // Exercise playback error UI without creating a stream on a live gateway.
  await page.route("**/api/webrtc?*", route => route.fulfill({status:503,body:"Stream unavailable in browser test"}));
  await page.setViewportSize({width:390,height:844});
  await page.goto("/registry",{waitUntil:"domcontentloaded"});
  await page.locator('[aria-label="Camera results"] button').click();
  await expect(page.getByLabel("Selected camera details")).toBeVisible();
  await page.getByRole("button",{name:"Close camera details"}).click();
  await expect(page.getByLabel("Selected camera details")).toHaveCount(0);
  await page.goto("/video-wall?camera=cam1",{waitUntil:"domcontentloaded"});
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByLabel("Search video cameras").fill("missing");
  await expect(page.getByText("No cameras match this view.")).toBeVisible();
});
