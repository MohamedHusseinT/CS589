from sentence_transformers import SentenceTransformer, InputExample, losses, models, LoggingHandler
from torch.utils.data import DataLoader
import logging
import os

# Setup logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, handlers=[LoggingHandler()])

# Load base model
model_name = "all-MiniLM-L6-v2"
word_embedding_model = models.Transformer(model_name)
pooling_model = models.Pooling(word_embedding_model.get_word_embedding_dimension())
model = SentenceTransformer(modules=[word_embedding_model, pooling_model])

# Define labeled examples (query, correct_doc)
train_examples = [
    InputExample(texts=["What is Form G-1055?", "Form G-1055 is used to request fee waiver..."]),
    InputExample(texts=["How to file an asylum claim?", "To file an asylum claim, you must submit Form I-589..."]),
    # Add more manually rated pairs
]

# Prepare DataLoader
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)

# Define Loss
train_loss = losses.MultipleNegativesRankingLoss(model)

# Fine-tune
model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=1,
    warmup_steps=10,
    output_path="fine-tuned-miniLM"
)
