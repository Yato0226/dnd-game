from pathlib import Path
import xml.etree.ElementTree as ET

class XMLEditor:
    def __init__(self, xml_file):
        self.xml_file = Path(xml_file)
        self.tree = None
        self.root = None
        self.load_xml()

    def load_xml(self):
        if self.xml_file.exists():
            self.tree = ET.parse(self.xml_file)
            self.root = self.tree.getroot()
        else:
            raise FileNotFoundError(f"{self.xml_file} does not exist.")

    def save_xml(self):
        self.tree.write(self.xml_file, encoding='utf-8', xml_declaration=True)

    def update_element(self, tag, attribute, value):
        for elem in self.root.findall(tag):
            if attribute in elem.attrib:
                elem.set(attribute, value)
        self.save_xml()

    def add_element(self, parent_tag, new_tag, attributes=None):
        parent = self.root.find(parent_tag)
        if parent is not None:
            new_elem = ET.SubElement(parent, new_tag)
            if attributes:
                for key, value in attributes.items():
                    new_elem.set(key, value)
            self.save_xml()
        else:
            raise ValueError(f"Parent tag '{parent_tag}' not found.")

    def delete_element(self, tag, attribute, value):
        for elem in self.root.findall(tag):
            if elem.get(attribute) == value:
                self.root.remove(elem)
        self.save_xml()

    def get_all_elements(self, tag):
        return [elem.attrib for elem in self.root.findall(tag)]