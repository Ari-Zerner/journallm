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
        
def load_prompt(prompt_file: str) -> str:
    with open(prompt_file, 'r') as f:
        return f.read()

MODEL = "claude-sonnet-4-0"
SYSTEM_PROMPT = load_prompt('role.prompt.txt')
REPORT_PROMPT = load_prompt('create_report.prompt.txt')

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

    def get_report(self, journal: str, cache_for_interactive: bool = False) -> Optional[str]:
        """
        Get insights from Claude based on journal entries
        
        Args:
            journal: Journal entries
            cache_for_interactive: Whether to cache the journal and initial prompt (more expensive initially, cheaper repeated prompting for interactive mode)
            
        Returns:
            str or None: Claude's response with insights
        """
        try:
            logger.debug("Preparing to send request to Claude")
            assistant_prefill = f"# JournalLM Advice for {datetime.datetime.now().strftime('%A, %B %d, %Y')}"
            
            logger.debug("Sending request to Claude API")
            logger.info("Waiting for Claude's response (this may take a minute)...")
            
            MAX_JOURNAL_TOKENS = 200000 - 10000 # context window is 200k, leave 10k for prompt and output
            journal_token_count = self.client.messages.count_tokens(
                model=MODEL,
                messages=[{"role": "user", "content": journal}]
            ).input_tokens
            if journal_token_count > MAX_JOURNAL_TOKENS:
                logger.info(f"Journal is too long ({journal_token_count} tokens), truncating oldest entries")
                truncation_index = int(len(journal) * (1 - MAX_JOURNAL_TOKENS / journal_token_count))
                journal = '...older entries truncated...\n\n' + journal[truncation_index:]
                logger.debug(f"Truncated {truncation_index} characters, now {len(journal)} characters")
                
            report_prompt_content = {"type": "text", "text": REPORT_PROMPT, "cache_control": {"type": "ephemeral"}} if cache_for_interactive else REPORT_PROMPT
            
            response = self.client.messages.create(
                model=MODEL,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": f"<journal>\n{journal}\n</journal>"},
                    {"role": "user", "content": report_prompt_content},
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

    def start_interactive_session(self, journal_xml: str, initial_report: Optional[str] = None) -> None:
        """Start an interactive session with Claude"""
        try:
            messages = [{"role": "user", "content": journal_xml}]
            
            # If we have a report, treat it as assistant's response to report prompt
            if initial_report:
                messages.append({"role": "user", "content": REPORT_PROMPT})
                messages.append({"role": "assistant", "content": initial_report})
            
            print("\nEntering interactive mode. Type 'exit' to end the session.")
            
            while True:
                user_input = input("\n> ").strip()
                if user_input.lower() == 'exit':
                    break
                
                # Cache after each user input; this is a cost savings with even one follow-up prompt
                messages.append({"role": "user", "content": [
                    {"type": "text", "text": user_input, "cache_control": {"type": "ephemeral"}}
                ]})
                
                print(f"\nThinking...")
                
                response = self.client.messages.create(
                    model=MODEL,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                    max_tokens=4000
                )
                
                content = response.content[0].text
                messages.append({"role": "assistant", "content": content})
                print(f"\n{content}")
                
        except KeyboardInterrupt:
            print("\nExiting interactive mode...")
        except Exception as e:
            logger.error(f"Error in interactive session: {str(e)}")
            logger.debug(traceback.format_exc())