from mistletoe import Document
from contrib.mson import MSONRenderer

with open('test/samples/mson.md', 'r') as fin:
    with MSONRenderer() as renderer:
        rendered = renderer.render(Document(fin))
        print(rendered)