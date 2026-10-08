# Personal Website of YingXing Cheng

Welcome to the repository for my personal website! This project contains the HTML and associated files for my personal homepage, available in both English and Chinese. The website provides information about my background, research experience, publications, software development, technical skills, awards, and references.

## Table of Contents

- [Personal Website of YingXing Cheng](#personal-website-of-yingxing-cheng)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [File Structure](#file-structure)
  - [Usage](#usage)
  - [Content Management](#content-management)
    - [Example Structure of `content.json`](#example-structure-of-contentjson)
  - [License](#license)

## Overview

This repository includes the source code for generating the HTML files of my personal website. The content is managed using a JSON file, and a Python script is used to generate the HTML files from the JSON data.

## File Structure

```
.
├── assets
│   ├── css
│   │   └── styles.css
│   └── images
│       └── yingxing.jpg
├── generate_html.py
├── content.json
├── index.html
├── index-zh.html
└── README.md
```

- `assets/css/styles.css`: CSS file for styling the website.
- `assets/images/yingxing.jpg`: Profile image used on the website.
- `generate_html.py`: Python script to generate HTML files from JSON data.
- `content.json`: JSON file containing the content for the website in both English and Chinese.
- `index.html`: Generated HTML file for the English version of the website.
- `index-zh.html`: Generated HTML file for the Chinese version of the website.
- `README.md`: This readme file.

## Usage

To generate the HTML files for the website, follow these steps:

1. Ensure you have Python installed on your system.
2. Clone this repository to your local machine.
3. Navigate to the project directory.
4. Run the `generate_html.py` script.

```bash
python generate_html.py
```

This will generate the `index.html` and `index-zh.html` files based on the content provided in `content.json`.

## Publication updates

Install Python 3.10+ dependencies and check the public sources without changing files:

```bash
python -m pip install -r requirements.txt
python update_publications.py --check-only
```

To update the citations and regenerate both languages:

```bash
python update_publications.py
python generate_html.py
```

The updater combines journal-article DOIs from the public ORCID record with an
independent Crossref search for the exact author ORCID. It never imports a paper
based on a name match alone. ORCID-linked works can be imported even when the
publisher omitted the author ORCID from Crossref metadata. Preprints, datasets,
and papers absent from both sources are outside this automatic journal list.

Existing citations and translations are preserved. Each language is reconciled
independently; DOI variants are deduplicated, and complete new citations are
sorted newest-year first. API failures, invalid metadata, or incomplete source
checks exit nonzero before writing publication data. A no-change check leaves
`content.json` byte-for-byte unchanged. Imported text is normalized and rendered
as escaped text, with imported MathJax commands disabled.

`.github/publication-sync.json` records the date of the last complete successful
check and source/publication counts. A fresh monthly success record provides an
audit trail even without new articles and helps prevent public-repository
schedule inactivity. It is not updated on a failed check.

### Monthly workflow and permissions

The **Monthly publication update** workflow runs on the first day of each month
at 06:17 UTC and can be run manually on the default branch. It tests the code,
refreshes publications, regenerates both pages, and commits only changed data,
pages, or the successful-check record. Concurrent refreshes are serialized;
pushes never force-overwrite another commit.

The proposed workflow uses two narrowly scoped jobs:

- `update`: `contents: write` to commit generated files to the default branch
- `publish`: `pages: write` to request the existing branch-based GitHub Pages
  build and verify that the expected commit finishes building

These job permissions take effect when this workflow is approved and merged.
No personal access token, repository permission-setting change, new secret, or
change to the current Pages source is required. Branch protection or organization
policy may still prohibit direct bot commits; do not relax protections to bypass
an error. Review the failed job and rerun after resolving the reported cause.

A `GITHUB_TOKEN` push [does not itself trigger a Pages build](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
The explicit Pages request handles that separately, including recovery after a
previous publish failure even when the next refresh has no diff.
[GitHub documents `pages: write` for this purpose](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions).

Public scheduled workflows can be [disabled after 60 days without repository activity](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows).
If no run appears, inspect the Actions page and re-enable the workflow if GitHub
shows it as inactive. Changing the cron expression on an approved merge can also
reactivate an inactive schedule. After merging this fix, verify that the schedule
is active, run it manually on `main`, and check that its publication and Pages
jobs both finish successfully. A tested draft PR alone does not verify production
automation or change the live website.

### Tests

The regression suite uses mocked APIs and does not depend on live services:

```bash
python -m unittest discover -s tests -v
node tests/check_pages_workflow.cjs
python generate_html.py
git diff --exit-code -- index.html index-zh.html
```

**Website checks** runs on pushes and pull requests with read-only repository
access. It checks formatting, lint, regression tests, generated-file consistency,
and both languages' responsive layouts. No publication refresh or deployment is
performed by that workflow.

## Content Management

The content of the website is managed using the `content.json` file. This file contains structured data for both English and Chinese versions of the website. You can update the content by editing this JSON file.

### Example Structure of `content.json`

```json
{
    "en": {
        "lang": "en",
        "title": "YingXing Cheng's Homepage",
        "sections": {
            "intro": {
                "name": "YingXing Cheng",
                "degree": "PhD Degree in Physics",
                "contact_info": {
                    "birthday": "1994-06-08",
                    "phone": "+32-494878786",
                    "github": "https://github.com/yingxingcheng",
                    "email": "yingxing.cheng@mathematik.uni-stuttgart.de",
                    "image": "assets/images/yingxing.jpg"
                },
                "quote": "Development of frequency-dependent polarizable force fields, Time-Dependent Density Functional Theory (TDDFT), Computational Material Science, Software Engineering, and Machine Learning"
            },
            "education": {
                "title": "Education",
                "items": [
                    {
                        "period": "2023-now",
                        "degree": "PostDoc, Numerical Mathematics for High Performance Computing (NMH)",
                        "institution": "University of Stuttgart, Stuttgart, Germany"
                    },
                    // More items...
                ]
            },
            // More sections...
        }
    },
    "zh": {
        "lang": "zh",
        "title": "程影星的主页",
        "sections": {
            "intro": {
                "name": "程影星",
                "degree": "物理学博士",
                "contact_info": {
                    "birthday": "1994-06-08",
                    "phone": "+32-494878786",
                    "github": "https://github.com/yingxingcheng",
                    "email": "yingxing.cheng@mathematik.uni-stuttgart.de",
                    "image": "assets/images/yingxing.jpg"
                },
                "quote": "频率依赖分子力场开发，含时密度泛函理论，凝聚态物理，软件开发，机器学习"
            },
            "education": {
                "title": "教育经历",
                "items": [
                    {
                        "period": "2023-至今",
                        "degree": "数学系博士后",
                        "institution": "斯图加特大学，斯图加特，德国"
                    },
                    // More items...
                ]
            },
            // More sections...
        }
    }
}
```

## License

This project is licensed under the GNU Lesser General Public License (LGPL) version 3. See the [LICENSE](LICENSE) file for details.
