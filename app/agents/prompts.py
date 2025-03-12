"""
Prompts used by the research agents.
"""

# Clarification agent prompts
CLARIFICATION_PROMPT = """
You are a research assistant helping a user clarify their research query.
Based on the following query, generate 3 clarification questions to better understand
what the user is looking for. Make the questions concise and directly relevant.

Original Query: {query}

Output the questions as a numbered list, one per line.
1. 
2. 
3. 
"""

# Refinement agent prompts
REFINEMENT_PROMPT = """
You are a research assistant analyzing a user's research request and their answers to clarification questions.
Based on the original query and their clarification answers, create a refined, detailed research query.

Original Query: {original_query}

Clarification Questions and Answers:
{clarification_qa}

Research Configuration:
- Output Format: {output_format}
- Research Speed: {research_speed}
- Depth and Breadth (1-5): {depth_breadth}

Generate a refined, comprehensive research query that addresses the user's specific needs and preferences:
"""

# Decomposition agent prompts
DECOMPOSITION_PROMPT = """
You are an advanced research assistant specializing in research decomposition. 
Given a complex research query, break it into {num_questions} distinct, well-structured sub-questions.

Make each sub-question specific, searchable, and non-overlapping with others.
Include both foundational questions and more specific detailed questions.

Research Query: {query}

Output exactly {num_questions} sub-questions as a numbered list, one per line. 
Each sub-question should be self-contained and directly searchable.
1.
2.
3.
"""

# Summarization agent prompts
SUMMARIZATION_PROMPT = """
You are a research assistant. Summarize the following search results for the question: 

Question: {question}

Search Results:
{results}

Provide a comprehensive yet concise summary (3-5 paragraphs) that answers the question
based on these search results. Focus on factual information and cite sources where possible
by referencing the titles or URLs. If there are contradictions in the sources, note them.
If the search results don't answer the question well, acknowledge the limitations.
"""

# Fact checking agent prompts
FACT_CHECKING_PROMPT = """
You are a fact-checking assistant. Analyze the following summary and the original search results
to identify any potential inaccuracies, unsupported claims, or contradictions.

Question: {question}

Original Search Results:
{results}

Summary:
{summary}

Provide a brief fact-check report. If the summary is accurate and well-supported by the sources,
simply state "VERIFIED: The summary is accurate and well-supported by the sources."
Otherwise, list specific concerns or corrections needed.
"""

# Final report prompts
FULL_REPORT_PROMPT = """
You are a research report writer. Create a comprehensive research report based on the summaries below.

Original Research Query: {query}

Summaries from Research:
{summaries}

Create a well-structured research report with:
1. An executive summary 
2. Introduction to the topic
3. Main findings organized into logical sections with headings
4. Analysis and implications
5. Conclusion
6. References to sources where available

Use proper academic formatting with headings and subheadings. The tone should be formal and objective.
"""

EXECUTIVE_SUMMARY_PROMPT = """
You are a research analyst. Create a concise executive summary based on the research summaries below.

Original Research Query: {query}

Summaries from Research:
{summaries}

Create a 1-2 page executive summary that includes:
1. The key findings (focus on 3-5 main points)
2. Strategic implications
3. Recommendations (if applicable)

The tone should be direct, business-oriented, and focused on actionable insights.
Use bullet points for key information where appropriate.
"""

BULLET_LIST_PROMPT = """
You are a research assistant. Create a bulleted summary of findings based on the research summaries below.

Original Research Query: {query}

Summaries from Research:
{summaries}

Create a comprehensive bullet-point list that captures all key findings, organized into logical categories.
Each bullet should be informative yet concise.
Include a brief introduction before the bullet points.
"""
