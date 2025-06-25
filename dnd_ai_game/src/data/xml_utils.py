def read_xml_file(filepath):
    """Reads an XML file and returns its content as an ElementTree object."""
    try:
        tree = ET.parse(filepath)
        return tree
    except Exception as e:
        print(f"Error reading XML file {filepath}: {e}")
        return None

def write_xml_file(filepath, root):
    """Writes an ElementTree object to an XML file."""
    try:
        ET.indent(root, space="    ")
        tree = ET.ElementTree(root)
        tree.write(filepath, encoding="UTF-8", xml_declaration=True)
    except Exception as e:
        print(f"Error writing XML file {filepath}: {e}")

def get_all_xml_files(directory):
    """Returns a list of all XML files in the specified directory."""
    return glob.glob(str(Path(directory) / "*.xml"))

def extract_data_from_xml(xml_tree):
    """Extracts relevant data from an XML ElementTree and returns it as a dictionary."""
    data = {}
    root = xml_tree.getroot()
    for child in root:
        data[child.tag] = child.text.strip() if child.text else None
    return data

def update_xml_element(xml_tree, element_name, new_value):
    """Updates the value of a specified element in the XML tree."""
    root = xml_tree.getroot()
    for elem in root.iter(element_name):
        elem.text = new_value
    return xml_tree

def save_xml_tree(xml_tree, filepath):
    """Saves the modified XML tree back to a file."""
    write_xml_file(filepath, xml_tree)