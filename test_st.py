import sys
print("Loading model...")
from sentence_transformers import SentenceTransformer
import warnings
warnings.filterwarnings("ignore")
try:
    model = SentenceTransformer("BAAI/bge-m3")
    print("Model loaded successfully!")
    out = model.encode(["test"])
    print("Encoding worked, shape:", out.shape)
except Exception as e:
    print("Error:", e)
