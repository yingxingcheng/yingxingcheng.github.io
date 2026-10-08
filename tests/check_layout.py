#!/usr/bin/env python3
"""Run deterministic browser layout checks separately from the unit tests.

Install with ``pip install playwright`` and ``playwright install chromium``,
then run ``python tests/check_layout.py`` from any working directory.
Screenshots and a JSON report are written to .layout-checks/ by default.
"""

import argparse
import json
import re
from itertools import combinations
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (360, 768, 860, 1165, 1440)
HEIGHT = 900
EPSILON = 1


def overlaps(first, second):
    return (
        first["x"] + first["width"] > second["x"] + EPSILON
        and second["x"] + second["width"] > first["x"] + EPSILON
        and first["y"] + first["height"] > second["y"] + EPSILON
        and second["y"] + second["height"] > first["y"] + EPSILON
    )


def check_layout(page, width):
    measurements = page.evaluate(
        """() => {
            const rect = element => {
                const {x, y, width, height} = element.getBoundingClientRect();
                return {x, y, width, height};
            };
            return {
                viewportWidth: window.innerWidth,
                documentWidth: document.documentElement.scrollWidth,
                bodyWidth: document.body.scrollWidth,
                navigation: Array.from(document.querySelectorAll('nav a')).map(link => {
                    const range = document.createRange();
                    range.selectNodeContents(link);
                    const lines = Array.from(range.getClientRects())
                        .filter(box => box.width > 0 && box.height > 0);
                    return {
                        text: link.textContent,
                        href: link.getAttribute('href'),
                        lines: lines.length,
                        ...rect(link)
                    };
                }),
                intro: Object.fromEntries(['details', 'contact-info', 'contact-imag']
                    .map(name => [name, rect(document.querySelector('.intro .' + name))])),
                imageLoaded: document.querySelector('.contact-imag img').naturalWidth > 0
            };
        }"""
    )
    assert measurements["viewportWidth"] == width, measurements
    assert measurements["documentWidth"] <= width + EPSILON, measurements
    assert measurements["bodyWidth"] <= width + EPSILON, measurements
    assert measurements["imageLoaded"], "Profile image did not load"
    navigation = measurements["navigation"]
    assert len(navigation) == 8, f"Expected eight navigation links, got {navigation}"
    for link in navigation:
        assert link["lines"] == 1, f"Navigation label wraps: {link}"
        assert link["width"] > 0 and link["height"] > 0, f"Hidden navigation link: {link}"
        assert link["x"] >= -EPSILON, f"Navigation link clipped on the left: {link}"
        assert link["x"] + link["width"] <= width + EPSILON, f"Link clipped on right: {link}"
        assert link["y"] >= -EPSILON, f"Navigation link clipped above viewport: {link}"
        assert link["y"] + link["height"] <= HEIGHT + EPSILON, f"Link below viewport: {link}"

    for (first_name, first), (second_name, second) in combinations(
        measurements["intro"].items(), 2
    ):
        assert not overlaps(
            first, second
        ), f"Intro overlap between {first_name} {first} and {second_name} {second}"
    return measurements


def check_navigation(page, alternate, alternate_language):
    links = page.locator("nav a")
    hrefs = links.evaluate_all("links => links.map(link => link.getAttribute('href'))")
    assert len(hrefs) == 8, hrefs
    for index, href in enumerate(hrefs):
        if href.startswith("#"):
            target = page.locator(href)
            assert target.count() == 1, f"Missing or duplicated navigation target {href}"
            links.nth(index).click()
            assert urlsplit(page.url).fragment == href[1:], f"Navigation failed: {href}"
            box = target.bounding_box()
            assert (
                box and box["y"] < HEIGHT and box["y"] + box["height"] > 0
            ), f"Navigation target is outside the viewport: {href}, {box}"
        else:
            assert href == alternate.name, f"Unexpected language destination: {href}"
            with page.expect_navigation(wait_until="load"):
                links.nth(index).click()
            assert page.url == alternate.as_uri(), f"Language switch failed: {page.url}"
            assert page.locator("html").get_attribute("lang") == alternate_language


def check_page(browser, filename, language, width, output):
    alternate_name = "index-zh.html" if language == "en" else "index.html"
    alternate_language = "zh" if language == "en" else "en"
    context = browser.new_context(viewport={"width": width, "height": HEIGHT})
    # Static layout must work without external scripts or icon-font CDNs.
    # Local file resources (our stylesheet and profile image) still load.
    context.route(re.compile(r"^https?://"), lambda route: route.abort())
    page = context.new_page()
    page.set_default_timeout(10000)
    result = {"language": language, "width": width, "page": filename}
    try:
        page.goto((ROOT / filename).as_uri(), wait_until="load")
        page.screenshot(path=str(output / f"{language}-{width}.png"))
        result["measurements"] = check_layout(page, width)
        check_navigation(page, ROOT / alternate_name, alternate_language)
        result["passed"] = True
    except Exception as error:
        result["passed"] = False
        result["error"] = str(error)
    finally:
        context.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".layout-checks")
    parser.add_argument("--browser-executable", help="Optional installed Chromium executable")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as playwright:
        options = {"headless": True}
        if args.browser_executable:
            options["executable_path"] = args.browser_executable
        browser = playwright.chromium.launch(**options)
        try:
            for language, filename in (("en", "index.html"), ("zh", "index-zh.html")):
                for width in WIDTHS:
                    result = check_page(browser, filename, language, width, args.output_dir)
                    results.append(result)
                    status = "PASS" if result["passed"] else "FAIL"
                    print(f"{status}: {filename} at {width}px", flush=True)
                    if not result["passed"]:
                        print(result["error"], flush=True)
        finally:
            browser.close()
    (args.output_dir / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if any(not result["passed"] for result in results):
        raise SystemExit(1)
    print(f"All {len(results)} layout checks passed. Screenshots: {args.output_dir}")


if __name__ == "__main__":
    main()
