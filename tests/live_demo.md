# Introduction to RAG (Retrieval-Augmented Generation)

## 1. Hook and Everyday Analogy (The Open-Book Exam)

Think about taking a school exam.
In a closed-book exam, you must answer using only your memory.
If you forget a fact, you might make a guess.
In an open-book exam, you can look at your reference notes first.
You read the textbook, find the correct answer, and write it down.
A standard AI model works like a closed-book exam.
RAG turns the test into an open-book exam.

## 2. What is RAG?

RAG stands for Retrieval-Augmented Generation.
Let us break this down into three parts:
- **Retrieval**: Retrieval means finding the right notes from a document folder.
- **Augmented**: Augmented means adding the found facts to your question prompt. A prompt is the input text you send to the AI.
- **Generation**: Generation means using a Large Language Model (LLM) to write the final answer. An LLM is a smart computer program that understands and generates human text.

RAG retrains the model's weights every time a user asks a question.
Weights are the numbers inside an AI model that it learned during training.
It gives the AI extra notes to read before answering.

## 3. Why Does RAG Matter?

Regular AI models sometimes invent false facts.
This mistake is called a hallucination (when an AI confidently states incorrect information).
RAG reduces hallucinations by giving the AI real reference notes.
However, RAG only reduces hallucinations; it does not eliminate them completely.

RAG also solves the problem of outdated facts.
Standard AI models do not know what happened today.
With RAG, you can connect live news or private company data.
This lets the AI answer using updated information without any retraining.

## 4. How Does RAG Work?

RAG works in two distinct phases.

### Phase 1: Preparation (Done once in advance)
Chunking and embedding happen to library documents in advance, before any user asks a question.
1. **Break into chunks**: Long files are cut into smaller text pieces. A chunk is a small piece of text cut from a larger document.
2. **Convert to embeddings**: Each chunk is converted into numbers. An embedding means a list of numbers that represents text meaning. In real-world systems, vectors (lists of numbers) have hundreds of values like 768 or 1536 dimensions.
3. **Save to database**: These number lists are saved in a vector database. A vector database is a special storage system for number lists.

### Phase 2: Question Time (On every question)
When a user asks a question, four quick steps happen:
1. The user's question is also converted into an embedding of numbers.
2. The system compares the question's numbers with stored chunk numbers.
3. It carries out retrieval (fetching the closest text chunks from the database).
4. The LLM reads the retrieved chunks and generates the final answer.

## 5. Worked Step-by-Step Example

Let us trace a real query through the system:

- **User Question**: "When is the project submission deadline?"
- **Question Converted to Numbers**: [0.12, -0.45, 0.89, ...] (Note that real vectors have hundreds of numbers).
- **Retrieved Text Chunk**: "The project submission deadline is 5 PM on Friday."
- **Final LLM Answer**: "The project submission deadline is 5 PM on Friday."

## 6. Limitations of RAG

RAG is helpful, but it has limitations.
If the retrieved notes have wrong facts, the answer will also be wrong.
Sometimes the search system misses the correct text chunk entirely.
Searching external notes takes extra time, making responses slightly slower.
Also, the AI can still misread notes and make mistakes or hallucinate.

## 7. Hinglish Glossary

- **RAG**: Notes search karke answer likhne ka tareeka.
- **LLM**: Ek smart AI model jo text samajhta hai.
- **Chunk**: Kisi bade document ka chhota tukda.
- **Embedding**: Text ko numbers me convert karna.
- **Vector Database**: Numbers data store karne wala database.
- **Hallucination**: AI ka galat answer confidently bolna.

## 8. Recap and Quick Check

### Recap
RAG helps an AI work like an open-book exam.
It retrieves stored notes, adds them to your prompt, and generates an answer.
RAG reduces hallucinations without changing model weights.

### Quick Check
1. What does RAG stand for?
2. True or False: RAG changes the AI model's weights.
3. Does chunking happen before or after a user asks a question?

<details>
<summary>Click to reveal answers</summary>

1. RAG stands for Retrieval-Augmented Generation.
2. False. RAG does NOT change the AI model's weights.
3. Chunking happens before a user asks a question, during the Preparation phase.
</details>
