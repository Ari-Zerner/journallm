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
        
    def load_prompt(self, prompt_file: str, variable_dict: Dict[str, str] = {}) -> str:
        """
        Load a prompt from a file and substitute any variables.

        Args:
            prompt_file: Path to the prompt template file
            variable_dict: Dictionary mapping variable names to values to substitute

        Returns:
            str: The prompt with all variables substituted

        Note:
            Variables in the prompt file should be in the format {{variable_name}}.
            If variable_dict values themselves contain {{key}} patterns, behavior is undefined.
        """
        with open(prompt_file, 'r') as f:
            prompt = f.read()
            for key, value in variable_dict.items():
                prompt = prompt.replace(f"{{{key}}}", value)
            return prompt
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for Claude
        
        Returns:
            str: The system prompt
        """
        system_prompt = self.load_prompt('role.prompt.txt')
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
        
        prompt = self.load_prompt('create_report.prompt.txt', {
            'journal_xml': journal_xml
        })
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