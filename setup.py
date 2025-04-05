from setuptools import setup, find_packages
from pathlib import Path

long_description = (Path(__file__).parent / "README.md").read_text()

exec(open("streamlit_openai/version.py").read())

setup(
    name="streamlit-openai",
    version=__version__,
    author='Seung-been "Steven" Lee',
    author_email="sbstevenlee@gmail.com",
    description="Build AI chatbots with Streamlit and OpenAI",
    url="https://github.com/sbslee/streamlit-openai",
    packages=find_packages(),
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown"
)