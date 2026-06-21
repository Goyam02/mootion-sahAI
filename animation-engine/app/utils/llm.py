import os

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-14")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_API_KEY")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")

if not endpoint:
    raise RuntimeError("AZURE_OPENAI_ENDPOINT is required")

if not api_key:
    raise RuntimeError("AZURE_OPENAI_API_KEY is required")

if not deployment_name:
    raise RuntimeError("AZURE_OPENAI_DEPLOYMENT is required")

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=api_key,
)


def call_llm(prompt: str, temperature: float = 0):
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=temperature,
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("LLM returned an empty response")

    # Track usage if tracker is active
    try:
        from utils.cost_tracker import get_tracker
        tracker = get_tracker()
        if tracker and response.usage:
            model_used = response.model or deployment_name
            tracker.add_llm_call(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                model_name=model_used
            )
    except Exception as e:
        print(f"[cost-tracker] Error recording LLM tokens: {e}")

    return content.strip()