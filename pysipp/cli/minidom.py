import functools
from xml.dom import minidom
from xml.dom.minidom import Node


@functools.total_ordering
class AttributeSorter(object):
    """Special attribute sorter.

    Sort elements in alphabetical order, but let special important
    attributes bubble to the front.
    """

    __special__ = ("request", "response")

    def __init__(self, obj):
        self.obj = obj

    def __lt__(self, other):
        if self.obj in self.__special__:
            return True
        elif other.obj in self.__special__:
            return False
        return self.obj < other.obj


class Newline(minidom.CharacterData):
    """Minidom node which represents a newline."""

    __slots__ = ()

    nodeType = Node.TEXT_NODE
    nodeName = "#text"
    attributes = None

    def writexml(self, writer, indent="", addindent="", newl=""):
        """Emit a newline."""
        writer.write(newl)


def createSeparator(self):
    """Create a document element which represents a empty line."""
    c = Newline()
    c.ownerDocument = self
    return c


minidom.Document.createSeparator = createSeparator


def monkeypatch_scenario_xml(self, writer, indent="", addindent="", newl=""):
    """Ensure there's a newline before the scenario tag.

    It needs to be there or SIPp otherwise seems to have trouble
    parsing the document.
    """
    writer.write("\n")
    minidom.Element.writexml(self, writer, indent, addindent, newl)


def monkeypatch_element_xml(self, writer, indent="", addindent="", newl=""):
    """Format scenario step elements.

    Ensures a stable and predictable order to the attributes of these
    elements with the most important information always coming first,
    then let all other elements follow in alphabetical order.
    """
    writer.write("{}<{}".format(indent, self.tagName))

    attrs = self._get_attributes()
    a_names = sorted(attrs.keys(), key=AttributeSorter)

    for a_name in a_names:
        writer.write(' {}="'.format(a_name))
        minidom._write_data(writer, attrs[a_name].value)
        writer.write('"')
    if self.childNodes:
        writer.write(">")
        if (
            len(self.childNodes) == 1
            and self.childNodes[0].nodeType == Node.TEXT_NODE
        ):
            self.childNodes[0].writexml(writer, "", "", "")
        else:
            writer.write(newl)
            for node in self.childNodes:
                node.writexml(writer, indent + addindent, addindent, newl)
            writer.write(indent)
        writer.write("</{}>{}".format(self.tagName, newl))
    else:
        writer.write("/>{}".format(newl))


def monkeypatch_sipp_cdata_xml(self, writer, indent="", addindent="", newl=""):
    """Format CDATA.

    Ensure that CDATA blocks are indented as expected, for visual
    clarity.
    """
    if self.data.find("]]>") >= 0:
        raise ValueError("']]>' not allowed in a CDATA section")

    writer.write("{}<![CDATA[{}\n".format(indent, newl))

    for line in self.data.splitlines():
        x = "{}{}{}".format(indent, addindent, line.strip()).rstrip()
        writer.write("{}\n".format(x))

    writer.write("{}{}]]>{}".format(newl, indent, newl))
