from setuptools import setup, find_packages

setup(
    name="audit_tool",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic-settings",
        "aiofiles",
        "python-multipart",  # for file uploads
        "pandas",  # for data processing
        "numpy",   # for numerical operations
        "scikit-learn",  # for anomaly detection
    ],
)
