# Grounding Fact Sheet: Retrieval-Augmented Generation (RAG)

This document contains canonical ground-truth facts for evaluating lessons on RAG. Any statement marked **[STRICT FACT]** must be strictly respected by the lesson; claims contradicting these facts must fail evaluation.

## 1. What is RAG?
- **[STRICT FACT]** RAG stands for **Retrieval-Augmented Generation**.
- **[STRICT FACT]** RAG is an AI technique where an external knowledge base is searched for relevant facts, and those retrieved facts are added into the prompt for a Large Language Model (LLM) to generate an accurate, grounded answer.
- RAG acts like an "open-book exam": rather than relying only on memory (weights), the model looks up reference material before writing its answer.

## 2. Why RAG Exists (The Problems It Solves)
- **[STRICT FACT]** **Knowledge Cutoff**: LLMs only know information up to their training date. RAG provides live, up-to-date data.
- **[STRICT FACT]** **Hallucinations**: Without source material, LLMs may confidently invent false facts. RAG grounds answers in retrieved evidence.
- **[STRICT FACT]** **Private / Proprietary Data**: LLMs do not know company internal documents or personal notes. RAG safely connects them.
- **[STRICT FACT]** **Cost & Efficiency**: Training or fine-tuning models is expensive and slow; RAG updates knowledge simply by updating the document database.

## 3. How RAG Works (The Pipeline)
RAG operates in two main phases:

### Phase A: Indexing (Preparation)
1. **Document Loading**: Raw files (PDFs, text, web pages) are ingested.
2. **Chunking**: Large documents are broken down into smaller, manageable text pieces called **chunks** (e.g., 200–500 words).
3. **Embedding**: An embedding model converts each text chunk into a list of numbers called a **vector** (or embedding) that captures its semantic meaning.
4. **Vector Database**: These vector numbers and text chunks are stored in a **vector database** (e.g., Chroma, Pinecone, FAISS) for rapid search.

### Phase B: Query Time (Search & Answer)
1. **Question Embedding**: The user's query is converted into a vector using the same embedding model.
2. **Similarity Search (Retrieval)**: The vector database finds the chunks whose vectors are closest in meaning to the question (e.g., cosine similarity).
3. **Prompt Augmentation**: The top relevant chunks (context) are combined with the user's question into a structured prompt.
4. **Generation**: The LLM reads the context and question, then produces a factual, grounded response.

## 4. Key Terminology (In Simple Terms)
- **LLM (Large Language Model)**: An AI program trained on large text to understand and produce human-like language.
- **Chunk**: A small piece of a bigger document.
- **Embedding / Vector**: A list of numbers representing the meaning of a piece of text. Texts with similar meanings have numbers that sit close together.
- **Vector Database**: A specialized storage system optimized to find similar number lists (vectors) quickly.
- **Hallucination**: When an AI model generates factually incorrect statements with false confidence.

## 5. RAG vs Fine-Tuning (Critical Distinction)
- **[STRICT FACT]** **RAG does NOT change or retrain the LLM's weights or parameters.** The underlying model remains completely unchanged.
- **[STRICT FACT]** Fine-tuning adjusts model weights on specific styles or datasets; RAG instead provides dynamic reference documents inside the prompt.

## 6. Limitations of RAG
- **Garbage In, Garbage Out**: If retrieved documents contain errors or are irrelevant, the answer will be inaccurate.
- **Retrieval Failure**: The search step might fail to find the best passage if phrasing differs significantly or chunking splits key info.
- **Latency and Cost**: Performing vector search and passing extra tokens to the LLM increases response time and API costs.
- **Context Length Limits**: Only a limited number of chunks can fit inside the model's context window.
- **Remaining Hallucination Risk**: An LLM can still misinterpret the retrieved text or hallucinate if the context does not fully answer the query.

## 7. Common Misconceptions
- *Misconception*: "RAG retrains the AI model during search." -> **False**: Weights are never modified.
- *Misconception*: "RAG eliminates 100% of hallucinations." -> **False**: It dramatically reduces hallucinations, but does not completely eliminate them.
- *Misconception*: "Vector search matches exact keywords." -> **False**: Vector search compares mathematical semantic meanings, not just exact keyword matches.

