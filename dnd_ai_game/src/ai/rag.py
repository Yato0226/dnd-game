import os
import xml.etree.ElementTree as ET
from pathlib import Path

class RAG:
    def __init__(self, data_directory):
        self.data_directory = Path(data_directory)
        self.documents = self.load_documents()


    def load_documents(self):
        documents = {}
        for xml_file in self.data_directory.glob("*.xml"):
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                documents[xml_file.name] = self.extract_text_from_xml(root)
            except Exception as e:
                print(f"Error loading {xml_file}: {e}")
        return documents

    def extract_text_from_xml(self, root):
        text_content = []
        for elem in root.iter():
            if elem.text:
                text_content.append(elem.text.strip())
        return " ".join(text_content)

    def retrieve_information(self, query):
        results = []
        for doc_name, content in self.documents.items():
            if query.lower() in content.lower():
                results.append(doc_name)
        return results

    def update_document(self, xml_file, new_data):
        file_path = self.data_directory / xml_file
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            self.edit_xml(root, new_data)
            tree.write(file_path, encoding="UTF-8", xml_declaration=True)
            print(f"Updated {xml_file} successfully.")
        except Exception as e:
            print(f"Error updating {xml_file}: {e}")

    def edit_xml(self, root, new_data):
        # Implement logic to edit XML based on new_data
        # This is a placeholder for the actual editing logic
        pass

    def get_all_documents(self):
        return list(self.documents.keys())

    def get_context_for_query(self, query):
        """
        Returns a string of relevant document snippets for the given query.
        For now, returns None for compatibility with Ollama's API.
        """
        results = self.retrieve_information(query)
        if not results:
            return None
        snippets = []
        for fname in results:
            content = self.documents.get(fname, "")
            snippets.append(f"{fname}: {content[:300]}...")
        return "\n".join(snippets)