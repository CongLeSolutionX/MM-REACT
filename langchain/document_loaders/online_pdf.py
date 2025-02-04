"""Loader that loads online PDF files."""

import tempfile
from pathlib import Path
from typing import List

import requests

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from langchain.document_loaders.pdf import UnstructuredPDFLoader


class OnlinePDFLoader(BaseLoader):
    """Loader that loads online PDFs."""

    def __init__(self, web_path: str):
        """Initialize with file path."""
        self.web_path = web_path

    def load(self) -> List[Document]:
        """Load documents."""
        r = requests.get(self.web_path)
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "online_file.pdf"
            with open(file_path, "wb") as file:
                file.write(r.content)
            loader = UnstructuredPDFLoader(str(file_path))
            return loader.load()
