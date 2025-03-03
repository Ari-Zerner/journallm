#!/usr/bin/env python3
"""
Claude Prompter - Generate insights from journal entries using Claude AI
"""

import datetime
import os
import logging
from typing import Optional, Dict
import traceback

import anthropic

# Set up logging
logger = logging.getLogger(__name__)

class ClaudePrompter:
    """
    Class for generating insights from journal entries using Claude AI
    """
    def __init__(self, api_key: str):
        """
        Initialize the ClaudePrompter
        
        Args:
            api_key: Anthropic API key
        """
        self.api_key = api_key
        
        logger.debug("Initializing ClaudePrompter")
        logger.debug(f"API key length: {len(api_key)} characters")
        
        self.client = anthropic.Client(api_key=api_key)
        logger.debug("Anthropic client initialized")
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for Claude
        
        Returns:
            str: The system prompt
        """
        system_prompt = """You are JournalLM, an expert life coach and personal assistant.
Your job is to analyze journal entries and provide thoughtful, personalized insights, advice, and suggestions.
Be insightful, direct, empathetic, and practical in your analysis.
Focus on identifying patterns, suggesting improvements, and offering actionable advice.
"""
        logger.debug(f"System prompt length: {len(system_prompt)} characters")
        return system_prompt

    def get_user_prompt(self, journal_xml: str) -> str:
        """
        Construct the user prompt for Claude
        
        Args:
            journal_xml: XML representation of the journal entries
            
        Returns:
            str: The user prompt including the journal data
        """
        logger.debug(f"Creating user prompt with journal XML of {len(journal_xml)} bytes")
        
        prompt = f"""
{journal_xml}

<response_format>
Format your entire response in Markdown, with clear sections.
Because the whole response is markdown, there's no need to include ```markdown blocks.
Include a blank line after each section heading and before each bulleted/numbered list.
</response_format>

<instructions>
Based on my journal entries above, please write a report with the following sections.
Be thoughtful, thorough, and honest in your analysis.

## Executive Summary
Give me an executive summary for today consisting of two short paragraphs (or less).
This should contain a brief summary of recent developments and things to be mindful of in general,
but the main focus of the executive summary is actionable advice I can follow today.

## General Insights
Describe what you notice about my patterns, strengths, weaknesses, state of mind, trajectory, etc.
Try to focus on non-obvious insights, but remember that what's obvious to you may not be obvious to me.

## Specific Suggestions
Suggest preparations or next steps based on my apparent plans or goals.
The goal here is to think as if you had 10x the agency you do, and impart that agency to me.
Specificity is good! Include high-level strategies where appropriate, but suggest ways to break them down into actionable steps.

## Overlooked Considerations
Point out things I might be overlooking or should consider.
I know I have blind spots, and I want you to help me see them.

## Other Observations
This section is a catch-all for anything that might be helpful for my growth and well-being but doesn't fit into the other sections.

## Context for JournalLM
A journal entry template for me to fill out in order to provide missing context (e.g. my relation to specific names I've mentioned),
as well as any other information that would be helpful for your next analysis.
This should be a one-off entry where I answer specific questions you have, not a generic template. Make it as convenient as possible for me to fill out:
   - don't ask for information you can already find in the journal entries
   - have a clearly defined space for each answer
   - aim for questions with short, concrete answers when possible
   - avoid making me write out long answers unless absolutely necessary
   - leave blank spaces rather than including placeholder text
</instructions>
"""
        logger.debug(f"User prompt created, total length: {len(prompt)} characters")
        return prompt

    def get_insights(self, journal_xml: str) -> Optional[str]:
        """
        Get insights from Claude based on journal entries
        
        Args:
            journal_xml: XML representation of the journal entries
            
        Returns:
            str or None: Claude's response with insights
        """
        try:
            logger.debug("Preparing to send request to Claude")
            system_prompt = self.get_system_prompt()
            user_prompt = self.get_user_prompt(journal_xml)
            assistant_prefill = f"# JournalLM Advice for {datetime.datetime.now().strftime('%B %d, %Y')}"
            
            logger.debug("Sending request to Claude API")
            logger.info("Waiting for Claude's response (this may take a minute)...")
            
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": assistant_prefill}
                ],
                max_tokens=4000
            )
            
            logger.debug("Received response from Claude API")
            
            usage = getattr(response, 'usage', None)
            if usage:
                logger.debug(f"Token usage - Input: {usage.input_tokens}, Output: {usage.output_tokens}")
            
            content = assistant_prefill + response.content[0].text
            logger.debug(f"Response length: {len(content)} characters")
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting insights from Claude: {str(e)}")
            logger.debug(traceback.format_exc())
            return None