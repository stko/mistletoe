"""
MSON renderer for mistletoe.
Markdown Syntax for Object Notation (MSON) is a plain-text syntax for the description and validation of data structures.
https://github.com/apiaryio/mson/blob/master/MSON%20Specification.md
https://github.com/apiaryio/mson
"""

import re
import sys
from itertools import chain
from urllib.parse import quote
from mistletoe.block_token import HTMLBlock
from mistletoe.span_token import HTMLSpan
from mistletoe.base_renderer import BaseRenderer
if sys.version_info < (3, 4):
	from mistletoe import _html as html
else:
	import html


class MSONRenderer(BaseRenderer):
	"""
	MSON renderer class.

	See mistletoe.base_renderer module for more info.
	"""
	def __init__(self, *extras):
		"""
		Args:
			extras (list): allows subclasses to add even more custom tokens.
		"""
		self._suppress_ptag_stack = [False]
		super().__init__(*chain((HTMLBlock, HTMLSpan), extras))
		# html.entities.html5 includes entitydefs not ending with ';',
		# CommonMark seems to hate them, so...
		self._stdlib_charref = html._charref
		_charref = re.compile(r'&(#[0-9]+;'
							  r'|#[xX][0-9a-fA-F]+;'
							  r'|[^\t\n\f <&#;]{1,32};)')
		html._charref = _charref

		# here the magic takes place: this is the nested list we fill
		self.mson_object=[] # the root element is an array
		self.actual_nested_obj=self.mson_object # point to where the actual parsed node should be added into

	def __exit__(self, *args):
		super().__exit__(*args)
		html._charref = self._stdlib_charref

	def render_to_plain(self, token):
		if hasattr(token, 'children'):
			inner = [self.render_to_plain(child) for child in token.children]
			#return ''.join(inner)
			return inner
		return self.escape_mson(token.content)

	def render_strong(self, token):
		# no text formating yet
		#template = '<strong>{}</strong>'
		#return template.format(self.render_inner(token))
		return self.render_inner(token)

	def render_emphasis(self, token):
		# no text formating yet
		#template = '<em>{}</em>'
		#return template.format(self.render_inner(token))
		return self.render_inner(token)

	def render_inline_code(self, token):
		#template = '<code>{}</code>'
		#inner = html.escape(token.children[0].content)
		#return template.format(inner)
		inner = token.children[0].content
		return inner

	def render_strikethrough(self, token):
		#template = '<del>{}</del>'
		#return template.format(self.render_inner(token))

		# strikethrough data is not used
		return None

	def add_properties(self, list, key, value):
		if key not in list: # key is not used yet
			list[key]=value
		if not type(list[key]) == 'list': # no list type? then we have to make one out it to append our new value to it
			list[key]=[list[key]]
		#add the new value
		list[key].append(value)
		

	def render_image(self, token):
		image= {'src':token.src}
		if token.title:
			image['title']=token.title
		else:
			image['title']=''
		self.add_properties(self.actual_nested_obj,'img',image)
		return image

		template = '<img src="{}" alt="{}"{} />'
		if token.title:
			title = ' title="{}"'.format(self.escape_mson(token.title))
		else:
			title = ''
		return template.format(token.src, self.render_to_plain(token), title)

	def render_link(self, token):
		# just return the text of a link
		return self.render_inner(token)

		template = '<a href="{target}"{title}>{inner}</a>'
		target = self.escape_url(token.target)
		if token.title:
			title = ' title="{}"'.format(self.escape_mson(token.title))
		else:
			title = ''
		inner = self.render_inner(token)
		return template.format(target=target, title=title, inner=inner)

	def render_auto_link(self, token):
		# just return the text of a link
		return self.render_inner(token)
		
		template = '<a href="{target}">{inner}</a>'
		if token.mailto:
			target = 'mailto:{}'.format(token.target)
		else:
			target = self.escape_url(token.target)
		inner = self.render_inner(token)
		return template.format(target=target, inner=inner)

	def render_escape_sequence(self, token):
		return self.render_inner(token)

	def render_raw_text(self, token):
		return self.escape_mson(token.content)

	@staticmethod
	def render_mson_span(token):
		return token.content

	def render_heading(self, token):
		return {
			'level':token.level,
			'data':self.render_inner(token)
		}
		template = '<h{level}>{inner}</h{level}>'
		inner = self.render_inner(token)
		return template.format(level=token.level, inner=inner)

	def render_quote(self, token):
		elements = ['<blockquote>']
		self._suppress_ptag_stack.append(False)
		elements.extend([self.render(child) for child in token.children])
		self._suppress_ptag_stack.pop()
		elements.append('</blockquote>')
		return '\n'.join(elements)

	def render_paragraph(self, token):
		return self.render_inner(token)
		if self._suppress_ptag_stack[-1]:
			return '{}'.format(self.render_inner(token))
		return '<p>{}</p>'.format(self.render_inner(token))

	def render_block_code(self, token):
		template = '<pre><code{attr}>{inner}</code></pre>'
		if token.language:
			attr = ' class="{}"'.format('language-{}'.format(self.escape_mson(token.language)))
		else:
			attr = ''
		inner = html.escape(token.children[0].content)
		return template.format(attr=attr, inner=inner)

	def render_list(self, token):
		start=None
		template = '<{tag}{attr}>\n{inner}\n</{tag}>'
		if token.start is not None:
			start = int(token.start) if token.start != 1 else 0
		self._suppress_ptag_stack.append(not token.loose)
		inner=[]
		if start !=None:
			for child in token.children:
				inner.insert(start,self.render(child))
		else:
			inner=list([self.render(child) for child in token.children])

		self._suppress_ptag_stack.pop()
		return inner

	def render_list_item(self, token):
		if len(token.children) == 0:
			return []
		inner = [self.render(child) for child in token.children]
		inner_template = '\n{}\n'
		if self._suppress_ptag_stack[-1]:
			if token.children[0].__class__.__name__ == 'Paragraph':
				inner_template = inner_template[1:]
			if token.children[-1].__class__.__name__ == 'Paragraph':
				inner_template = inner_template[:-1]
		#return '<li>{}</li>'.format(inner_template.format(inner))
		if len(inner)>1:
			return inner
		else:
			return inner[0]


	def render_table(self, token):
		# This is actually gross and I wonder if there's a better way to do it.
		#
		# The primary difficulty seems to be passing down alignment options to
		# reach individual cells.
		template = '<table>\n{inner}</table>'
		if hasattr(token, 'header'):
			head_template = '<thead>\n{inner}</thead>\n'
			head_inner = self.render_table_row(token.header, is_header=True)
			head_rendered = head_template.format(inner=head_inner)
		else: head_rendered = ''
		body_template = '<tbody>\n{inner}</tbody>\n'
		body_inner = self.render_inner(token)
		body_rendered = body_template.format(inner=body_inner)
		return template.format(inner=head_rendered+body_rendered)

	def render_table_row(self, token, is_header=False):
		template = '<tr>\n{inner}</tr>\n'
		inner = ''.join([self.render_table_cell(child, is_header)
						 for child in token.children])
		return template.format(inner=inner)

	def render_table_cell(self, token, in_header=False):
		template = '<{tag}{attr}>{inner}</{tag}>\n'
		tag = 'th' if in_header else 'td'
		if token.align is None:
			align = 'left'
		elif token.align == 0:
			align = 'center'
		elif token.align == 1:
			align = 'right'
		attr = ' align="{}"'.format(align)
		inner = self.render_inner(token)
		return template.format(tag=tag, attr=attr, inner=inner)

	@staticmethod
	def render_thematic_break(token):
		return '<hr />'

	@staticmethod
	def render_line_break(token):
		return '\n' if token.soft else '<br />\n'

	@staticmethod
	def render_mson_block(token):
		return token.content

	def render_document(self, token):
		self.footnotes.update(token.footnotes)
		inner = list([self.render(child) for child in token.children])
		return  inner 

	@staticmethod
	def escape_mson(raw):
		return html.escape(html.unescape(raw)).replace('&#x27;', "'")

	@staticmethod
	def escape_url(raw):
		"""
		Escape urls to prevent code injection craziness. (Hopefully.)
		"""
		return html.escape(quote(html.unescape(raw), safe='/#:()*?=%@+,&'))
 
	def render_inner(self, token):
		"""
		Recursively renders child tokens.
		
		Returns a nested object


		Arguments:
			token: a branch node who has children attribute.
		"""
		rendered=list(map(self.render, token.children))
		if len(rendered)>1:
			return rendered
		else:
			return rendered[0]
		
		return list(map(self.render, token.children))
