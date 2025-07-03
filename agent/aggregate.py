import asyncio
import json
import os
from typing import List

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMConfig,
    LLMExtractionStrategy,
)
from jinja2 import Template
from pydantic import BaseModel, Field

from agent.settings import GEMINI_MODEL_ID
from lib.utils import output_content


class Config(BaseModel):
    sources: List[str] = Field(description="List of URLs to aggregate")
    output: str = Field(description="Output file path for the aggregated content")


class JobSchema(BaseModel):
    name: str = Field(description="Name of the job")
    description: str = Field(description="Description of the job")
    company: str = Field(description="Company offering the job")
    location: str = Field(description="Location of the job")
    remote: bool = Field(default=False, description="Is the job remote?")
    job_type: str = Field(description="Type of the job (e.g., Full-time, Part-time)")
    salary: str = Field(description="Salary range for the job")
    url: str = Field(description="URL of the job posting")


__JOB_EXETRACTOR_PROMPT__ = """
You are an expert job extractor. Your task is to extract job details from the provided content.
You will receive a chunk of text that contains job information. Your goal is to extract the following
fields: name, description, company, location, remote, job_type, salary, and url.

NOTE: NOT ALL FIELDS WILL BE PRESENT IN EVERY JOB POSTING.
If a field is not present, you should return an empty string ("" NOT N/A) for that field.
"""
_browser_config = BrowserConfig(headless=False)
# 1. Define the LLM extraction strategy
_llm_strategy = LLMExtractionStrategy(
    llm_config=LLMConfig(
        provider=f"gemini/{GEMINI_MODEL_ID}", api_token=os.getenv("GOOGLE_API_KEY")
    ),
    schema=JobSchema.model_json_schema(),
    extraction_type="schema",
    instruction=__JOB_EXETRACTOR_PROMPT__,
    input_format="markdown",  # or "html", "fit_markdown"
    extra_args={
        "temperature": 0.0,
    },
)


def _load_config(config: str) -> Config:
    with open(config, "r", encoding="utf-8") as file:
        json_data = file.read()
    return Config.model_validate_json(json_data)


async def load_url(url: str) -> List[JobSchema] | None:
    run_config = CrawlerRunConfig(
        scan_full_page=True,
        wait_until="networkidle",
        page_timeout=600_000,
        extraction_strategy=_llm_strategy,
        cache_mode=CacheMode.BYPASS,
        # deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=3),
    )
    async with AsyncWebCrawler(config=_browser_config) as crawler:
        result = await crawler.arun(url, config=run_config)
        if result.success:
            return [
                JobSchema.model_validate(job)
                for job in json.loads(result.extracted_content)
            ]
        else:
            return None


async def aggregate_content(sources: List[str]) -> List[JobSchema]:
    tasks = [load_url(source) for source in sources]
    results = await asyncio.gather(*tasks)

    # Filter out None values and parse JSON strings
    all_jobs: List[JobSchema] = []
    for result in results:
        if result is not None:
            all_jobs.extend(result)

    return all_jobs


def aggregate_sources(config: str):
    c = _load_config(config)

    try:
        # Use aggregate_content to get all jobs from all sources
        all_jobs = asyncio.run(aggregate_content(c.sources))

        # Render jobs to HTML
        html_content = render_jobs_to_html(all_jobs)
        output_content(c.output, "txt", html_content)
        print(f"\nHTML content saved to: {c.output}")

    except Exception as e:
        print(f"Error aggregating sources: {e}")


# HTML template for job listings
JOB_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Job Listings</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }
        .job { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
        .job-title { font-size: 18px; font-weight: bold; color: #333; }
        .company { color: #666; font-weight: bold; }
        .location { color: #888; }
        .remote-badge { background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; }
        .job-type { background: #007bff; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; }
        .salary { color: #dc3545; font-weight: bold; }
        .description { margin: 10px 0; }
        .job-url { margin-top: 10px; }
        .job-url a { color: #007bff; text-decoration: none; }
        .job-url a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Job Listings (Total: {{ jobs|length }})</h1>
    {% if jobs %}
        {% for job in jobs %}
        <div class="job">
            <div class="job-title">{{ job.name }}</div>
            <div class="company">{{ job.company }}</div>
            <div style="margin: 5px 0;">
                {% if job.location %}
                <span class="location">📍 {{ job.location }}</span>
                {% endif %}
                {% if job.remote %}
                <span class="remote-badge">Remote</span>
                {% endif %}
                {% if job.job_type %}
                <span class="job-type">{{ job.job_type }}</span>
                {% endif %}
            </div>
            {% if job.salary %}
            <div class="salary">💰 {{ job.salary }}</div>
            {% endif %}
            {% if job.description %}
            <div class="description">{{ job.description }}</div>
            {% endif %}
            {% if job.url %}
            <div class="job-url">
                <a href="{{ job.url }}" target="_blank">View Job Posting</a>
            </div>
            {% endif %}
        </div>
        {% endfor %}
    {% else %}
        <p>No jobs found.</p>
    {% endif %}
</body>
</html>
"""


def render_jobs_to_html(jobs: List[JobSchema]) -> str:
    """Render job list to HTML using Jinja2 template."""
    template = Template(JOB_LIST_TEMPLATE)
    return template.render(jobs=jobs)
