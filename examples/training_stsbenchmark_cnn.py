"""
This example runs a CNN after the word embedding lookup. The output of the CNN is than pooled,
for example with mean-pooling.


"""
import torch
from torch.utils.data import DataLoader
import math
from soco_sentence_transformers import models, losses
from soco_sentence_transformers import SentencesDataset, LoggingHandler, SentenceTransformer
from soco_sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from soco_sentence_transformers.readers import *
import logging
from datetime import datetime

#### Just some code to print debug information to stdout
logging.basicConfig(format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO,
                    handlers=[LoggingHandler()])
#### /print debug information to stdout

# Read the dataset
batch_size = 32
sts_reader = STSDataReader('datasets/stsbenchmark')
model_save_path = 'output/training_stsbenchmark_bilstm-'+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")



# Map tokens to vectors using BERT
word_embedding_model = models.BERT('bert-base-uncased')

cnn = models.CNN(in_word_embedding_dimension=word_embedding_model.get_word_embedding_dimension(), out_channels=256, kernel_sizes=[1,3,5])

# Apply mean pooling to get one fixed sized sentence vector
pooling_model = models.Pooling(cnn.get_word_embedding_dimension(),
                               pooling_mode_mean_tokens=True,
                               pooling_mode_cls_token=False,
                               pooling_mode_max_tokens=False)


model = SentenceTransformer(modules=[word_embedding_model, cnn, pooling_model])


# Convert the dataset to a DataLoader ready for training
logging.info("Read STSbenchmark train dataset")
train_data = SentencesDataset(sts_reader.get_examples('sts-train.csv'), model=model)
train_dataloader = DataLoader(train_data, shuffle=True, batch_size=batch_size)
train_loss = losses.CosineSimilarityLoss(model=model)

logging.info("Read STSbenchmark dev dataset")
dev_data = SentencesDataset(examples=sts_reader.get_examples('sts-dev.csv'), model=model)
dev_dataloader = DataLoader(dev_data, shuffle=False, batch_size=batch_size)
evaluator = EmbeddingSimilarityEvaluator(dev_dataloader)

# Configure the training
num_epochs = 10
warmup_steps = math.ceil(len(train_data) * num_epochs / batch_size * 0.1) #10% of train data for warm-up
logging.info("Warmup-steps: {}".format(warmup_steps))

# Train the model
model.fit(train_objectives=[(train_dataloader, train_loss)],
          evaluator=evaluator,
          epochs=num_epochs,
          warmup_steps=warmup_steps,
          output_path=model_save_path
          )



##############################################################################
#
# Load the stored model and evaluate its performance on STS benchmark dataset
#
##############################################################################

model = SentenceTransformer(model_save_path)
test_data = SentencesDataset(examples=sts_reader.get_examples("sts-test.csv"), model=model)
test_dataloader = DataLoader(test_data, shuffle=False, batch_size=batch_size)
evaluator = EmbeddingSimilarityEvaluator(test_dataloader)

model.evaluate(evaluator)