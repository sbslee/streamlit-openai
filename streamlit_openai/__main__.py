import argparse
import openai
from .version import __version__

def clear_vector_stores(client):
    vector_stores = []
    after = None
    while True:
        response = client.vector_stores.list(limit=20, after=after)
        if not response.data:
            break
        vector_stores.extend(response.data)
        if not response.has_more:
            break
        after = response.data[-1].id
    print(f"Found {len(vector_stores)} vector stores to delete.")
    for vector_store in vector_stores:
        response = client.vector_stores.delete(vector_store.id)
        print(response)

def clear_files(client):
    files = []
    after = None
    while True:
        response = client.files.list(limit=10000, after=after)
        if not response.data:
            break
        files.extend(response.data)
        if not response.has_more:
            break
        after = response.data[-1].id
    print(f"Found {len(files)} files to delete.")
    for file in files:
        response = client.files.delete(file.id)
        print(response)

def clear_all(client, config):
    clear_vector_stores(client, config)
    clear_files(client, config)

def main():
    choices = {
        "clear-vector-stores": clear_vector_stores,
        "clear-files": clear_files,
        "clear-all": clear_all,
    }
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=[x for x in choices.keys()])
    args = parser.parse_args()
    client = openai.OpenAI()
    choices[args.command](client)

if __name__ == "__main__":
    main()