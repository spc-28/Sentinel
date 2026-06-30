"""Serve the fine-tuned Qwen locally as an OpenAI-compatible endpoint.

Sentinel talks to it via LiteLLM (model ``openai/qwen2.5-rca`` at
``http://localhost:8001/v1``), so we just need any OpenAI-compatible server on 8001.

Recommended (needs a GPU box — your Colab/Kaggle session, or a local GPU):

    pip install "vllm>=0.6"
    vllm serve Qwen/Qwen2.5-7B-Instruct \\
        --enable-lora --lora-modules qwen2.5-rca=./qwen2.5-rca-lora \\
        --port 8001 --served-model-name qwen2.5-rca

No GPU locally? Merge the adapter and run a quantized GGUF with Ollama instead:

    # on the GPU box, merge adapter into the base and export, then:
    ollama create qwen2.5-rca -f Modelfile      # Modelfile FROM the merged gguf
    # point LOCAL_LLM_BASE_URL at Ollama's OpenAI shim: http://localhost:11434/v1

This module just documents/launches vLLM; it is not imported by the app.
"""

from __future__ import annotations

import subprocess

ADAPTER_DIR = "qwen2.5-rca-lora"
PORT = 8001


def main() -> None:
    cmd = [
        "vllm",
        "serve",
        "Qwen/Qwen2.5-7B-Instruct",
        "--enable-lora",
        "--lora-modules",
        f"qwen2.5-rca={ADAPTER_DIR}",
        "--served-model-name",
        "qwen2.5-rca",
        "--port",
        str(PORT),
    ]
    print("launching:", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
