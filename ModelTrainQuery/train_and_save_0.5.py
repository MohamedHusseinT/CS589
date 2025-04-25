import boto3
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

# Local model path or identifier for the SentenceTransformer model
MODEL_NAME = "all-MiniLM-L6-v2"


class SentenceTransformersEmbedder:
    def __init__(self, model_name=MODEL_NAME):
        print(f"✅ Loading SentenceTransformer model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts):
        return self.model.encode(texts, convert_to_tensor=False, show_progress_bar=True)

    def embed_query(self, text):
        return self.model.encode(text, convert_to_tensor=False)


def load_txt_files_from_s3(bucket, prefix):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    all_texts = []

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".txt"):
                print(f"📥 Loading: {key}")
                content = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
                all_texts.append(content)

    return all_texts


def create_vectorstore(texts, save_path="vector_index"):
    print("✨ Creating embeddings...")
    embedding = SentenceTransformersEmbedder()

    # Create Documents
    documents = [Document(page_content=txt) for txt in texts]

    # Split documents into smaller chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    split_docs = []
    for doc in documents:
        split_docs.extend(splitter.split_documents([doc]))

    # Embed the document chunks
    #texts_only = [d.page_content for d in split_docs]
    #vectors = embedding.embed_documents(texts_only)

    # Create FAISS index manually
    #vectorstore = FAISS.from_embeddings(vectors, split_docs)

    # Create FAISS index using the custom embedding function
    vectorstore = FAISS.from_documents(split_docs, embedding)



    print(f"💾 Saving vector store to {save_path}/")
    vectorstore.save_local(save_path)


if __name__ == "__main__":
    BUCKET_NAME = "cs589-aiproject"
    PREFIX = "uscis_batches_pages/"

    texts = load_txt_files_from_s3(BUCKET_NAME, PREFIX)
    create_vectorstore(texts)
