"""
Integrated Web Analyzer with Knowledge Persistence
Combines browser control, knowledge store, and LLM analysis
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

from playwright.async_api import async_playwright, Page, Browser
from knowledge_store import KnowledgeStore, KnowledgeAwareAnalyzer
from browser_with_controls import BrowserWithControls

logger = logging.getLogger(__name__)


class IntegratedWebAnalyzer:
    """Main analyzer combining all components"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.controls: Optional[BrowserWithControls] = None
        self.knowledge_store = KnowledgeStore()
        self.knowledge_analyzer = KnowledgeAwareAnalyzer(self.knowledge_store)
        self.current_url = None
        
    async def start(self):
        """Start the browser and initialize components"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        self.controls = BrowserWithControls(self.page)
        
    async def analyze_url(self, url: str, force_fresh: bool = False):
        """Navigate to URL and run analysis"""
        self.current_url = url
        
        # Navigate to the page
        await self.page.goto(url, wait_until="networkidle")
        
        # Check if we have cached knowledge
        existing_knowledge = self.knowledge_store.load_site_knowledge(url)
        has_cache = len(existing_knowledge) > 0
        
        # Inject control overlay
        await self.controls.inject_control_overlay(has_cached_knowledge=has_cache)
        
        # Connect the analyze button to our method
        await self.page.expose_function('requestAnalysis', 
                                       lambda: asyncio.create_task(self._run_analysis(force_fresh=True)))
        await self.page.evaluate("""
            window.addEventListener('web-inference-analyze', () => window.requestAnalysis());
        """)
        
        if not has_cache or force_fresh:
            # Run initial analysis
            await self._run_analysis(force_fresh=force_fresh)
        else:
            # Load cached overlays
            await self._load_cached_analysis()
    
    async def _run_analysis(self, force_fresh: bool = False):
        """Run the actual analysis"""
        await self.controls.update_status("Analyzing...", "#ff9800")
        
        # Clear existing overlays
        await self.controls.clear_overlays()
        
        # Extract elements hierarchically
        elements = await self._extract_page_elements()
        
        # Reset stats
        self.knowledge_analyzer.stats = {'cache_hits': 0, 'llm_calls': 0}
        
        # Analyze each element
        analyzed_count = 0
        for element_data in elements:
            try:
                # Get analysis (from cache or fresh)
                analysis = await self.knowledge_analyzer.analyze_with_cache(
                    self.current_url, 
                    element_data,
                    force_fresh=force_fresh
                )
                
                # Create overlay
                from_cache = self.knowledge_analyzer.stats['cache_hits'] > analyzed_count
                await self.controls.create_element_overlay(
                    element_data['element'],
                    analysis,
                    from_cache=from_cache
                )
                
                analyzed_count += 1
                
                # Update stats periodically
                if analyzed_count % 5 == 0:
                    await self.controls.update_stats({
                        'elements': analyzed_count,
                        **self.knowledge_analyzer.stats
                    })
                
            except Exception as e:
                logger.error(f"Error analyzing element: {e}")
        
        # Final status update
        cache_percent = (self.knowledge_analyzer.stats['cache_hits'] / max(analyzed_count, 1)) * 100
        status_text = f"Analysis complete: {analyzed_count} elements"
        if not force_fresh and cache_percent > 0:
            status_text += f" ({cache_percent:.0f}% from cache)"
        
        await self.controls.update_status(status_text, "#4CAF50")
        await self.controls.update_stats({
            'elements': analyzed_count,
            **self.knowledge_analyzer.stats
        })
        
        logger.info(f"Analysis complete: {analyzed_count} elements analyzed")
    
    async def _load_cached_analysis(self):
        """Load and display cached analysis"""
        await self.controls.update_status("Loading cached analysis...", "#2196F3")
        
        # Extract current page elements
        elements = await self._extract_page_elements()
        
        loaded_count = 0
        for element_data in elements:
            # Check cache
            knowledge = self.knowledge_store.find_element_knowledge(
                self.current_url,
                element_data
            )
            
            if knowledge:
                # Create overlay from cached knowledge
                await self.controls.create_element_overlay(
                    element_data['element'],
                    knowledge.llm_response,
                    from_cache=True
                )
                loaded_count += 1
        
        await self.controls.update_status(
            f"Loaded {loaded_count} cached analyses", 
            "#4CAF50"
        )
        
        # Show stats
        await self.controls.update_stats({
            'elements': loaded_count,
            'cache_hits': loaded_count,
            'llm_calls': 0
        })
    
    async def _extract_page_elements(self) -> List[Dict[str, Any]]:
        """Extract analyzable elements from the page"""
        # Get all potentially interesting elements
        selectors = [
            "header", "nav", "main", "section", "article", "aside",
            "footer", "div[role]", "div[class*='content']",
            "div[class*='section']", "div[id]:not([id=''])",
            "form", "table"
        ]
        
        elements = []
        for selector in selectors:
            found = await self.page.query_selector_all(selector)
            for element in found:
                try:
                    # Get element data
                    data = await element.evaluate("""
                        (el) => {
                            const rect = el.getBoundingClientRect();
                            return {
                                tagName: el.tagName.toLowerCase(),
                                id: el.id || '',
                                className: el.className || '',
                                text: el.innerText?.substring(0, 200) || '',
                                rect: {
                                    x: rect.x,
                                    y: rect.y,
                                    width: rect.width,
                                    height: rect.height
                                },
                                visible: rect.width > 50 && rect.height > 50 &&
                                        window.getComputedStyle(el).display !== 'none'
                            };
                        }
                    """)
                    
                    if data['visible']:
                        data['element'] = element
                        elements.append(data)
                        
                except Exception as e:
                    logger.error(f"Error extracting element: {e}")
        
        # Remove duplicates and nested elements
        # (simplified for now - you could make this more sophisticated)
        return elements[:30]  # Limit to 30 elements for demo
    
    async def clear_site_knowledge(self):
        """Clear all knowledge for current site"""
        if self.current_url:
            self.knowledge_store.clear_site_knowledge(self.current_url)
            await self.controls.update_status("Knowledge cleared", "#f44336")
            logger.info(f"Cleared knowledge for {self.current_url}")


# Example usage
async def main():
    """Example usage of the integrated analyzer"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    analyzer = IntegratedWebAnalyzer(headless=False)
    
    try:
        await analyzer.start()
        
        # Get URL from user
        url = input("Enter URL to analyze (default: https://example.com): ").strip()
        if not url:
            url = "https://example.com"
        
        print(f"\n🚀 Opening {url}...")
        print("📌 Controls in top-right corner:")
        print("   - Green button: Run/re-run analysis")
        print("   - Red button: Clear overlays")
        print("   - Blue button: Show/hide overlays")
        print("   - Alt+Click on highlighted elements to see AI insights")
        print("\n📦 = Loaded from cache, ✨ = Fresh analysis")
        
        await analyzer.analyze_url(url)
        
        # Keep running
        print("\nPress Ctrl+C to exit...")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nClosing browser...")
    finally:
        if analyzer.browser:
            await analyzer.browser.close()


