from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
from dotenv import load_dotenv
from rich import print

load_dotenv()


@tool
def web_search(query: str) -> str:
    """
    Perform a web search for recent and reliable information using Tavily API and return the titles ,Urls and snippets.
    """
    tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    results = tavily_client.search(query, max_results=5)
    
    out=[]

    for r in results['results']:
        out.append(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['content']}\n")
        
    return "\n---\n".join(out)

# print(web_search.invoke("latest advancements in AI research"))


@tool
def scrape_webpage(url: str) -> str:
    """Fetch a webpage and extract its readable text."""

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove content that usually isn't useful for research
        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside"
        ]):
            tag.decompose()

        # Extract the page title
        title = (
            soup.title.get_text(strip=True)
            if soup.title
            else "No title found"
        )

        # Extract headings and paragraphs
        content = soup.find_all([
            "h1", "h2", "h3", "p", "li"
        ])

        text_content = "\n".join(
            element.get_text(" ", strip=True)
            for element in content
            if element.get_text(strip=True)
        )

        return f"Title: {title}\n\nContent:\n{text_content}"

    except requests.RequestException as e:
        return f"Error fetching webpage: {e}"


