#!/usr/bin/env python

import json
from datetime import date


def _nav(sections, lang):
    other_lang = "index-zh" if lang == "en" else "index"
    other_label = "中文" if lang == "en" else "English"
    items = [
        ("education", sections["education"]["title"]),
        ("experience", sections["experience"]["title"]),
        ("publications", sections["publications"]["title"]),
        ("software", sections["software"]["title"]),
        ("skills", sections["skills"]["title"]),
        ("awards", sections["awards"]["title"]),
        ("references", sections["references"]["title"]),
    ]
    links = "".join(f'<li><a href="#{sid}">{label}</a></li>' for sid, label in items)
    links += f'<li><a href="{other_lang}.html">{other_label}</a></li>'
    return f"<ul>{links}</ul>"


def _intro(info, lang):
    ci = info["contact_info"]
    orcid_url = f"https://orcid.org/{ci['orcid']}"
    position_line = f'<h2 class="position">{info["position"]}</h2>'
    affiliation_line = f'<p class="affiliation">{info["affiliation"]}</p>'
    return f"""
        <section id="intro" class="intro">
            <div class="details">
                <h1>{info["name"]}</h1>
                {position_line}
                {affiliation_line}
            </div>
            <div class="contact-info">
                <p><i class="fab fa-orcid"></i>
                <a href="{orcid_url}">{ci['orcid']}</a></p>
                <p><i class="fab fa-github"></i>
                <a href="{ci['github']}">@yingxingcheng</a></p>
                <p><i class="fas fa-envelope"></i>
                <a href="mailto:{ci['email']}">{ci['email']}</a></p>
            </div>
            <div class="contact-imag">
                <img src="{ci['image']}" alt="{info['name']}" width="150">
            </div>
        </section>
        <section id="quote" class="quote">
            <p>{info["quote"]}</p>
        </section>"""


def _education(section):
    rows = ""
    for item in section["items"]:
        gpa = f" (GPA: {item['gpa']})" if "gpa" in item else ""
        rows += f"<p><strong>{item['period']}:</strong> {item['degree']}, {item['institution']}{gpa}</p>"
    return f'<section id="education" class="section education"><h2>{section["title"]}</h2>{rows}</section>'


def _experience(section):
    items = ""
    for item in section["items"]:
        items += f"""<div class="research-item">
                <h3>{item['period']}</h3>
                <p><strong>{item['title']}</strong></p>
                <p>{item['description']}</p>
            </div>"""
    return f'<section id="experience" class="section experience"><h2>{section["title"]}</h2>{items}</section>'


def _publications(section):
    items = ""
    for idx, item in enumerate(section["items"]):
        citation = (
            f'<strong>[{idx+1}] {item["authors"]}.</strong> '
            f'{item["title"]}. <em>{item["journal"]}</em> {item["volume"]}, {item["pages"]} '
            f'({item["year"]}). <a href="{item["link"]}">{item["link"]}</a>'
        )
        items += f"<p>{citation}</p>"
    return f'<section id="publications" class="section publications"><h2>{section["title"]}</h2>{items}</section>'


def _software(section):
    items = ""
    for item in section["items"]:
        items += (
            f'<p><strong>{item["title"]}</strong>, {item["description"]} '
            f'<a href="{item["link"]}">More</a></p>'
        )
    return f'<section id="software" class="section software"><h2>{section["title"]}</h2>{items}</section>'


def _skills(section):
    items = "".join(
        f'<p><strong>{item["category"]}:</strong> {item["skills"]}</p>'
        for item in section["items"]
    )
    return f'<section id="skills" class="section skills"><h2>{section["title"]}</h2>{items}</section>'


def _awards(section):
    items = "".join(
        f'<p><strong>{item["year"]}:</strong> {item["award"]}, {item["institution"]}</p>'
        for item in section["items"]
    )
    return f'<section id="awards" class="section awards"><h2>{section["title"]}</h2>{items}</section>'


def _references(section):
    items = "".join(
        f'<p><strong>{item["name"]}</strong>, {item["institution"]}. '
        f'<a href="mailto:{item["email"]}">{item["email"]}</a></p>'
        for item in section["items"]
    )
    return f'<section id="references" class="section references"><h2>{section["title"]}</h2>{items}</section>'


def generate_html(data, filename):
    lang = data["lang"]
    title = data["title"]
    s = data["sections"]
    intro = s["intro"]
    year = date.today().year

    description = intro["quote"]

    body = (
        _intro(intro, lang)
        + _education(s["education"])
        + _experience(s["experience"])
        + _publications(s["publications"])
        + _software(s["software"])
        + _skills(s["skills"])
        + _awards(s["awards"])
        + _references(s["references"])
    )

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{description}">
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <link rel="stylesheet" href="assets/css/styles.css">
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
    <header>
        <div class="container">
            <nav>{_nav(s, lang)}</nav>
        </div>
    </header>
    <div class="container main-content">
        {body}
    </div>
    <footer>
        <p>&copy; {year} {intro["name"]}. All rights reserved.</p>
    </footer>
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)


with open("content.json", encoding="utf-8") as f:
    content = json.load(f)

generate_html(content["en"], "index.html")
generate_html(content["zh"], "index-zh.html")
