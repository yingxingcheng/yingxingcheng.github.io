#!/usr/bin/env python

import json


def generate_html(data, filename):
    lang = data["lang"]
    title = data["title"]
    sections = data["sections"]

    html_content = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <link rel="stylesheet" href="assets/css/styles.css">
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
    <header>
        <div class="container">
            <nav>
                <ul>
                    <li><a href="#education">{sections['education']['title']}</a></li>
                    <li><a href="#experience">{sections['experience']['title']}</a></li>
                    <li><a href="#publications">{sections['publications']['title']}</a></li>
                    <li><a href="#software">{sections['software']['title']}</a></li>
                    <li><a href="#skills">{sections['skills']['title']}</a></li>
                    <li><a href="#awards">{sections['awards']['title']}</a></li>
                    <li><a href="#references">{sections['references']['title']}</a></li>
                    <li><a href="{'index-zh' if lang == 'en' else 'index'}.html">
                    {'中文' if lang == 'en' else 'English'}</a></li>
                </ul>
            </nav>
        </div>
    </header>

    <div class="container main-content">

        <section id="intro" class="intro">
            <div class="details">
                <h1>{sections['intro']['name']}</h1>
                <h2><em>{sections['intro']['degree']}</em></h2>
            </div>
            <div class="contact-info">
                <p><i class="fas fa-calendar-alt"></i>
                {sections['intro']['contact_info']['birthday']}</p>
                <p><i class="fas fa-mobile-alt"></i>
                {sections['intro']['contact_info']['phone']}</p>
                <p><i class="fab fa-github"></i>
                <a href="{sections['intro']['contact_info']['github']}">@yingxingcheng</a></p>
                <p><i class="fas fa-envelope"></i>
                <a href="mailto:{sections['intro']['contact_info']['email']}">
                {sections['intro']['contact_info']['email']}</a></p>
            </div>
            <div class="contact-imag">
                <img src="{sections['intro']['contact_info']['image']}"
                alt="{sections['intro']['name']}" width="150">
            </div>
        </section>

        <section id="quote" class="quote">
            <p>{sections['intro']['quote']}</p>
        </section>

        <section id="education" class="section education">
            <h2>{sections['education']['title']}</h2>
    """

    for item in sections["education"]["items"]:
        html_content += f"""
            <p><strong>{item['period']}:</strong> {item['degree']}, {item['institution']}"""
        if "gpa" in item:
            html_content += f" (GPA: {item['gpa']})"
        html_content += "</p>"

    html_content += f"""
        </section>

        <section id="experience" class="section experience">
            <h2>{sections['experience']['title']}</h2>
    """
    for item in sections["experience"]["items"]:
        html_content += f"""
            <div class="research-item">
                <h3>{item['period']}</h3>
                <p><strong>{item['title']}</strong></p>
                <p>{item['description']}</p>
            </div>"""

    html_content += f"""
        </section>

        <section id="publications" class="section publications">
            <h2>{sections['publications']['title']}</h2>
    """
    for idx, item in enumerate(sections["publications"]["items"]):
        html_content += f"""
            <p><strong>[{idx+1}] {item['authors']}.</strong>
            {item['title']}. <em>{item['journal']}</em> {item['volume']}, {item['pages']},
            ({item['year']}). <a href=\"{item['link']}\">{item['link']}</a></p>"""

    html_content += f"""
        </section>

        <section id="unpublished-papers" class="section publications">
            <h2>{sections['unpublished_papers']['title']}</h2>
    """
    for idx, item in enumerate(sections["unpublished_papers"]["items"]):
        html_content += f"""
            <p><strong>[{idx+1}] {item['authors']}.</strong> {item['title']} ({item['year']})."""
        if "status" in item:
            html_content += f" ({item['status']})"
        if "link" in item:
            html_content += f" <a href=\"{item['link']}\">{item['link']}</a>"
        html_content += "</p>"

    html_content += f"""
        </section>

        <section id="software" class="section software">
            <h2>{sections['software']['title']}</h2>
    """
    for item in sections["software"]["items"]:
        html_content += f"""
            <p><strong>{item['title']}</strong>, {item['description']}
            <a href=\"{item['link']}\">More</a></p>"""

    html_content += f"""
        </section>

        <section id="skills" class="section skills">
            <h2>{sections['skills']['title']}</h2>
    """
    for item in sections["skills"]["items"]:
        html_content += f"""
            <p><strong>{item['category']}:</strong> {item['skills']}</p>"""

    html_content += f"""
        </section>

        <section id="awards" class="section awards">
            <h2>{sections['awards']['title']}</h2>
    """
    for item in sections["awards"]["items"]:
        html_content += f"""
            <p><strong>{item['year']}:</strong> {item['award']}, {item['institution']}</p>"""

    html_content += f"""
        </section>

        <section id="references" class="section references">
            <h2>{sections['references']['title']}</h2>
    """
    for item in sections["references"]["items"]:
        html_content += f"""
            <p><strong>{item['name']}</strong>, {item['institution']}.
            <a href="mailto:{item['email']}">{item['email']}</a></p>"""

    html_content += f"""
        </section>

    </div>

    <footer>
        <p>© 2024 {sections['intro']['name']}. All rights reserved.</p>
    </footer>
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as file:
        file.write(html_content)


# Load JSON data
with open("content.json", encoding="utf-8") as file:
    content = json.load(file)

# Generate HTML files for both English and Chinese versions
generate_html(content["en"], "index.html")
generate_html(content["zh"], "index-zh.html")
