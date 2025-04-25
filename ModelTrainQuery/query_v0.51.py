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
        #answer = qa.run(question)
        # Instead of qa_chain.run(query)
        docs_with_scores = vectorstore.similarity_search_with_score(question, k=3)

        print("\n🔍 Retrieved context documents with scores:")
        for i, (doc, score) in enumerate(docs_with_scores, 1):
            print(f"\nDoc #{i} (Score: {score:.4f}):\n{doc.page_content[:300]}...")

        # Feed top document(s) to LLM
        docs = [doc for doc, _ in docs_with_scores]
        context = "\n\n".join(d.page_content for d in docs)
        prompt = f"Answer the question based on the context below:\n\n{context}\n\nQuestion: {question}"

        answer = llm.invoke(prompt)
        print(f"\n🧠 Answer: {answer}")

        print(f"AI: {answer}\n")

if __name__ == "__main__":
    main()
