"""GPU runtime shared by inference and paired evaluation."""

import contextlib
import random
import json
import hashlib
from pathlib import Path
from src.build_dataset import truncate_narrative
from src.prompt import FORMAT, messages_for
from src.schema import SYSTEM_PROMPT


class Generator:
    def __init__(self, config, adapter=None):
        if adapter and (Path(adapter) / "train_meta.json").exists():
            metadata = json.loads((Path(adapter) / "train_meta.json").read_text())
            for field, value in (
                ("system_prompt_sha256", SYSTEM_PROMPT),
                ("schema_prompt_sha256", FORMAT),
            ):
                if (
                    field in metadata
                    and metadata[field] != hashlib.sha256(value.encode()).hexdigest()
                ):
                    raise ValueError("Prompt differs from the one used to train this adapter")
        # Unsloth must patch transformers before it is imported.
        from unsloth import FastLanguageModel
        import torch

        self.torch = torch
        self.config = config
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is required. Run this command on Cathedral with scripts/cathedral.sh."
            )
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=config["model_id"],
            revision=config["model_revision"],
            max_seq_length=config["max_seq_length"],
            load_in_4bit=True,
            dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            trust_remote_code=False,
        )
        self.has_adapter = bool(adapter)
        if adapter:
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, adapter)
        FastLanguageModel.for_inference(self.model)
        self.model.eval()

    def generate(self, narrative, *, use_adapter=True, seed=42):
        narrative, truncated = truncate_narrative(
            narrative, self.tokenizer, self.config["narrative_tokens"]
        )
        text = self.tokenizer.apply_chat_template(
            messages_for(narrative),
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = self.tokenizer(text, return_tensors="pt", add_special_tokens=False).to("cuda")
        if (
            inputs.input_ids.shape[1] + self.config["max_new_tokens"]
            > self.config["max_seq_length"]
        ):
            raise ValueError("Prompt plus generation budget exceeds the configured context length")
        random.seed(seed)
        self.torch.manual_seed(seed)
        self.torch.cuda.manual_seed_all(seed)
        context = (
            self.model.disable_adapter()
            if self.has_adapter and not use_adapter
            else contextlib.nullcontext()
        )
        with context, self.torch.inference_mode():
            output = self.model.generate(
                **inputs,
                do_sample=True,
                temperature=self.config["temperature"],
                top_p=0.9,
                top_k=20,
                max_new_tokens=self.config["max_new_tokens"],
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                use_cache=True,
            )
        tokens = output[0, inputs.input_ids.shape[1] :]
        completion = self.tokenizer.decode(tokens, skip_special_tokens=True).strip()
        return {
            "text": completion,
            "tokens": len(tokens),
            "input_truncated": truncated,
            "narrative": narrative,
        }
