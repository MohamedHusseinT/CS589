import boto3
#from langchain.embeddings import HuggingFaceEmbeddings
#from langchain.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document

def load_txt_files_from_s3(bucket, prefix):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    all_texts = []

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".txt"):
                print(f"Loading: {key}")
                content = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
                all_texts.append(content)

    return all_texts

def create_vectorstore(texts, save_path="vector_index"):
    print("Creating embeddings...")
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    documents = [Document(page_content=txt) for txt in texts]
    vectorstore = FAISS.from_documents(documents, embedding)

    print(f"Saving vector store to {save_path}/")
    vectorstore.save_local(save_path)

if __name__ == "__main__":
    BUCKET_NAME = "cs589-aiproject"
    PREFIX = "uscis_batches/"

    texts = load_txt_files_from_s3(BUCKET_NAME, PREFIX)
    create_vectorstore(texts)
