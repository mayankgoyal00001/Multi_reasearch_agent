
import re


from agents import (
    research_agent,
    scraping_agent,
    writer_runnable,
    critic_runnable,
)


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


def extract_urls(text):
    urls = re.findall(r'https?://[^\s<>"\]\)]+', text)
    urls = [url.rstrip(".,;:") for url in urls]
    return list(dict.fromkeys(urls))


def main():
    research_question = input(
        "Enter your research question: "
    ).strip()

    if not research_question:
        print("Research question cannot be empty.")
        return

    # 1. Research
    print("\n[1/4] Researching...")
    research_result = research_agent.invoke({
        "messages": [{
            "role": "user",
            "content": (
                f"Research this topic: {research_question}. "
                "Include useful findings and source URLs."
            )
        }]
    })
    research_text = get_agent_response(research_result)

    # 2. Scrape webpages
    print("\n[2/4] Scraping webpages...")
    scraped_pages = []

    for url in extract_urls(research_text)[:3]:
        print(f"Scraping: {url}")

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

            scraped_pages.append(
                f"Source URL: {url}\n"
                f"{get_agent_response(result)}"
            )

        except Exception as error:
            print(f"Scraping failed: {error}")

    gathered_knowledge = (
        f"SEARCH RESULTS:\n{research_text}\n\n"
        "SCRAPED CONTENT:\n"
        + "\n\n".join(scraped_pages)
    )

    # 3. Write report
    print("\n[3/4] Writing report...")
    report = writer_runnable.invoke({
        "research_question": research_question,
        "gathered_knowledge": gathered_knowledge,
    })

    print("\n========== RESEARCH REPORT ==========\n")
    print(report)

    # 4. Critic review
    print("\n[4/4] Reviewing report...")
    review = critic_runnable.invoke({
        "report": report,
    })

    print("\n========== CRITIC REVIEW ==========\n")
    print(review)

    return {
        "research_question": research_question,
        "research_results": research_text,
        "scraped_pages": scraped_pages,
        "report": report,
        "review": review,
    }


if __name__ == "__main__":
    main()
