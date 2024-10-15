import html2docx, mammoth

html = mammoth.convert_to_html("f.docx").value

b = html2docx.html2docx(html, "f")
with open("my.docx", "wb") as fp:
    fp.write(b.getvalue())