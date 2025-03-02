#!/usr/bin/env python3
"""
Claude Prompter - Generate insights from journal entries using Claude AI
"""

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
        system_prompt = """You are an expert therapist, life coach, and personal assistant. 
Your job is to analyze the user's journal entries and provide thoughtful, 
personalized insights, advice, and suggestions. Be empathetic, insightful, 
and practical in your analysis. Focus on identifying patterns, 
highlighting strengths, suggesting improvements, and offering actionable advice.
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
<journal_entries>
{journal_xml}
</journal_entries>

<instructions>
Based on my journal entries above, please provide:

1. General insights about me, my patterns, and my current state of mind
2. Any suggestions for preparations or next steps based on my apparent plans or goals
3. Advice for things I might be overlooking or should consider
4. Any other observations that might be helpful for my growth and well-being

After providing these insights, please create a journal entry template for me to fill out in order to provide context that I haven't yet written in the journal (e.g. my relation to specific names I've mentioned), as well as any other information that would be helpful for your next analysis. This should be a one-off entry where I answer specific questions you have, not a generic template. Format this template in Markdown with clear sections and spaces for my responses.

Please format your entire response in Markdown, with clear sections and thoughtful analysis.
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
            
            logger.debug("Sending request to Claude API")
            logger.info("Waiting for Claude's response (this may take a minute)...")
            
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000
            )
            
            logger.debug("Received response from Claude API")
            
            usage = getattr(response, 'usage', None)
            if usage:
                logger.debug(f"Token usage - Input: {usage.input_tokens}, Output: {usage.output_tokens}")
            
            content = response.content[0].text
            logger.debug(f"Response length: {len(content)} characters")
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting insights from Claude: {str(e)}")
            logger.debug(traceback.format_exc())
            return None