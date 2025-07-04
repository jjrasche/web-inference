"""
Enhanced Browser Controller with Analysis Controls
"""
import asyncio
from typing import Optional, Dict, List, Any
from playwright.async_api import Page, ElementHandle
import json
import logging

logger = logging.getLogger(__name__)


class BrowserWithControls:
    """Browser controller with overlay controls and knowledge integration"""
    
    def __init__(self, page: Page):
        self.page = page
        self.current_url = None
        self.is_analyzing = False
        
    async def inject_control_overlay(self, has_cached_knowledge: bool = False):
        """Inject the control overlay and status indicator"""
        
        control_html = """
        <div id="web-inference-controls" style="
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            font-family: system-ui, -apple-system, sans-serif;
        ">
            <!-- Status Badge -->
            <div id="wi-status" style="
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                margin-bottom: 10px;
                font-size: 14px;
                display: flex;
                align-items: center;
                gap: 8px;
            ">
                <div id="wi-status-dot" style="
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: %s;
                "></div>
                <span id="wi-status-text">%s</span>
            </div>
            
            <!-- Control Buttons -->
            <div style="display: flex; gap: 10px;">
                <button id="wi-analyze-btn" style="
                    background: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-weight: 500;
                    transition: all 0.3s ease;
                " onmouseover="this.style.background='#45a049'" 
                   onmouseout="this.style.background='#4CAF50'">
                    %s
                </button>
                
                <button id="wi-clear-btn" style="
                    background: #f44336;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-weight: 500;
                    transition: all 0.3s ease;
                " onmouseover="this.style.background='#da190b'" 
                   onmouseout="this.style.background='#f44336'">
                    Clear
                </button>
                
                <button id="wi-toggle-btn" style="
                    background: #2196F3;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-weight: 500;
                    transition: all 0.3s ease;
                " onmouseover="this.style.background='#0b7dda'" 
                   onmouseout="this.style.background='#2196F3'">
                    Hide
                </button>
            </div>
            
            <!-- Stats -->
            <div id="wi-stats" style="
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 10px;
                border-radius: 5px;
                margin-top: 10px;
                font-size: 12px;
                display: none;
            ">
                <div>Elements analyzed: <span id="wi-stat-elements">0</span></div>
                <div>From cache: <span id="wi-stat-cache">0</span></div>
                <div>New analyses: <span id="wi-stat-new">0</span></div>
            </div>
        </div>
        """ % (
            "#4CAF50" if has_cached_knowledge else "#ff9800",  # Green if cached, orange if not
            "Knowledge loaded" if has_cached_knowledge else "No prior analysis",
            "Re-analyze" if has_cached_knowledge else "Analyze Page"
        )
        
        # Inject the control overlay
        await self.page.evaluate(f"""
            (() => {{
                // Remove existing controls if any
                const existing = document.getElementById('web-inference-controls');
                if (existing) existing.remove();
                
                // Add new controls
                const controls = document.createElement('div');
                controls.innerHTML = `{control_html}`;
                document.body.appendChild(controls.firstElementChild);
                
                // Initialize web inference state
                window.webInferenceState = {{
                    overlaysVisible: true,
                    stats: {{
                        elements: 0,
                        cache: 0,
                        new: 0
                    }},
                    overlays: new Map()
                }};
                
                // Button handlers
                document.getElementById('wi-analyze-btn').addEventListener('click', () => {{
                    window.dispatchEvent(new CustomEvent('web-inference-analyze'));
                }});
                
                document.getElementById('wi-clear-btn').addEventListener('click', () => {{
                    if (confirm('Clear all analysis overlays?')) {{
                        window.dispatchEvent(new CustomEvent('web-inference-clear'));
                    }}
                }});
                
                document.getElementById('wi-toggle-btn').addEventListener('click', () => {{
                    window.webInferenceState.overlaysVisible = !window.webInferenceState.overlaysVisible;
                    const visible = window.webInferenceState.overlaysVisible;
                    
                    // Toggle all overlays
                    document.querySelectorAll('.wi-overlay').forEach(overlay => {{
                        overlay.style.display = visible ? 'block' : 'none';
                    }});
                    
                    // Update button text
                    document.getElementById('wi-toggle-btn').textContent = visible ? 'Hide' : 'Show';
                }});
            }})();
        """)
        
        # Set up event listeners
        await self.page.expose_function('onAnalyzeRequest', self._handle_analyze_request)
        await self.page.expose_function('onClearRequest', self._handle_clear_request)
        
        await self.page.evaluate("""
            window.addEventListener('web-inference-analyze', () => window.onAnalyzeRequest());
            window.addEventListener('web-inference-clear', () => window.onClearRequest());
        """)
    
    async def update_status(self, text: str, color: str = "#4CAF50"):
        """Update the status indicator"""
        await self.page.evaluate(f"""
            (() => {{
                const statusDot = document.getElementById('wi-status-dot');
                const statusText = document.getElementById('wi-status-text');
                if (statusDot && statusText) {{
                    statusDot.style.background = '{color}';
                    statusText.textContent = '{text}';
                }}
            }})();
        """)
    
    async def update_stats(self, stats: Dict[str, int]):
        """Update the statistics display"""
        await self.page.evaluate(f"""
            (() => {{
                document.getElementById('wi-stat-elements').textContent = '{stats.get("elements", 0)}';
                document.getElementById('wi-stat-cache').textContent = '{stats.get("cache_hits", 0)}';
                document.getElementById('wi-stat-new').textContent = '{stats.get("llm_calls", 0)}';
                document.getElementById('wi-stats').style.display = 'block';
            }})();
        """)
    
    async def create_element_overlay(self, element: ElementHandle, analysis: Dict[str, Any], from_cache: bool = False):
        """Create overlay for an analyzed element"""
        
        color = self._get_confidence_color(analysis.get('confidence', 0))
        cache_indicator = "📦" if from_cache else "✨"
        
        await element.evaluate(f"""
            (element) => {{
                const rect = element.getBoundingClientRect();
                
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
                    pointer-events: none;
                    z-index: 9998;
                    transition: all 0.3s ease;
                `;
                
                // Add cache indicator
                const indicator = document.createElement('div');
                indicator.style.cssText = `
                    position: absolute;
                    top: -10px;
                    right: -10px;
                    background: {color};
                    color: white;
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                `;
                indicator.textContent = '{cache_indicator}';
                overlay.appendChild(indicator);
                
                document.body.appendChild(overlay);
                
                // Store overlay reference
                window.webInferenceState.overlays.set(element, {{
                    overlay: overlay,
                    analysis: {json.dumps(analysis)}
                }});
                
                // Update position on scroll/resize
                const updatePosition = () => {{
                    const newRect = element.getBoundingClientRect();
                    overlay.style.left = newRect.left + 'px';
                    overlay.style.top = newRect.top + 'px';
                    overlay.style.width = newRect.width + 'px';
                    overlay.style.height = newRect.height + 'px';
                }};
                
                window.addEventListener('scroll', updatePosition);
                window.addEventListener('resize', updatePosition);
                
                // Click handler for explanation
                element.addEventListener('click', (e) => {{
                    if (e.altKey) {{  // Alt+Click to see explanation
                        e.preventDefault();
                        e.stopPropagation();
                        
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
                        `;
                        
                        const analysis = window.webInferenceState.overlays.get(element).analysis;
                        modal.innerHTML = `
                            <h3 style="margin: 0 0 20px 0;">AI Understanding {cache_indicator}</h3>
                            <p><strong>What this is:</strong> ${{analysis.understanding}}</p>
                            <p><strong>Purpose:</strong> ${{analysis.purpose}}</p>
                            <p><strong>Confidence:</strong> ${{(analysis.confidence * 100).toFixed(0)}}%</p>
                            <button onclick="this.parentElement.remove()" 
                                    style="background: #4CAF50; border: none; 
                                           padding: 10px 20px; border-radius: 5px; 
                                           cursor: pointer; margin-top: 20px;">
                                Close
                            </button>
                        `;
                        
                        document.body.appendChild(modal);
                        modal.addEventListener('click', (e) => {{
                            if (e.target === modal) modal.remove();
                        }});
                    }}
                }});
            }}
        """, element)
    
    def _get_confidence_color(self, confidence: float) -> str:
        """Get color based on confidence level"""
        if confidence > 0.8:
            return "rgba(76, 175, 80, 0.6)"  # Green
        elif confidence > 0.5:
            return "rgba(255, 193, 7, 0.6)"  # Amber
        else:
            return "rgba(244, 67, 54, 0.4)"  # Red
    
    async def clear_overlays(self):
        """Clear all analysis overlays"""
        await self.page.evaluate("""
            (() => {
                document.querySelectorAll('.wi-overlay').forEach(el => el.remove());
                window.webInferenceState.overlays.clear();
                window.webInferenceState.stats = { elements: 0, cache: 0, new: 0 };
            })();
        """)
    
    async def _handle_analyze_request(self):
        """Handle request to analyze/re-analyze the page"""
        # This will be connected to the main analyzer
        logger.info("Analysis requested via overlay button")
    
    async def _handle_clear_request(self):
        """Handle request to clear overlays"""
        await self.clear_overlays()
        await self.update_status("Overlays cleared", "#f44336")
        logger.info("Overlays cleared via button")