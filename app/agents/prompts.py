"""
Prompts used by the research agents.
"""

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

REFINEMENT_PROMPT = """
You are a research assistant analyzing a user's research request and their answers to clarification questions.
Based on the original query and their clarification answers, create a refined, detailed research query.

Original Query: {original_query}

Clarification Questions and Answers:
{clarification_qa}

Research Configuration:
- Output Format: {output_format}
- Research Speed: {research_speed} (fast = quicker but less comprehensive, deep = more thorough but takes longer)
- Depth and Breadth (1-5): {depth_breadth} (higher values mean more sub-questions, more search results, and longer reports)

Based on the depth and breadth setting of {depth_breadth}, this research will:
- Generate between 3-8 sub-questions (more at higher depth levels)
- Collect between 2-5 search results per question (more at higher depth levels)
- Create summaries ranging from 200-1000 words per question (longer at higher depth levels)
- Produce a final report between 2000-7000 words (longer at higher depth levels)

Generate a refined, comprehensive research query that addresses the user's specific needs and preferences:
"""

DECOMPOSITION_PROMPT = """
You are an advanced research assistant specializing in research decomposition. 
Given a complex research query, break it into {num_questions} distinct, well-structured sub-questions.

The number of sub-questions ({num_questions}) has been determined based on the user's selected research depth and breadth.
Higher depth settings result in more questions to provide a more comprehensive research report.

Make each sub-question specific, searchable, and non-overlapping with others.
Include both foundational questions and more specific detailed questions.
Ensure the sub-questions cover different aspects of the topic, including:
- Fundamental concepts and definitions
- Historical context and development
- Current state and recent developments
- Different perspectives and viewpoints
- Practical applications and real-world examples
- Future trends and implications
- Challenges and limitations
- Comparative analysis with related topics

Research Query: {query}

Output exactly {num_questions} sub-questions as a numbered list, one per line. 
Each sub-question should be self-contained and directly searchable.
1.
2.
3.
"""

SUMMARIZATION_PROMPT = """
You are a research assistant. Summarize the following search results for the question: 

Question: {question}

Search Results:
{results}

Provide a comprehensive and detailed summary that thoroughly answers the question
based on these search results. Include as much specific information as possible, including:
- Key facts, statistics, and data points
- Different perspectives and viewpoints on the topic
- Historical context and background information
- Current trends and developments
- Future projections or implications

Focus on factual information and cite sources where possible by referencing the titles or URLs. 
If there are contradictions in the sources, analyze and explain these contradictions.
If the search results don't answer the question well, acknowledge the limitations but still provide
the most comprehensive analysis possible based on available information and general knowledge of the topic.

Your summary should be detailed enough to stand alone as a mini-report on this specific aspect of the research.
Aim for at least 500-750 words in your summary.

IMPORTANT: Be thorough and comprehensive. Include ALL relevant information from the search results.
This summary will be used as a key component in generating the final research report.
"""

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

FULL_REPORT_PROMPT = """
You are a research report writer. Create an extremely comprehensive and detailed research report based on the summaries below.

Original Research Query: {query}

Summaries from Research:
{summaries}

CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. You MUST use ALL of the information provided in ALL of the summaries to create a comprehensive report.
2. Do not omit any significant information from the summaries.
3. Your report MUST be at least 5000 words in length, and ideally 6000-7000 words.
4. If you find yourself running out of space, prioritize including ALL the factual information from the summaries.
5. Your report should be a thorough synthesis of ALL the research summaries provided.
6. DO NOT truncate or cut off your report before including all key information.
7. DO NOT just provide an outline or table of contents - you must write the COMPLETE REPORT with all sections fully developed.
8. Write the actual content for each section, not just section headings.
9. PROVIDE DEFINITIVE CONCLUSIONS - do not just present both sides without taking a position.

Create a well-structured, in-depth research report with:
1. An executive summary (500-750 words)
2. Detailed introduction to the topic (750-1000 words)
3. Main findings organized into logical sections with headings and subheadings (2000-3000 words)
   - Include at least 4-6 main sections
   - Each main section should have 2-3 subsections
   - Provide detailed analysis in each section
   - Include specific examples, data points, and evidence from the summaries
   - Discuss implications of each finding in depth
4. Comprehensive analysis and implications section (1000-1500 words)
   - Include economic, social, political, and technological implications as relevant
   - Discuss short-term and long-term implications
   - Consider different stakeholder perspectives
5. Detailed conclusion with recommendations and a firm position (750-1000 words)
   - Take a clear stance on the research question
   - Provide strong, definitive answers based on the evidence
   - Make specific, actionable recommendations
   - Avoid vague, equivocal, or overly balanced statements
   - Clearly state "the answer is X because of Y evidence"
6. Extensive references section

Use proper academic formatting with headings and subheadings. The tone should be formal, objective, and scholarly, but conclusions should be definitive. Aim for a total report length of 5000-7000 words.

IMPORTANT: You MUST include a "References" section at the end of the report that lists all sources mentioned in the summaries. Format each reference properly with the title and URL. Cite these references within the text of your report using [Source Title] format.

FINAL CHECK: Before submitting your report, verify that:
1. You have included ALL key information from ALL summaries
2. Your report is at least 5000 words in length
3. You have not truncated or cut off any sections
4. All sections are fully developed with detailed information
5. You have included all necessary references
6. You have written the COMPLETE REPORT, not just an outline or table of contents
7. Your conclusions are DEFINITIVE, not ambiguous or overly balanced

Remember: Your report MUST be comprehensive and include ALL the key information from the summaries. Do not leave out important details or findings. Most importantly, provide clear, definitive conclusions and recommendations that directly answer the original research query.
"""

