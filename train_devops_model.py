# train_devops_model.py
import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, get_peft_model
from datasets import Dataset

def create_training_dataset():
    """Create training dataset from your DevOps examples"""
    examples = []
    
    # Load your custom examples
    dockerfile_examples = load_dockerfile_examples()
    k8s_examples = load_k8s_examples()
    
    for example in dockerfile_examples + k8s_examples:
        examples.append({
            "input": example["prompt"],
            "output": example["expected_config"]
        })
    
    return Dataset.from_list(examples)

def fine_tune_model():
    # Load base model
    model = AutoModelForCausalLM.from_pretrained("codellama/CodeLlama-13b-Instruct-hf")
    tokenizer = AutoTokenizer.from_pretrained("codellama/CodeLlama-13b-Instruct-hf")
    
    # LoRA configuration
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.1,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, lora_config)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir="./devops-model",
        overwrite_output_dir=True,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        warmup_steps=100,
        logging_steps=50,
        save_steps=500,
        evaluation_strategy="steps",
        eval_steps=500,
        learning_rate=2e-4,
        fp16=True,  # Use mixed precision
    )
    
    # Create trainer and train
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=create_training_dataset(),
        tokenizer=tokenizer,
    )
    
    trainer.train()
    trainer.save_model("./fine-tuned-devops-model")

if __name__ == "__main__":
    fine_tune_model()