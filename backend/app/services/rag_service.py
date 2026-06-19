import os
import re
import chromadb
from openai import AzureOpenAI
from app.core.config import settings

# NCERT structure:
# Grades 6-10 → single "Science" textbook (biology/chemistry/physics merged)
# Grades 11-12 → separate Physics, Chemistry, Biology textbooks
_MATH_ALIASES = {"math", "maths", "mathematics"}
_SCIENCE_ALIASES = {"science", "sci", "general science", "natural science"}
_PHYSICS_ALIASES = {"physics", "phy"}
_CHEMISTRY_ALIASES = {"chemistry", "chem"}
_BIOLOGY_ALIASES = {"biology", "bio", "life science", "life sciences"}

# All possible subject names we try in order when an exact match fails
_SUBJECT_FALLBACK_ORDER = ["science", "biology", "chemistry", "physics"]


def _get_azure_client() -> AzureOpenAI:
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        raise RuntimeError("Azure OpenAI is not configured")

    endpoint = settings.azure_openai_endpoint.rstrip("/")
    if endpoint.endswith("/openai/v1"):
        endpoint = endpoint[:-10]
    elif endpoint.endswith("/openai"):
        endpoint = endpoint[:-7]

    return AzureOpenAI(
        api_version=settings.azure_openai_api_version,
        azure_endpoint=endpoint,
        api_key=settings.azure_openai_api_key,
    )


def _normalize_subject(subject: str, grade_num: int) -> str:
    """
    Map a classroom subject label to the ChromaDB collection subject string.

    For grades 6-10, NCERT uses a combined Science book, so physics/biology/
    chemistry all map to 'science'.  For grades 11-12 the books are separate.
    """
    sub = subject.lower().strip()
    # Remove common suffixes like "(Class 9)" from subject labels
    sub = re.sub(r"\(.*\)", "", sub).strip()

    if sub in _MATH_ALIASES:
        return "mathematics"

    if sub in _SCIENCE_ALIASES:
        return "science"

    if sub in _PHYSICS_ALIASES:
        # Grades 6-10: no separate physics book → use combined science
        return "science" if grade_num <= 10 else "physics"

    if sub in _CHEMISTRY_ALIASES:
        return "science" if grade_num <= 10 else "chemistry"

    if sub in _BIOLOGY_ALIASES:
        return "science" if grade_num <= 10 else "biology"

    # Generic fallback: underscore-normalise whatever label we got
    return re.sub(r"[\s\-]+", "_", sub)


def get_chroma_collection_name(grade: str | None, subject: str | None) -> str | None:
    """Return the ChromaDB collection name for a given grade and subject label."""
    if not grade or not subject:
        return None

    # Extract the grade number (e.g. "Class 10" → 10)
    grade_match = re.search(r"\d+", str(grade))
    if not grade_match:
        return None
    grade_num = int(grade_match.group(0))

    normalized_sub = _normalize_subject(str(subject), grade_num)
    return f"class_{grade_num}_{normalized_sub}"


def _candidate_collection_names(grade: str, subject: str) -> list[str]:
    """
    Return an ordered list of collection names to try for the given grade/subject.
    The primary name is tried first; fallbacks are included so we always find
    *something* relevant even when the exact collection is missing.
    """
    grade_match = re.search(r"\d+", str(grade))
    if not grade_match:
        return []
    grade_num = int(grade_match.group(0))

    primary = get_chroma_collection_name(grade, subject)
    candidates = [primary] if primary else []

    # Add science/subject fallbacks
    for fallback_sub in _SUBJECT_FALLBACK_ORDER:
        name = f"class_{grade_num}_{fallback_sub}"
        if name not in candidates:
            candidates.append(name)

    return candidates


def retrieve_context(query: str, grade: str | None, subject: str | None, limit: int = 5) -> str:
    if not query or not query.strip():
        return ""

    if not grade or not subject:
        print(f"[rag-service] grade='{grade}' subject='{subject}' — skipping RAG (no context).")
        return ""

    # Get absolute path to backend/chroma_db
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../chroma_db"))

    try:
        chroma_client = chromadb.PersistentClient(path=db_path)
        available = {col.name for col in chroma_client.list_collections()}
    except Exception as e:
        print(f"[rag-service] Failed to open ChromaDB at '{db_path}': {e}")
        return ""

    # Try candidates in order until we find one that exists
    collection = None
    used_collection_name = None
    for candidate in _candidate_collection_names(grade, subject):
        if candidate in available:
            try:
                collection = chroma_client.get_collection(name=candidate)
                used_collection_name = candidate
                break
            except Exception:
                continue

    if collection is None:
        primary = get_chroma_collection_name(grade, subject)
        print(
            f"[rag-service] No collection found for grade='{grade}' subject='{subject}' "
            f"(tried '{primary}' + fallbacks). Available: {sorted(available)}"
        )
        return ""

    print(f"[rag-service] Using collection '{used_collection_name}' for grade='{grade}' subject='{subject}'")

    try:
        # Generate embedding for the query using Azure OpenAI
        client = _get_azure_client()
        embed_res = client.embeddings.create(
            input=[query],
            model="text-embedding-3-small",
        )
        query_embedding = embed_res.data[0].embedding

        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
        )

        # Format the retrieved documents
        retrieved_texts = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else []

            for idx, doc in enumerate(docs):
                meta = metadatas[idx] if idx < len(metadatas) else {}
                chapter_title = meta.get("chapter_title", "Unknown Chapter")
                page = meta.get("page_number", "Unknown Page")
                chapter_num = meta.get("chapter_number", "")

                source_label = f"Chapter {chapter_num}" if chapter_num else "Preliminaries"
                retrieved_texts.append(
                    f"[Source: {source_label} '{chapter_title}', Page {page}]\n{doc}"
                )

        return "\n\n---\n\n".join(retrieved_texts)

    except Exception as e:
        print(f"[rag-service] Error retrieving context: {e}")
        return ""
