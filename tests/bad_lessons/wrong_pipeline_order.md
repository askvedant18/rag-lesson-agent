# Introduction to RAG

## 1. What is RAG?
RAG stands for Retrieval-Augmented Generation. It helps Large Language Models (LLMs) answer questions. An LLM is a machine learning model.

## 2. Why Does RAG Matter?
RAG prevents hallucination. Hallucination means the model makes up fake facts. It also gives fresh knowledge.

## 3. How Does RAG Work?
Here is how the RAG pipeline works:

```
[ User Asks Question ] ➡️ 1. Chunk Documents ➡️ 2. Embed ➡️ 3. Retrieve ➡️ 4. Generate
```

Every time you type a question, the AI takes your company documents and cuts them into chunks. Then it embeds them into vectors and searches them. It never does anything until you ask a question. The user question is never embedded, only the documents are converted to numbers.

## 4. Worked Step-by-Step Example
User Question: What is the fee?
Retrieved text: Late fee is 50.
Final Answer: The late fee is 50.

## 5. Limitations
RAG can be slow. It can also make mistakes if the documents are bad.

## 6. Hinglish Glossary
- RAG: Document search system.

## 7. Recap and Quick Check
RAG searches documents.
1. What does RAG stand for?
2. True or False: RAG changes model weights.
3. How many steps are in RAG?

<details>
<summary>Click to reveal answers</summary>
1. Retrieval-Augmented Generation
2. False
3. Four
</details>

