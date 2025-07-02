# Web Inference

An interpretable AI system for understanding and navigating websites. This tool creates a visual semantic layer over web pages, showing how AI understands different sections of a website.

## Features

- 🧠 **Semantic Understanding**: Uses LLMs to classify and understand website sections
- 👁️ **Visual Confidence Overlay**: Shows AI's confidence in different page sections
- 💭 **Explainable Reasoning**: Click any section to see why the AI classified it that way
- 📊 **Pattern Learning**: Builds understanding across similar sites
- 🔄 **Non-Intrusive**: Preserves all website functionality while adding semantic layer

## Demo

![Web Inference Demo](docs/demo.gif)

When analyzing a school website:
- Green borders indicate high-confidence sections (e.g., "Leadership" section)
- Click on any non-interactive area to see AI's reasoning
- Understanding persists across navigation

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/semantic-web-analyzer.git
cd semantic-web-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install playwright browsers
playwright install chromium
```


## Architecture

Web Inference uses a multi-step process to understand websites:

1. **DOM Analysis**: Extracts semantic sections from the page
2. **LLM Classification**: Sends sections to language models for understanding
3. **Confidence Scoring**: Assigns confidence levels to each inference
4. **Visual Overlay**: Creates non-intrusive visual indicators
5. **Knowledge Persistence**: Stores understanding for future use

```
Website → Section Extraction → LLM Inference → Visual Overlay → Knowledge Store
                                    ↓
                            Reasoning & Confidence
```

## How It Works

Web Inference acts as a semantic layer between you and websites:

- **Subtle Borders**: Sections the AI understands have subtle colored borders
- **Click for Details**: Click any non-interactive area to see AI reasoning
- **Confidence Colors**: Green = high confidence, Yellow = medium, Red = low
- **Smart Navigation**: AI learns patterns across similar sites
