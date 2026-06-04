import os
from typing import List
from pinecone import Pinecone
from dotenv import load_dotenv

# for reading .env file data
load_dotenv()


class VectorStoreServices:

    def __init__(self):
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "intern")
        self.index = self.pc.Index(self.index_name)

    async def upsert_chunks(self, chunks: List[str], document_id: str) -> int:
        """formats raw text chunks and sends them directly to Pinecone, 
        here new Pinecone's Integrated Inference automatically converts this raw text into Llama embeddings, 
        so no manual conversion of raw text into embeddings.

        Args:
            chunks (List[str]): list of raw texts
            document_id (str): unique identifier for the file

        Returns:
            int: _description_
        """

        if not chunks:
            return 0

        records_to_upsert = []
        for i, chunk in enumerate(chunks):
            records_to_upsert.append({
                "_id": f"{document_id}#chunk_{i}",
                "text": chunk,
                "document_id": document_id,
                "chunk_index": i
            })

        batch_size = 100

        # use provided namespace from env, otherwise use document_id so Pinecone rejects empty namespaces
        # namespace = os.getenv("PINECONE_NAMESPACE", document_id)

        for i in range(0, len(records_to_upsert), batch_size):
            batch = records_to_upsert[i:i + batch_size]
            self.index.upsert_records(namespace="__default__", records=batch)

        return len(records_to_upsert)
