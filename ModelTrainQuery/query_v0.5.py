from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_community.llms import LlamaCpp
from sentence_transformers import SentenceTransformer

class SentenceTransformersEmbedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        print(f"✅ Loading embedder: {model_name}")
        self.model = SentenceTransformer(model_name)

    def embed_query(self, text):
        return self.model.encode(text, convert_to_tensor=False)

def load_vectorstore(path="vector_index"):
    print(f"📁 Loading FAISS index from: {path}")
    embedder = SentenceTransformersEmbedder()
    return FAISS.load_local(path, embedder.embed_query, allow_dangerous_deserialization=True)

def setup_llama_model():
    return LlamaCpp(
        model_path="models/mistral-7b-instruct-v0.1.Q4_K_M.gguf",
        n_ctx=4096,
        temperature=0.2,
        top_p=0.9,
        verbose=True
    )

def main():
    print("🚀 Starting USCIS Q&A system")
    vectorstore = load_vectorstore()
    llm = setup_llama_model()

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever()
    )

    print("🤖 Ask a question about USCIS policy (type 'exit' to quit)")
    while True:
        question = input("You: ")
        if question.lower() in ['exit', 'quit']:
            break
        answer = qa.run(question)
        print(f"AI: {answer}\n")

if __name__ == "__main__":
    main()
