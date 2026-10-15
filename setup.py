from setuptools import setup, find_packages

setup(
    name="mistral-vibe-crypto",
    version="0.1.0",
    description="Mistral Vibe Crypto Trading Bots",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pandas>=2.0",
        "numpy>=1.24",
        "requests>=2.31",
        "PyYAML>=6.0",
        "python-dotenv>=1.0",
        "matplotlib>=3.7",
    ],
)
