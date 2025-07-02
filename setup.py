from setuptools import setup, find_packages
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
setup(
    name="web-inference",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Interpretable AI system for understanding websites",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/web-inference",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "playwright>=1.40.0",
        "beautifulsoup4>=4.12.0",
        "pydantic>=2.5.0",
        "rich>=13.7.0",
        "click>=8.1.7",
    ],
    extras_require={
        "openai": ["openai>=1.6.0"],
        "anthropic": ["anthropic>=0.8.0"],
        "dev": ["pytest>=7.4.3", "black>=23.12.0", "flake8>=6.1.0"],
    },
    entry_points={
        "console_scripts": [
            "web-inference=scripts.cli:main",
        ],
    },
)
