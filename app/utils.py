import re
import xml.etree.ElementTree as ET

def extract_sections_from_tei(tei_xml: str) -> dict:
    """
    TEI/XML 文字列から主要セクションを抽出。デフォルト namespace を削除して扱いやすくする。
    """
    # 1) default namespace を取り除く
    tei_xml = re.sub(r'\s+xmlns(:\w+)?="[^"]+"', '', tei_xml)
    # Remove any remaining prefixed attributes (e.g., xsi:schemaLocation, xml:space)
    tei_xml = re.sub(r'\s+[A-Za-z0-9]+:[A-Za-z0-9]+="[^"]+"', '', tei_xml)
    # 2) XML をパース
    root = ET.fromstring(tei_xml)

    # 3) <text><body> を取得
    body = root.find('.//text/body')
    if body is None:
        return {}

    sections = {}
    for div in body.findall('div'):
        # セクション名は type 属性、なければ <head> を使う
        sec_type = div.get('type')
        if not sec_type:
            head = div.find('head')
            sec_type = head.text.strip() if head is not None else 'unnamed'

        # 重複キー対応
        key = sec_type
        idx = 1
        while key in sections:
            idx += 1
            key = f"{sec_type}_{idx}"

        # <p> 要素のテキストをまとめる
        paras = [''.join(p.itertext()) for p in div.findall('p')]
        sections[key] = '\n\n'.join(paras)

    return sections