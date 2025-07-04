"""
Flexible LLM Classifier - src/llm_classifier.py
No prescriptive categories, lets LLM understand naturally
"""
import json
import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class FlexibleLLMClassifier:
    """LLM classifier that doesn't constrain to specific types"""
    
    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'openai')
        self._setup_client()
    
    def _setup_client(self):
        """Initialize LLM client based on provider"""
        if self.provider == 'openai':
            import openai
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.client = openai
            self.model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
        elif self.provider == 'anthropic':
            from anthropic import Anthropic
            self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229')
        elif self.provider == 'ollama':
            self.base_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
            self.model = os.getenv('OLLAMA_MODEL', 'llama2')
        elif self.provider == 'groq':
            from groq import Groq
            self.client = Groq(api_key=os.getenv('GROQ_API_KEY'))
            self.model = os.getenv('GROQ_MODEL', 'mixtral-8x7b-32768')
    
    async def analyze_element(self, element_data: Dict[str, Any], 
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze element with full flexibility"""
        
        prompt = self._build_flexible_prompt(element_data, context)
        
        try:
            response = await self._query_llm(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._mock_response(element_data)  # Fallback for testing
    
    def _build_flexible_prompt(self, element_data: Dict[str, Any], 
                              context: Optional[Dict[str, Any]] = None) -> str:
        """Build unconstrained prompt for natural understanding"""
        
        # Element details
        element_desc = f"""
Element Details:
- Tag: <{element_data.get('tagName', 'unknown')}>
- ID: {element_data.get('id', 'none')}
- Classes: {element_data.get('className', 'none')}
- Size: {element_data.get('rect', {}).get('width', 0)}x{element_data.get('rect', {}).get('height', 0)} pixels
- Position: ({element_data.get('rect', {}).get('x', 0)}, {element_data.get('rect', {}).get('y', 0)})
- Text preview: {element_data.get('text', 'No text')[:200]}
- Clickable: {element_data.get('clickable', False)}
- Href: {element_data.get('href', 'none') if element_data.get('clickable') else 'N/A'}
"""
        
        # Add context if available
        context_desc = ""
        if context:
            if context.get('parent'):
                context_desc += f"\nParent element: {context['parent'].get('understanding', 'Unknown')}"
            if context.get('siblings'):
                context_desc += f"\nSibling elements: {', '.join(s.get('tag', '') for s in context['siblings'][:3])}"
            if context.get('children'):
                context_desc += f"\nChild elements: {', '.join(c.get('tag', '') + (f' ({c.get("text", "")[:20]}...)' if c.get("text") else '') for c in context['children'][:5])}"
        
        return f"""You are analyzing a section of a webpage. Describe what this element is and its purpose in natural language.

{element_desc}
{context_desc}

Provide a thoughtful analysis of:
1. What this element/section represents (be specific and descriptive)
2. Its purpose on the page
3. What users likely want when they interact with it
4. Your confidence level (0-1) in this analysis
5. Key identifying features that led to your conclusion
{f"6. What happens when users click this element" if element_data.get('clickable') else ""}

Don't constrain yourself to predefined categories. Describe it as you naturally understand it.

Respond in JSON format:
{{
    "understanding": "Natural description of what this is",
    "purpose": "What this helps users accomplish",
    "user_intent": "What users likely want when they see/use this",
    "confidence": 0.0-1.0,
    "key_elements": ["identifying", "features"],
    {'"click_behavior": "What happens when clicked",' if element_data.get('clickable') else ''}
    "notes": "Any additional observations"
}}"""
    
    async def _query_llm(self, prompt: str) -> str:
        """Query the LLM"""
        if self.provider == 'openai':
            response = await self.client.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a web UX expert analyzing webpage elements."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            return response.choices[0].message.content
            
        elif self.provider == 'anthropic':
            response = await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.3
            )
            return response.content[0].text
            
        elif self.provider == 'ollama':
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                ) as response:
                    result = await response.json()
                    return result.get("response", "{}")
                    
        elif self.provider == 'groq':
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a web UX expert analyzing webpage elements."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            return response.choices[0].message.content
        
        return "{}"
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response flexibly"""
        try:
            # Find JSON in response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            logger.error(f"Failed to parse LLM response: {response[:200]}")
        
        return {
            "understanding": "Unable to analyze",
            "purpose": "Unknown",
            "confidence": 0.0,
            "key_elements": []
        }
    
    def _mock_response(self, element_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock response for testing without LLM"""
        tag = element_data.get('tagName', 'div')
        text = element_data.get('text', '')[:50]
        
        # Simple heuristics for testing
        if tag == 'nav' or 'nav' in element_data.get('className', ''):
            return {
                "understanding": "This appears to be the main navigation menu for the website",
                "purpose": "Helps users navigate to different sections of the site",
                "user_intent": "Users want to find and access other pages or sections",
                "confidence": 0.85,
                "key_elements": ["navigation", "menu", "links"],
                "notes": "Contains multiple navigation links"
            }
        elif tag == 'header':
            return {
                "understanding": "This is the site header containing branding and top-level navigation",
                "purpose": "Establishes site identity and provides primary navigation",
                "user_intent": "Users look here for site identification and main menu options",
                "confidence": 0.9,
                "key_elements": ["header", "branding", "top navigation"]
            }
        elif 'footer' in tag or 'footer' in element_data.get('className', ''):
            return {
                "understanding": "This is the website footer with supplementary information",
                "purpose": "Provides additional links, legal info, and contact details",
                "user_intent": "Users check here for contact info, policies, or sitemap",
                "confidence": 0.8,
                "key_elements": ["footer", "contact", "links"]
            }
        elif 'search' in element_data.get('className', '') or 'search' in text.lower():
            return {
                "understanding": "This appears to be a search interface for finding content",
                "purpose": "Allows users to search for specific information on the site",
                "user_intent": "Users want to quickly find specific content or pages",
                "confidence": 0.75,
                "key_elements": ["search", "input", "query"]
            }
        else:
            return {
                "understanding": f"This is a {tag} element that appears to contain {('content' if text else 'structural layout')}",
                "purpose": "Organizes or presents information on the page",
                "user_intent": "Users may read or interact with this content",
                "confidence": 0.4,
                "key_elements": [tag, "content" if text else "layout"],
                "notes": "Generic element without clear semantic markers"
            }