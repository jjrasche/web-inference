"""
Knowledge Store - src/knowledge_store.py
Simple JSON-based storage for quick prototyping
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ElementKnowledge:
    """Stored knowledge about an element"""
    url: str
    selector: str  # CSS selector or XPath
    element_hash: str  # Hash of element properties
    understanding: str
    purpose: str
    confidence: float
    timestamp: str
    llm_response: Dict[str, Any]
    

class KnowledgeStore:
    """Simple file-based knowledge persistence"""
    
    def __init__(self, data_dir: Path = Path("data/site_knowledge")):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache = {}  # In-memory cache
        
    def _get_site_file(self, url: str) -> Path:
        """Get the JSON file for a specific site"""
        # Create safe filename from URL
        safe_name = hashlib.md5(url.encode()).hexdigest()[:12]
        domain = url.split('/')[2].replace('www.', '')
        return self.data_dir / f"{domain}_{safe_name}.json"
    
    def _compute_element_hash(self, element_data: Dict[str, Any]) -> str:
        """Create hash of element properties for comparison"""
        # Hash based on stable properties
        key_props = {
            'tag': element_data.get('tagName'),
            'id': element_data.get('id'),
            'classes': element_data.get('className'),
            'text_preview': element_data.get('text', '')[:100],
            'position': f"{element_data.get('rect', {}).get('x', 0)},{element_data.get('rect', {}).get('y', 0)}"
        }
        return hashlib.md5(json.dumps(key_props, sort_keys=True).encode()).hexdigest()[:16]
    
    def load_site_knowledge(self, url: str) -> Dict[str, ElementKnowledge]:
        """Load all knowledge for a site"""
        site_file = self._get_site_file(url)
        
        if site_file.exists():
            try:
                with open(site_file, 'r') as f:
                    data = json.load(f)
                    # Convert back to ElementKnowledge objects
                    knowledge = {}
                    for key, value in data.items():
                        knowledge[key] = ElementKnowledge(**value)
                    logger.info(f"Loaded {len(knowledge)} elements for {url}")
                    return knowledge
            except Exception as e:
                logger.error(f"Error loading knowledge: {e}")
        
        return {}
    
    def save_element_knowledge(self, url: str, element_data: Dict[str, Any], 
                              llm_response: Dict[str, Any]) -> ElementKnowledge:
        """Save knowledge about an element"""
        # Create element knowledge
        element_hash = self._compute_element_hash(element_data)
        selector = self._build_selector(element_data)
        
        knowledge = ElementKnowledge(
            url=url,
            selector=selector,
            element_hash=element_hash,
            understanding=llm_response.get('understanding', ''),
            purpose=llm_response.get('purpose', ''),
            confidence=llm_response.get('confidence', 0.0),
            timestamp=datetime.now().isoformat(),
            llm_response=llm_response
        )
        
        # Load existing knowledge
        site_knowledge = self.load_site_knowledge(url)
        
        # Add/update this element
        site_knowledge[element_hash] = knowledge
        
        # Save back to file
        site_file = self._get_site_file(url)
        with open(site_file, 'w') as f:
            # Convert to dict for JSON serialization
            data = {k: asdict(v) for k, v in site_knowledge.items()}
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved knowledge for element {selector} on {url}")
        return knowledge
    
    def find_element_knowledge(self, url: str, element_data: Dict[str, Any]) -> Optional[ElementKnowledge]:
        """Find existing knowledge for an element"""
        element_hash = self._compute_element_hash(element_data)
        site_knowledge = self.load_site_knowledge(url)
        return site_knowledge.get(element_hash)
    
    def _build_selector(self, element_data: Dict[str, Any]) -> str:
        """Build a CSS selector for the element"""
        tag = element_data.get('tagName', 'div')
        id_attr = element_data.get('id', '')
        classes = element_data.get('className', '').split()[:2]  # First 2 classes
        
        selector = tag
        if id_attr:
            selector = f"#{id_attr}"
        elif classes:
            selector += '.' + '.'.join(classes)
            
        return selector
    
    def clear_site_knowledge(self, url: str):
        """Clear all knowledge for a site (for re-analysis)"""
        site_file = self._get_site_file(url)
        if site_file.exists():
            site_file.unlink()
            logger.info(f"Cleared knowledge for {url}")


class KnowledgeAwareAnalyzer:
    """Analyzer that uses persisted knowledge"""
    
    def __init__(self, knowledge_store: KnowledgeStore):
        self.store = knowledge_store
        self.stats = {
            'cache_hits': 0,
            'llm_calls': 0
        }
    
    async def analyze_with_cache(self, url: str, element_data: Dict[str, Any], 
                                 force_fresh: bool = False) -> Dict[str, Any]:
        """Analyze element, using cache if available"""
        
        if not force_fresh:
            # Check for existing knowledge
            existing = self.store.find_element_knowledge(url, element_data)
            if existing:
                self.stats['cache_hits'] += 1
                logger.info(f"Using cached knowledge: {existing.understanding[:50]}...")
                return existing.llm_response
        
        # No cache or forced fresh - call LLM
        self.stats['llm_calls'] += 1
        logger.info("Calling LLM for fresh analysis...")
        
        # This is where you'd call your LLM
        # For now, return mock response
        llm_response = {
            'understanding': f"Fresh analysis of {element_data.get('tagName', 'element')}",
            'purpose': 'Analyzed purpose',
            'confidence': 0.8,
            'key_elements': ['mock', 'analysis']
        }
        
        # Save to knowledge store
        self.store.save_element_knowledge(url, element_data, llm_response)
        
        return llm_response
    
    def get_stats(self) -> Dict[str, int]:
        """Get analysis statistics"""
        return self.stats.copy()