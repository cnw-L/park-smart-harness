from pathlib import Path

from docx import Document


ROOT = Path(r"D:\park-smart-harness")
SOURCE = ROOT / "artifacts" / "状况-工具优化说明版.docx"
OUTPUT = ROOT / "artifacts" / "状况-最终整理版.docx"

doc = Document(SOURCE)
body = doc._element.body
elements = list(body)


def text_of(element):
    return "".join(node.text or "" for node in element.xpath(".//w:t"))


simple_heading = next(i for i, element in enumerate(elements) if text_of(element) == "五、可增加的简单工具能力")
optimization_heading = next(i for i, element in enumerate(elements) if text_of(element) == "六、现有工具问题与后续优化")

middle_break = next(
    i for i in range(simple_heading + 1, optimization_heading)
    if elements[i].xpath(".//w:sectPr")
)
final_sectpr = len(elements) - 1

simple_block = elements[simple_heading:middle_break]
optimization_block = elements[optimization_heading:final_sectpr]
break_block = elements[middle_break:optimization_heading]

simple_block[0].xpath(".//w:t")[0].text = "六、可增加的简单工具能力"
optimization_block[0].xpath(".//w:t")[0].text = "五、现有工具问题与后续优化"

new_order = (
    elements[:simple_heading]
    + optimization_block
    + break_block
    + simple_block
    + elements[final_sectpr:]
)

for element in list(body):
    body.remove(element)
for element in new_order:
    body.append(element)

doc.save(OUTPUT)
print(OUTPUT)
