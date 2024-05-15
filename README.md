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
