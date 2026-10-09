
import re
from collections.abc import Callable, Sequence
from urllib.parse import urlparse


from agents import (
    research_agent,
    scraping_agent,
    writer_runnable,
    critic_runnable,
)


ProgressCallback = Callable[[str, str, str], None]


def get_agent_response(result):
    for message in reversed(result.get("messages", [])):
        if getattr(message, "type", None) == "ai" and message.content:
            content = message.content

            # Gemini may return a list of content blocks.
            if isinstance(content, list):
                parts = []

                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        parts.append(block)

                return "\n".join(parts)

            # Normal string response.
            if isinstance(content, str):
                return content

    return "No response generated."


def get_tool_responses(result):
    responses = []
    for message in result.get("messages", []):
        if getattr(message, "type", None) != "tool":
            continue
        content = getattr(message, "content", "")
        if isinstance(content, str):
            responses.append(content)
        elif isinstance(content, list):
            responses.extend(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
    return "\n".join(responses)


def extract_urls(text):
    urls = re.findall(r'https?://[^\s<>"\]\)]+', text)
    urls = [url.rstrip(".,;:") for url in urls]
    return list(dict.fromkeys(urls))


def _source_title(text, fallback_url):
    lines = text.splitlines()
    matching_line = next(
        (index for index, line in enumerate(lines) if fallback_url in line),
        None,
    )
    if matching_line is not None:
        candidates = lines[max(0, matching_line - 4):matching_line + 1]
        candidates.reverse()
    else:
        candidates = lines
    for line in candidates:
        title_match = re.match(r"(?i)^\s*Title:\s*(.+)$", line)
        if title_match:
            return title_match.group(1).strip()
    return urlparse(fallback_url).netloc or fallback_url


def run_research(
    research_question: str,
    extra_source_urls: Sequence[str] | None = None,
    on_progress: ProgressCallback | None = None,
):
    research_question = research_question.strip()
    if not research_question:
        raise ValueError("Research question cannot be empty.")

    def progress(stage, state, detail):
        if on_progress:
            on_progress(stage, state, detail)

    progress("research", "running", "Searching for relevant evidence.")
    try:
        research_result = research_agent.invoke({
            "messages": [{
                "role": "user",
                "content": (
                    f"Research this topic: {research_question}. "
                    "Include useful findings and source URLs."
                )
            }]
        })
    except Exception as error:
        progress("research", "error", f"Research failed: {error}")
        raise
    research_text = get_agent_response(research_result)
    search_results = get_tool_responses(research_result)
    progress("research", "complete", "Search findings collected.")

    source_urls = list(dict.fromkeys(
        [url.strip() for url in (extra_source_urls or []) if url.strip()]
        + extract_urls(research_text + "\n" + search_results)
    ))
    scraped_pages = []
    sources = []

    progress("scraping", "running", "Opening source pages.")
    for index, url in enumerate(source_urls):
        progress("scraping", "running", f"Scraping source {index + 1}/{len(source_urls)}: {url}")
        try:
            result = scraping_agent.invoke({
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Use the scrape_webpage tool to extract "
                        f"content from this URL: {url}"
                    )
                }]
            })
            page_text = get_agent_response(result)

            scraped_pages.append(
                f"Source URL: {url}\n"
                f"{page_text}"
            )
            sources.append({
                "title": _source_title(
                    page_text if "Title:" in page_text else search_results,
                    url,
                ),
                "url": url,
            })

        except Exception as error:
            scraped_pages.append(f"Source URL: {url}\nScraping failed: {error}")
            sources.append({"title": urlparse(url).netloc or url, "url": url})
            progress("scraping", "running", f"Could not scrape {url}: {error}")

    source_references = "\n".join(
        f"[{index}] {source['title']} — {source['url']}"
        for index, source in enumerate(sources, start=1)
    )

    gathered_knowledge = (
        f"SEARCH RESULTS:\n{research_text}\n\n"
        "SCRAPED CONTENT:\n"
        + "\n\n".join(scraped_pages)
        + "\n\nSOURCES:\n"
        + (source_references or "No source URLs were found.")
    )
    progress(
        "scraping",
        "complete",
        f"Collected {len(sources)} source reference(s).",
    )

    progress("writer", "running", "Drafting the evidence-based report.")
    try:
        report = writer_runnable.invoke({
            "research_question": research_question,
            "gathered_knowledge": gathered_knowledge,
        })
    except Exception as error:
        progress("writer", "error", f"Report writing failed: {error}")
        raise
    progress("writer", "complete", "Report draft completed.")

    progress("critic", "running", "Reviewing evidence, structure, and completeness.")
    try:
        review = critic_runnable.invoke({
            "report": report,
        })
    except Exception as error:
        progress("critic", "error", f"Quality review failed: {error}")
        raise
    progress("critic", "complete", "Quality review completed.")

    return {
        "research_question": research_question,
        "research_results": research_text,
        "scraped_pages": scraped_pages,
        "sources": sources,
        "report": report,
        "review": review,
    }


def main():
    research_question = input("Enter your research question: ").strip()
    if not research_question:
        print("Research question cannot be empty.")
        return

    result = run_research(
        research_question,
        on_progress=lambda stage, state, detail: print(
            f"[{stage}] {state}: {detail}"
        ),
    )
    print("\n========== RESEARCH REPORT ==========\n")
    print(result["report"])
    print("\n========== SOURCES ==========\n")
    for source in result["sources"]:
        print(f"- {source['title']}: {source['url']}")
    print("\n========== CRITIC REVIEW ==========\n")
    print(result["review"])


if __name__ == "__main__":
    main()
