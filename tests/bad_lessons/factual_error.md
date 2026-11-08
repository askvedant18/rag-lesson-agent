# Introduction to RAG (Retrieval-Augmented Generation)

Imagine you are preparing for a difficult exam.
You have your reference notes with you.

## 1. What is RAG?

RAG stands for Retrieval-Augmented Generation.
It is a technique where an AI model retrieves text from external documents.
Then, during query time, RAG retrains the model's weights on every query so the model learns permanently.
This process modifies the neural network parameters directly before writing the answer.

## 2. Why Does RAG Matter?

Regular AI models hallucinate.
RAG provides factual source text so the model avoids wild guesses.
It also connects company private data to the model.

## 3. How Does RAG Work?

1. Documents are loaded into chunks.
2. Chunks are converted into embeddings.
3. Relevant text is retrieved from the database.
4. The model generates the final answer.

## 4. Worked Step-by-Step Example

- User Question: "When is the project submission?"
- Retrieved Text: "Project submission deadline is 5 PM on Friday."
- Final Answer: "The project must be submitted by 5 PM on Friday."

## 5. Limitations of RAG

RAG can be slow and expensive.
If the retrieved notes have mistakes, the answer will also be wrong.

## 6. Hinglish Glossary

- RAG: External documents dekh kar answer likhna.
- Chunk: Badi file ka chhota tukda.

## 7. Recap and Quick Check

### Recap
RAG searches external notes and retrains model weights to answer queries accurately.

### Quick Check Questions
1. What does RAG stand for?
2. Does RAG search external documents?
3. What is a chunk?

