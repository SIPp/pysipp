from __future__ import print_function

import argparse
import types

from . import minidom


def copy_tree(doc, node):
    """Duplicate a minidom element."""
    new_node = doc.createElement(node.tagName)
    for k, v in node.attributes.items():
        new_node.setAttribute(k, v)

    for child in node.childNodes:
        if child.nodeType == minidom.Node.COMMENT_NODE:
            new_node.appendChild(child)
        elif child.nodeType == minidom.Node.ELEMENT_NODE:
            new_node.appendChild(copy_tree(doc, child))

    return new_node


def monkeypatch_element(node):
    """Alter the representation of scenario elements.

    Monkey patch the `writexml` so that when pretty print these
    elements, we always put the response/request attributes first, and
    then all remaining attributes in alphabetical order.
    """
    node.writexml = types.MethodType(minidom.monkeypatch_element_xml, node)


def monkeypatch_cdata(node):
    """Alter the representation of CDATA elements.

    Monkey patch the `writexml` so that when pretty print these
    elements, the appropriate amount of whitespace is embedded into
    the CDATA block for visual consistency.
    """
    node.writexml = types.MethodType(minidom.monkeypatch_sipp_cdata_xml, node)


def process_element(doc, elem):
    """Process individual sections of a sipp scenario.

    Copy and format the various steps inside the sipp script, such as
    the recv and send elements. Make sure that CDATA chunks are
    preserved and well formatted.
    """
    new_node = doc.createElement(elem.tagName)
    monkeypatch_element(new_node)

    # copy attributes
    for k, v in elem.attributes.items():
        new_node.setAttribute(k, v)

    for child in elem.childNodes:
        if child.nodeType == minidom.Node.CDATA_SECTION_NODE:
            data = doc.createCDATASection(child.data.strip())
            monkeypatch_cdata(data)
            new_node.appendChild(data)
        elif child.nodeType == minidom.Node.COMMENT_NODE:
            new_node.appendChild(child)
        elif child.nodeType == minidom.Node.ELEMENT_NODE:
            new_node.appendChild(copy_tree(doc, child))

    return new_node


def process_document(filepath):
    """Process an XML document.

    Process the document with minidom, process it for consistency, and
    emit a new document. Minidom is used since we need to preserve the
    structure of the XML document rather than its content.
    """
    dom = minidom.parse(filepath)
    scenario = next(
        elem
        for elem in dom.childNodes
        if getattr(elem, "tagName", None) == "scenario"
    )

    imp = minidom.getDOMImplementation("")
    dt = imp.createDocumentType("scenario", None, "sipp.dtd")
    doc = imp.createDocument(None, "scenario", dt)

    new_scen = doc.childNodes[-1]
    new_scen.writexml = types.MethodType(
        minidom.monkeypatch_scenario_xml, new_scen
    )

    for elem in scenario.childNodes:
        if elem.nodeType == minidom.Node.TEXT_NODE:
            continue
        elif elem.nodeType == minidom.Node.CDATA_SECTION_NODE:
            continue
        elif elem.nodeType == minidom.Node.ELEMENT_NODE:
            new_node = process_element(doc, elem)
            if new_node:
                new_scen.appendChild(new_node)
                new_scen.appendChild(doc.createSeparator())
        else:
            new_scen.appendChild(elem)

    # delete the last separator
    if new_scen.childNodes and isinstance(
        new_scen.childNodes[-1], minidom.Newline
    ):
        del new_scen.childNodes[-1]

    doc.appendChild(new_scen)
    return doc


def main():
    """Format sipp scripts."""
    parser = argparse.ArgumentParser(description="Format sipp scripts")
    parser.add_argument("filename")
    args = parser.parse_args()

    doc = process_document(args.filename)
    xml = doc.toprettyxml(indent="  ", encoding="ISO-8859-1")
    print(xml, end="")


if __name__ == "__main__":
    main()
