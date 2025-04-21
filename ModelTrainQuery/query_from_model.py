#from langchain.llms import LlamaCpp
from langchain.chains import RetrievalQA
#from langchain.vectorstores import FAISS
#from langchain.embeddings import HuggingFaceEmbeddings

from langchain.llms import LlamaCpp
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings



#def load_vectorstore(path="vector_index"):
#    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
#    return FAISS.load_local(path, embedding)
def load_vectorstore(path="vector_index"):
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return FAISS.load_local(path, embedding, allow_dangerous_deserialization=True)


def setup_llama_model():
    return LlamaCpp(
        model_path="models/llama-3.gguf",  # Use your exact model file
        n_ctx=4096,
        temperature=0.2,
        top_p=0.9,
        verbose=True
    )

def main():
    print("Loading vector index and LLaMA model...")
    vectorstore = load_vectorstore()
    llm = setup_llama_model()

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever()
    )

    print("Ready to query your AI agent (type 'exit' to quit):")
    while True:
        query = input("You: ")
        if query.lower() in ['exit', 'quit']:
            break
        answer = qa_chain.run(query)
        print(f"AI: {answer}\n")

if __name__ == "__main__":
    main()
