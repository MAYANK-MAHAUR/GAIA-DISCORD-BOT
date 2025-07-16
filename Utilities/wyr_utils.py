import asyncio
import os
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
GAIANET_API_KEY = os.getenv("GAIANET_API_KEY")
GAIANET_BASE_URL = os.getenv("GAIANET_BASE_URL")
GAIANET_MODEL_NAME = os.getenv("GAIANET_MODEL_NAME")
GAIANET_EMBEDDING_BASE_URL = os.getenv("GAIANET_EMBEDDING_EMBEDDING_BASE_URL", "https://qwen7b.gaia.domains/v1")
GAIANET_EMBEDDING_MODEL = os.getenv("GAIANET_EMBEDDING_EMBEDDING_MODEL", "nomic-embed-text-v1.5.f16")

gaia_client_utils = OpenAI(
    base_url=GAIANET_BASE_URL,
    api_key=GAIANET_API_KEY
)

gaia_embedding_client_utils = OpenAI(
    base_url=GAIANET_EMBEDDING_BASE_URL,
    api_key=GAIANET_API_KEY
)

async def get_embedding(text: str) -> list[float]:
    response = await asyncio.to_thread(
        gaia_embedding_client_utils.embeddings.create,
        model=GAIANET_EMBEDDING_MODEL,
        input=[text]
    )
    return response.data[0].embedding

def calculate_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    dot_product = np.dot(vec1_np, vec2_np)
    norm_vec1 = np.linalg.norm(vec1_np)
    norm_vec2 = np.linalg.norm(vec2_np)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    return dot_product / (norm_vec1 * norm_vec2)

async def get_gaia_ai_response(prompt_text: str) -> str:
    system_message = {"role": "system", "content": "You are a creative AI assistant focused on generating fun 'Would You Rather' questions and witty explanations. Ensure your explanations are *extremely brief* and no more than two concise sentences."}
    messages_to_send = [system_message, {"role": "user", "content": prompt_text}]
    response = await asyncio.to_thread(
        gaia_client_utils.chat.completions.create,
        model=GAIANET_MODEL_NAME,
        messages=messages_to_send,
        temperature=0.7,
        max_tokens=100
    )
    return response.choices[0].message.content