async def _extract_page_elements(self) -> List[Dict[str, Any]]:
    """Extract analyzable elements from the page with click detection"""
    # Get all potentially interesting elements
    selectors = [
        "header", "nav", "main", "section", "article", "aside",
        "footer", "div[role]", "div[class*='content']",
        "div[class*='section']", "div[id]:not([id=''])",
        "form", "table", "a", "button", "input[type='submit']"  # Added clickable elements
    ]
    
    elements = []
    for selector in selectors:
        found = await self.page.query_selector_all(selector)
        for element in found:
            try:
                # Get element data including clickability
                data = await element.evaluate("""
                    (el) => {
                        const rect = el.getBoundingClientRect();
                        const isClickable = (
                            el.tagName === 'A' || 
                            el.tagName === 'BUTTON' ||
                            el.onclick !== null ||
                            el.getAttribute('role') === 'button' ||
                            window.getComputedStyle(el).cursor === 'pointer'
                        );
                        
                        // Get children info for context
                        const children = Array.from(el.children).slice(0, 5).map(child => ({
                            tag: child.tagName.toLowerCase(),
                            text: child.innerText?.substring(0, 30) || ''
                        }));
                        
                        return {
                            tagName: el.tagName.toLowerCase(),
                            id: el.id || '',
                            className: el.className || '',
                            text: el.innerText?.substring(0, 200) || '',
                            rect: {
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            },
                            visible: rect.width > 50 && rect.height > 50 &&
                                    window.getComputedStyle(el).display !== 'none',
                            clickable: isClickable,
                            href: el.href || '',
                            children: children
                        };
                    }
                """)
                
                if data['visible']:
                    data['element'] = element
                    elements.append(data)
                    
            except Exception as e:
                logger.error(f"Error extracting element: {e}")
    
    # Remove duplicates and nested elements
    return elements[:30]  # Limit to 30 elements for demo


