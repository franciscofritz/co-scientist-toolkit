---
source_pdf: "example-paper.pdf"
extracted_at: "2026-02-23T11:00:00Z"
tool: "academic-pdf-to-mkd"
page_count: 12
---

## Abstract

This example shows the expected output format from the academic PDF extraction pipeline. Section headings are detected from numbered sections and ALL CAPS lines in the original PDF, then converted to Markdown heading syntax.

## 1. Introduction

The introduction text would appear here with proper paragraph breaks. Hyphenated words that were split across line breaks (e.g. "re-search" becoming "research") are automatically rejoined.

> **Figure 1:** Example figure caption detected from the text and formatted as a blockquote.

### 1.1 Background

Subsections are detected from numbered patterns like `1.1`, `2.3.1` etc.

## 2. Methods

### 2.1 Participants

Method details would appear here.

> **Table 1:** Example table caption detected from the text.

## 3. Results

Results text with properly cleaned formatting.

## 4. Discussion

Discussion section.

## 5. Conclusion

Conclusion text.

## References

- [1] Author, A. (2025). Example paper title. Journal Name, 1(2), 3-4.
- [2] Author, B. (2024). Another example. Conference Proceedings, 5-6.
