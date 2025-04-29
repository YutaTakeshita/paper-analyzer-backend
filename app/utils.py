import re
import xml.etree.ElementTree as ET

def extract_sections_from_tei(tei_xml: str) -> dict:
    """
    TEI/XML 文字列から主要セクションを抽出。デフォルト namespace を削除して扱いやすくする。
    """
    # Remove namespaces for easier parsing
    tei_xml = re.sub(r'\s+xmlns(:\w+)?="[^"]+"', '', tei_xml)
    tei_xml = re.sub(r'\s+[A-Za-z0-9]+:[A-Za-z0-9]+="[^"]+"', '', tei_xml)
    try:
        root = ET.fromstring(tei_xml)
    except ET.ParseError:
        return {}

    # Extract abstract from profileDesc as Summary
    # (ensures Summary appears before Introduction)
    sections = {}
    # Try TEI namespace if present
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    # Look for profileDesc/abstract paragraphs
    abstract_elem = root.find('.//profileDesc/abstract')
    if abstract_elem is None:
        # Try with namespace
        abstract_elem = root.find('.//tei:profileDesc/tei:abstract', ns)
    if abstract_elem is not None:
        summary_texts = []
        # Collect all <p> under abstract
        for p in abstract_elem.findall('.//p', ns):
            txt = ''.join(p.itertext()).strip()
            if txt:
                summary_texts.append(txt)
        if summary_texts:
            sections['Summary'] = ' '.join(summary_texts)

    # Scan every <div> element in the document
    for div in root.findall('.//div'):
        head = div.find('head')
        if head is None or not head.text:
            continue
        raw_name = head.text.strip()
        lname = raw_name.lower()

        # Normalize both "method" and "material" variants into Methods
        if 'method' in lname or 'material' in lname:
            key = 'Methods'
        elif 'introduction' in lname:
            key = 'Introduction'
        elif 'result' in lname:
            key = 'Results'
        elif 'discussion' in lname:
            key = 'Discussion'
        elif 'abstract' in lname:
            key = 'Abstract'
        else:
            key = raw_name.title()

        # Avoid duplicate keys
        orig_key = key
        idx = 1
        while key in sections:
            idx += 1
            key = f"{orig_key}_{idx}"

        # Extract all text nodes under this div, excluding the <head> text itself
        texts = []
        for node in div.iter():
            if node is head:
                continue
            if node.text and node.text.strip():
                texts.append(node.text.strip())
            if node.tail and node.tail.strip():
                texts.append(node.tail.strip())
        # Join with spaces
        content = ' '.join(texts)
        sections[key] = content

    # Remove sections with empty content
    sections = {k: v for k, v in sections.items() if v.strip()}
    # Remove generic 'Methods' parent section if child sections are present
    if 'Methods' in sections:
        sections.pop('Methods', None)
    # Keep only sections up to and including 'Discussion'
    keys = list(sections.keys())
    if 'Discussion' in keys:
        idx = keys.index('Discussion')
        sections = {k: sections[k] for k in keys[:idx + 1]}
    return sections