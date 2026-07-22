"""
Verification script to test OpenAIAgent with your .env configuration.

Usage:
    python3 src/tests/test_openai_runner.py
"""

import os
import sys
from pathlib import Path

# Ensure src/ is on sys.path
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agents import create_agent
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(SRC_DIR.parent / ".env")


def main():
    print("--- Testing OpenAI Agent Setup ---")
    api_key = os.getenv("FOUNDRY_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "❌ Error: FOUNDRY_API_KEY or OPENAI_API_KEY is not set "
            "in your .env file!"
        )
        return

    print(f"Key detected: {api_key[:8]}... (hidden)")
    model = os.getenv("AGENT_MODEL") or os.getenv("FOUNDRY_MODEL", "gpt-4o-mini")
    print(f"Using model: {model}")

    try:
        # Create agent with provider='openai'
        agent = create_agent(provider="openai", model=model)
        print("Agent created successfully.")

        # Test simple completion
        print("\nSending test completion query...")
        res = agent.complete(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'DistillNews OpenAI provider is working!' if you can read this.",
        )
        print("Response:\n", res.content)

        # Test YAML template substitution
        print("\nTesting prompt template execution (is_news.yaml)...")
        template_path = SRC_DIR / "prompts" / "is_news.yaml"
        sample_input = {
            "title": "ISRO announces new space mission planned for 2026",
            "content": "Indian Space Research Organisation today announced a major milestone for its upcoming space station program.",
        }

        template_res = agent.complete_from_template(template_path, sample_input)
        print(f"Template Output (is_news): {template_res.content.strip()}")

        print("\n✅ OpenAI Provider verified working successfully!")

    except Exception as e:
        print(f"\n❌ Error executing OpenAI agent: {e}")


if __name__ == "__main__":
    main()
