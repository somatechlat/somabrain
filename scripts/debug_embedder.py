import sys

sys.path.insert(0, "/app")
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "somabrain.settings.standalone"
import django

django.setup()

from somabrain.admin.core.embeddings import make_embedder
from django.conf import settings
import numpy as np

print(f"Numpy version: {np.__version__}")

print("Creating embedder...")
try:
    embedder = make_embedder(settings)
    print(f"Embedder created: {embedder}")
except Exception as e:
    print(f"Failed to create embedder: {e}")
    sys.exit(1)

text = "test string"
print(f"Embedding '{text}'...")
try:
    vec = embedder.embed(text)
    print(f"Vector shape: {vec.shape}")
    print("Success!")
except Exception as e:
    print(f"Embedding failed: {e}")
