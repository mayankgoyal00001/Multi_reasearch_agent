from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search, scrape_webpage
import os

from dotenv import load_dotenv
load_dotenv()


llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
    temperature=0,
    timeout=30,
    max_retries=1,
)

research_agent = create_agent(
    model=llm,
    tools=[web_search],
    system_prompt="""
    You are a web research agent.

    Your responsibilities:
    1. Understand the user's research question.
    2. Use the web_search tool to find relevant information.
    3. Identify useful results and source URLs.
    4. Summarize the findings clearly.
    5. Do not invent sources or facts.
    """
)

# Agent 2: Web Scraping Agent
scraping_agent = create_agent(
    model=llm,
    tools=[scrape_webpage],
    system_prompt="""
    You are a webpage scraping agent.

    Your responsibilities:
    1. Identify the webpage URL provided by the user.
    2. Use the scrape_webpage tool to extract its content.
    3. Return the extracted information in a clear format.
    4. Do not invent content if a page cannot be accessed.
    5. Do not claim that you verified information beyond
       what the extracted webpage content supports.
    """
)

writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        You are a senior research writer specializing in producing
        high-quality, evidence-based research reports.

        Your task is to transform the knowledge collected by research
        agents and web scraping agents into a comprehensive report.

        Follow these rules:

        1. Understand the research question and its objectives.
        2. Combine all relevant information into one coherent report.
        3. Organize the report using the following structure:

           - Title
           - Executive Summary
           - Introduction and Background
           - Key Findings
           - Detailed Analysis
           - Evidence and Supporting Examples
           - Limitations and Knowledge Gaps
           - Conclusion
           - References and Source URLs

        4. Remove redundant information and resolve repetition.
        5. Maintain a logical flow between sections.
        6. Use a professional, objective, research-oriented tone.
        7. Distinguish verified facts from assumptions and opinions.
        8. Never invent statistics, quotations, citations, or sources.
        9. If sources disagree, explain the disagreement instead
           of silently choosing one.
        10. Identify insufficient evidence and missing information.
        11. Cite supplied sources with their [number] where relevant.
        12. Preserve source URLs in the references section so claims
            can be checked. Do not invent source titles or URLs.
        13. Do not claim that you independently verified sources
            unless the supplied evidence supports that claim.

        Your goal is to produce the strongest report possible
        using the available evidence.

        Return the complete report in Markdown.
        """
    ),
    (
        "human",
        """
        Topic of Research:
        {research_question}

        Knowledge Gathered by Research Agents:
        {gathered_knowledge}


        Write a comprehensive research report using the
        instructions above.
        """
    )
])





critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        You are a senior research reviewer with extensive experience
        evaluating academic and professional research reports.

        A junior researcher has submitted a report for your review.

        Your responsibility is to critically evaluate the entire
        report, assign scores, and provide constructive feedback.

        Review the report using these criteria:

        1. Research Relevance (0-10)
           Does the report answer the original research question?

        2. Evidence and Source Quality (0-10)
           Are important claims supported by the supplied evidence?
           Are sources identifiable and relevant?

        3. Accuracy and Reliability (0-10)
           Are there unsupported claims, contradictions, misleading
           statements, or potentially fabricated details?

        4. Depth of Analysis (0-10)
           Does the report analyze the findings or merely summarize
           information? Does it compare different perspectives?

        5. Structure and Coherence (0-10)
           Is the report logically organized, readable, and consistent?

        6. Completeness (0-10)
           Are important aspects, limitations, and counterarguments
           missing?

        7. Writing Quality (0-10)
           Is the writing clear, professional, concise, and precise?

        Review instructions:

        - Read the entire report before giving your assessment.
        - Compare the report against the original research question
          and the supplied research evidence.
        - Identify specific weaknesses and explain why they matter.
        - Cite the relevant report section or quote a short phrase
          when identifying a problem.
        - Distinguish confirmed errors from claims that merely
          lack sufficient evidence.
        - Do not penalize the report for facts that cannot be
          assessed using the supplied material without explaining
          this limitation.
        - Do not invent sources or facts to justify criticism.
        - Recognize strong sections as well as weaknesses.
        - Give specific, actionable recommendations that the writer
          can implement.
        - Prioritize critical factual and evidentiary problems
          over stylistic improvements.

        Scoring rules:

        - 9-10: Excellent
        - 7-8: Good, with minor improvements needed
        - 5-6: Adequate, but significant improvements are needed
        - 3-4: Weak, with major issues
        - 0-2: Seriously deficient

        Calculate the overall score as the arithmetic mean of the
        seven category scores, rounded to one decimal place.

        Final verdict:
        - 9.0-10.0: Excellent
        - 7.0-8.9: Acceptable with minor revisions
        - 5.0-6.9: Major revisions required
        - Below 5.0: Rewrite required

        Be rigorous, fair, evidence-driven, and constructive,
        like a senior researcher mentoring a junior researcher.
        """
    ),
    (
        "human",
        """

        Complete Report Submitted by the Writer:
        {report}

        Review the entire report and return your assessment using
        this structure:

        ## 1. Overall Score
        - Score out of 10
        - Final verdict
        - Brief justification

        ## 2. Scorecard
        Score each of the seven criteria out of 10 and explain each
        score briefly.

        ## 3. Strengths
        Identify the strongest aspects of the report.

        ## 4. Critical Issues
        Identify factual, evidentiary, logical, or completeness issues.
        Explain the impact and reference relevant sections.

        ## 5. Missing Information
        Identify important questions or evidence the report lacks.

        ## 6. Actionable Feedback
        List prioritized changes the writer should make.

        ## 7. Final Recommendation
        State whether the report should be accepted, revised, or
        rewritten, and explain the next steps.
        """
    )
])

writer_runnable = writer_prompt | llm | StrOutputParser()

# Runnable for the Critic Agent
critic_runnable = critic_prompt | llm | StrOutputParser()

