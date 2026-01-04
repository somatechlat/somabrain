"""Module reset_milvus."""


import os
import sys
from pymilvus import connections, utility

def main():
    """Execute main.
        """

    print("Connecting to Milvus...")
    connections.connect(host="127.0.0.1", port="20530")
    
    collection_name = "oak_options"
    if utility.has_collection(collection_name):
        print(f"Dropping collection {collection_name}...")
        utility.drop_collection(collection_name)
        print("Dropped.")
    else:
        print(f"Collection {collection_name} does not exist.")

if __name__ == "__main__":
    main()