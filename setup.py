from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="check-bedrock-access",
    version="1.0.0",
    author="Scott Friedman and Project Contributors",
    author_email="scttfrdmn@github.com",
    description="A tool to verify AWS Bedrock access and permissions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/scttfrdmn/check-bedrock-access",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.6",
    install_requires=[
        "boto3>=1.28.0",
        "rich>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "check-bedrock-access=bedrock_access_checker.cli:main",
        ],
    },
)