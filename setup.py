from setuptools import setup, find_packages

setup(
    name="autopulsesynth",
    version="0.1.0",
    description="Robust quantum pulse optimization via surrogate-assisted control",
    author="AutoPulseSynth Team",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.20",
        "scipy>=1.7",
        "qutip>=4.6",
        "scikit-learn>=1.0",
        "matplotlib",  # for analysis plotting if needed
    ],
    entry_points={
        "console_scripts": [
            "autopulsesynth=autopulsesynth.cli:main",
        ],
    },
    python_requires=">=3.8",
)
