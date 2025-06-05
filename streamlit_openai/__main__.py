import argparse
import openai
from .version import __version__

def delete_vector_stores(client, keep):
    whitelist = [x for x in keep if x.startswith("vs_")]
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
        if vector_store.id in whitelist:
            print(f"Skipping {vector_store.id} as it is in the keep list.")
            continue
        response = client.vector_stores.delete(vector_store.id)
        print(response)

def delete_files(client, keep):
    whitelist = [x for x in keep if x.startswith("file-")]
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
        if file.id in whitelist:
            print(f"Skipping {file.id} as it is in the keep list.")
            continue
        response = client.files.delete(file.id)
        print(response)

def delete_all(client, keep):
    delete_vector_stores(client, keep)
    delete_files(client, keep)

def main():
    choices = {
        "delete-vector-stores": delete_vector_stores,
        "delete-files": delete_files,
        "delete-all": delete_all,
    }
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=[x for x in choices.keys()])
    parser.add_argument("--keep", nargs="+", default=[])
    args = parser.parse_args()
    client = openai.OpenAI()
    choices[args.command](client, args.keep)

if __name__ == "__main__":
    main()