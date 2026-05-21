import sys

from openai import OpenAI, OpenAIError

from src.embedder import Embedder
from src.vector_store import VectorStore
from src.config import OPENAI_API_KEY, OPENAI_MODEL


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def retrieve(query: str, top_k: int = 5):
    embedder = Embedder()
    query_embedding = embedder.embed_text(query)

    store = VectorStore()
    results = store.search(query_embedding, top_k=top_k)
    store.close()

    return results


def build_context(results, max_chars: int = 3500):
    context_parts = []

    for i, result in enumerate(results, start=1):
        metadata = result["metadata"]

        source_file = metadata.get("source_file")
        page = metadata.get("page")
        chunk_index = metadata.get("chunk_index")
        content = result["content"]

        context_parts.append(
            f"Source {i}\n"
            f"File: {source_file}\n"
            f"Page: {page}\n"
            f"Chunk: {chunk_index}\n"
            f"Content: {content}"
        )

    context = "\n\n".join(context_parts)
    return context[:max_chars]


def generate_fallback_answer(results, max_chars: int = 900):
    if not results:
        return "I could not find this information in the uploaded documents."

    best_result = results[0]
    metadata = best_result["metadata"]
    source_file = metadata.get("source_file")
    page = metadata.get("page")
    content = best_result["content"].strip()

    source = f"{source_file}"
    if page:
        source += f", page {page}"

    return (
        "OpenAI answer generation is unavailable right now, so here is the most relevant "
        f"retrieved context from {source}:\n\n"
        f"{content[:max_chars]}"
    )


def generate_openai_answer(query: str, results):
    if not OPENAI_API_KEY:
        return generate_fallback_answer(results)

    context = build_context(results)

    client = OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = """
You are a helpful WhatsApp assistant for answering questions using the uploaded SFT knowledge base.
You support both English and Hinglish (Hindi written in English letters).

Language handling:
- Understand questions written in Hinglish like "mujhe courses ke bare mein batao" or "kya hai ye course".
- Always reply in simple English only, even if the user writes in Hinglish.

Greeting handling:
- If the message contains ONLY a greeting word (hi, hello, hey, hii, helo, namaste, namaskar, good morning, good evening) AND nothing else, reply exactly:
  "Hello! 👋 Welcome to SFT. How can I assist you today?"
- If the message contains a greeting AND a question together (like "hello mujhe courses batao"), IGNORE the greeting part and answer the question directly.

Course listing:
- If the user asks about courses in any form — "courses batao", "what courses", "kaun se courses hain", "course list", "available courses", "sft ke courses" — list ALL courses found in the context.
- Present each course on a new line as a bullet point.
- Do not summarize or skip any course. List every one found.

Core rules:
- Answer only from the provided context.
- Keep the answer short, clear, polite, and human-like.
- Use simple language that a learner or customer can easily understand.
- Do not print long document chunks.
- Do not copy unnecessary source text.
- Keep the answer within 3 to 6 lines.
- Use bullet points only when needed, and do not use more than 2 to 3 bullet points.

When information is not available:
- If the answer is not found in the provided context, reply exactly:
  "Our call adviser will connect with you shortly."

Want to know more?
- At the end of every answer (except pure greetings), add one relevant follow-up question on a new line.
- The follow-up question must start exactly with:
  Want to know more?
- The follow-up question must be related to the user's current question.
- The follow-up question must be answerable with yes or no.
- Do not add more than one follow-up question.

Example:
ISO 14064 is an international standard for greenhouse gas accounting and reporting.
It helps organizations quantify, report, and verify GHG emissions and removals.
ISO 14064-1 focuses on organization-level GHG inventories.

Want to know more? Would you like to understand ISO 14064-1 in simple terms?
"""

    user_prompt = f"""
Question:
{query}

Retrieved context:
{context}

Give a short and accurate answer.
"""

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.2
        )

        return response.output_text.strip()
    except OpenAIError as exc:
        return (
            f"OpenAI answer generation failed: {exc.__class__.__name__}. "
            "Using retrieved document context instead.\n\n"
            f"{generate_fallback_answer(results)}"
        )


def print_sources(results):
    print("\nSources checked:\n")

    for i, result in enumerate(results, start=1):
        metadata = result["metadata"]

        print(
            f"{i}. Source: {metadata.get('source_file')} | "
            f"Page: {metadata.get('page')} | "
            f"Chunk: {metadata.get('chunk_index')} | "
            f"Similarity: {result['similarity']:.4f}"
        )


def main():
    if len(sys.argv) < 2:
        print('Usage: python -m src.retriever "your question here"')
        return

    query = sys.argv[1]
    results = retrieve(query, top_k=5)

    print("\nAnswer:\n")
    print("=" * 80)

    answer = generate_openai_answer(query, results)
    print(answer)

    print("=" * 80)

    print_sources(results)


if __name__ == "__main__":
    main()