EXECUTIVE_SUMMARY_PROMPT = """
You are a research analyst. Create a detailed executive summary based on the research summaries below.

Original Research Query: {query}

Summaries from Research:
{summaries}

CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. You MUST use ALL of the information provided in ALL of the summaries to create a comprehensive executive summary.
2. Do not omit any significant information from the summaries.
3. Your executive summary MUST be at least 1500 words in length, and ideally 2000-2500 words.
4. If you find yourself running out of space, prioritize including ALL the key factual information from the summaries.
5. DO NOT truncate or cut off your summary before including all key information.
6. PROVIDE DEFINITIVE CONCLUSIONS - do not just present both sides without taking a position.

Create a comprehensive 3-4 page executive summary (1500-2500 words) that includes:
1. The key findings (focus on 5-7 main points with detailed explanation of each)
2. Strategic implications (discuss short-term and long-term implications in detail)
3. Recommendations (provide specific, actionable recommendations with rationale)
   - Take a clear stance on the research question
   - Provide strong, definitive answers based on the evidence
   - Make specific, actionable recommendations
   - Avoid vague, equivocal, or overly balanced statements
   - Clearly state "the answer is X because of Y evidence"
4. References to key sources

The tone should be direct, business-oriented, and focused on actionable insights with definitive conclusions.
Use bullet points for key information where appropriate, but provide detailed explanations for each point.

IMPORTANT: You MUST include a "References" section at the end of the summary that lists all sources mentioned in the summaries. Format each reference properly with the title and URL. Cite these references within the text of your summary using [Source Title] format.

FINAL CHECK: Before submitting your executive summary, verify that:
1. You have included ALL key information from ALL summaries
2. Your summary is at least 1500 words in length
3. You have not truncated or cut off any sections
4. All sections are fully developed with detailed information
5. You have included all necessary references
6. Your conclusions are DEFINITIVE, not ambiguous or overly balanced

Most importantly, provide clear and definitive conclusions that directly answer the original research query.
"""

BULLET_LIST_PROMPT = """
You are a research assistant. Create a detailed bulleted summary of findings based on the research summaries below.

Original Research Query: {query}

Summaries from Research:
{summaries}

CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. You MUST use ALL of the information provided in ALL of the summaries to create a comprehensive bullet-point report.
2. Do not omit any significant information from the summaries.
3. Your report MUST be at least 2000 words in length, and ideally 2500-3000 words.
4. If you find yourself running out of space, prioritize including ALL the key factual information from the summaries.
5. DO NOT truncate or cut off your report before including all key information.
6. PROVIDE DEFINITIVE CONCLUSIONS - do not just present both sides without taking a position.

Create a comprehensive and detailed bullet-point report (2000-3000 words) that captures all key findings, organized into logical categories.
Each main category should have:
1. A brief introduction explaining its relevance (100-150 words)
2. At least 5-7 detailed bullet points
3. Each bullet point should be substantive (50-100 words) with specific information, not just a brief statement
4. Sub-bullets where appropriate to provide additional detail

Include a thorough introduction (300-500 words) before the bullet points explaining the context and importance of the research.
Conclude with a summary section (300-500 words) that synthesizes the key findings and provides definitive conclusions:
- Take a clear stance on the research question
- Provide strong, definitive answers based on the evidence
- Make specific, actionable recommendations
- Avoid vague, equivocal, or overly balanced statements
- Clearly state "the answer is X because of Y evidence"

IMPORTANT: You MUST include a "References" section at the end that lists all sources mentioned in the summaries. Format each reference properly with the title and URL. Cite these references within your bullet points using [Source Title] format.

FINAL CHECK: Before submitting your bullet-point report, verify that:
1. You have included ALL key information from ALL summaries
2. Your report is at least 2000 words in length
3. You have not truncated or cut off any sections
4. All sections are fully developed with detailed information
5. You have included all necessary references
6. Your conclusions are DEFINITIVE, not ambiguous or overly balanced

Most importantly, provide clear and definitive conclusions that directly answer the original research query.
"""