# Updated overlay creation with better interaction
async def create_element_overlay_interactive(self, element: ElementHandle, 
                                           analysis: Dict[str, Any], 
                                           from_cache: bool = False):
    """Create overlay that allows click-through for interactive elements"""
    
    color = self._get_confidence_color(analysis.get('confidence', 0))
    cache_indicator = "📦" if from_cache else "✨"
    
    await element.evaluate(f"""
        (element) => {{
            const rect = element.getBoundingClientRect();
            const isClickable = element.tagName === 'A' || 
                               element.tagName === 'BUTTON' ||
                               element.onclick !== null;
            
            // Create overlay
            const overlay = document.createElement('div');
            overlay.className = 'wi-overlay';
            overlay.style.cssText = `
                position: fixed;
                left: ${{rect.left}}px;
                top: ${{rect.top}}px;
                width: ${{rect.width}}px;
                height: ${{rect.height}}px;
                border: 2px solid {color};
                background: transparent;
                pointer-events: ${{isClickable ? 'none' : 'auto'}}; /* Allow clicks through for clickable elements */
                z-index: 9998;
                transition: all 0.3s ease;
            `;
            
            // Info badge
            const badge = document.createElement('div');
            badge.style.cssText = `
                position: absolute;
                top: -25px;
                right: 0;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-family: system-ui;
                pointer-events: auto;
                cursor: help;
            `;
            badge.innerHTML = `{cache_indicator} Alt+Click for info`;
            overlay.appendChild(badge);
            
            // Click behavior indicator for clickable elements
            if ({json.dumps(analysis.get('click_behavior', ''))}) {{
                const clickInfo = document.createElement('div');
                clickInfo.style.cssText = `
                    position: absolute;
                    bottom: -20px;
                    left: 0;
                    background: rgba(33, 150, 243, 0.9);
                    color: white;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-family: system-ui;
                    max-width: 200px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                `;
                clickInfo.textContent = '→ ' + {json.dumps(analysis.get('click_behavior', 'Click action'))};
                overlay.appendChild(clickInfo);
            }}
            
            document.body.appendChild(overlay);
            
            // Store reference
            window.webInferenceState.overlays.set(element, {{
                overlay: overlay,
                analysis: {json.dumps(analysis)}
            }});
            
            // Show full info on Alt+Click
            const showInfo = (e) => {{
                if (e.altKey) {{
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Create modal with full analysis
                    const modal = document.createElement('div');
                    modal.style.cssText = `
                        position: fixed;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        background: rgba(0, 0, 0, 0.95);
                        color: white;
                        padding: 30px;
                        border-radius: 10px;
                        z-index: 10001;
                        max-width: 600px;
                        font-family: system-ui;
                        line-height: 1.6;
                    `;
                    
                    const analysis = window.webInferenceState.overlays.get(element).analysis;
                    modal.innerHTML = `
                        <h3 style="margin: 0 0 20px 0; color: #4fc3f7;">
                            AI Analysis {cache_indicator}
                        </h3>
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #81c784;">Understanding:</strong><br>
                            ${{analysis.understanding}}
                        </div>
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #81c784;">Purpose:</strong><br>
                            ${{analysis.purpose}}
                        </div>
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #81c784;">User Intent:</strong><br>
                            ${{analysis.user_intent || 'Not specified'}}
                        </div>
                        ${{analysis.click_behavior ? `
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #64b5f6;">Click Behavior:</strong><br>
                            ${{analysis.click_behavior}}
                        </div>
                        ` : ''}}
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #81c784;">Confidence:</strong> 
                            ${{(analysis.confidence * 100).toFixed(0)}}%
                        </div>
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #81c784;">Key Features:</strong><br>
                            ${{(analysis.key_elements || []).join(', ')}}
                        </div>
                        <button onclick="this.parentElement.remove()" 
                                style="background: #4fc3f7; border: none; 
                                       padding: 10px 20px; border-radius: 5px; 
                                       cursor: pointer; margin-top: 10px;
                                       font-weight: 500;">
                            Close
                        </button>
                    `;
                    
                    document.body.appendChild(modal);
                    modal.addEventListener('click', (e) => {{
                        if (e.target === modal) modal.remove();
                    }});
                }}
            }};
            
            // Add listeners to both overlay and element
            overlay.addEventListener('click', showInfo);
            element.addEventListener('click', showInfo);
            
            // Update position on scroll/resize
            const updatePosition = () => {{
                const newRect = element.getBoundingClientRect();
                overlay.style.left = newRect.left + 'px';
                overlay.style.top = newRect.top + 'px';
            }};
            
            window.addEventListener('scroll', updatePosition);
            window.addEventListener('resize', updatePosition);
        }}
    """, element)

if __name__ == "__main__":
    asyncio.run(main())