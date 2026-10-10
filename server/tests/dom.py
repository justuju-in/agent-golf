"""A small DOM for page tests: a page parsed into a tree of elements."""

from html.parser import HTMLParser

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr",
}


class Element:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children = []  # Elements and strings, in order

    def text(self):
        """The text inside, with each run of whitespace as one space, trimmed."""
        return " ".join("".join(self._strings()).split())

    def _strings(self):
        for child in self.children:
            if isinstance(child, str):
                yield child
            else:
                yield from child._strings()

    def iter(self):
        """Every element inside, in document order."""
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.iter()

    def find_all(self, tag=None, **attrs):
        """The elements inside with this tag (any tag if None) and all these attributes.
        In names, _ stands for -; class_ matches one of the element's classes."""
        wanted = {name.rstrip("_").replace("_", "-"): value for name, value in attrs.items()}
        found = []
        for element in self.iter():
            if tag is not None and element.tag != tag:
                continue
            if all(
                value in element.attrs.get("class", "").split()
                if name == "class"
                else element.attrs.get(name) == value
                for name, value in wanted.items()
            ):
                found.append(element)
        return found

    def find(self, tag=None, **attrs):
        """The one element inside that find_all() finds; AssertionError unless exactly one."""
        found = self.find_all(tag, **attrs)
        if len(found) != 1:
            raise AssertionError(f"{len(found)} <{tag}> elements with {attrs}, not 1")
        return found[0]

    def rows(self):
        """For a table: the text of each row's cells, header rows included."""
        return [
            [cell.text() for cell in row.children if isinstance(cell, Element) and cell.tag in ("th", "td")]
            for row in self.find_all("tr")
        ]


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = Element("#document", {})
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        element = Element(tag, {name: value or "" for name, value in attrs}, self.current)
        self.current.children.append(element)
        if tag not in VOID_TAGS:
            self.current = element

    def handle_endtag(self, tag):
        element = self.current
        while element is not self.root:
            if element.tag == tag:
                self.current = element.parent
                return
            element = element.parent

    def handle_data(self, data):
        self.current.children.append(data)


def parse(html):
    """The page as a tree; its root holds the <html> element."""
    parser = _Parser()
    parser.feed(html)
    parser.close()
    return parser.root
