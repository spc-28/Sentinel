"""QLoRA fine-tune of Qwen 2.5 7B on Sentinel RCA reports — run on a FREE GPU.

This is written to run on **Google Colab or Kaggle** (free T4/P100), NOT a paid
cloud GPU and NOT this machine. Upload `data/train.jsonl` + `data/val.jsonl`
(produced by `make training-data`) next to this file, then run top to bottom.

Colab setup cell (run once):
    !pip install -q "transformers>=4.45" "peft>=0.13" "trl>=0.11" \
        "bitsandbytes>=0.44" "datasets>=3.0" "accelerate>=1.0"

Result: a small LoRA adapter (~tens of MB) you download and serve locally with
`serve_local.py`. The base weights stay on Hugging Face; you only ship the adapter.
"""

from __future__ import annotations

import torch
from datasets import load_dataset
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
OUTPUT_DIR = "qwen2.5-rca-lora"


def main() -> None:
    # 4-bit NF4 quantization — this is the "Q" in QLoRA (fits 7B on a free T4).
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model)

    # LoRA adapters on the attention + MLP projections — the only trained params.
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )

    dataset = load_dataset(
        "json", data_files={"train": "data/train.jsonl", "validation": "data/val.jsonl"}
    )

    def format_chat(example: dict) -> dict:
        text = tokenizer.apply_chat_template(
            example["messages"], tokenize=False, add_generation_prompt=False
        )
        return {"text": text}

    dataset = dataset.map(format_chat, remove_columns=["messages"])

    sft_config = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        bf16=True,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        max_seq_length=1024,
        dataset_text_field="text",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        peft_config=lora_config,
        processing_class=tokenizer,
    )

    trainer.train()
    trainer.save_model(OUTPUT_DIR)  # saves the LoRA adapter — download this folder
    print(f"Saved LoRA adapter to {OUTPUT_DIR}/  (download and serve with serve_local.py)")


if __name__ == "__main__":
    main()
