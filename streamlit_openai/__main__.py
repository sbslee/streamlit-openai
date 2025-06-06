import argparse
import openai
from .version import __version__

def delete_all(client, keep):
    delete_files(client, keep)
    delete_vector_stores(client, keep)
    delete_containers(client, keep)

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

def delete_vector_stores(client, keep):
    whitelist = [x for x in keep if x.startswith("vs_")]
    vector_stores = []
    after = None
    while True:
        response = client.vector_stores.list(limit=100, after=after)
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

def delete_containers(client, keep):
    whitelist = [x for x in keep if x.startswith("cntr_")]
    containers = []
    after = None
    while True:
        response = client.containers.list(limit=100, after=after)
        if not response.data:
            break
        containers.extend(response.data)
        if not response.has_more:
            break
        after = response.data[-1].id
    print(f"Found {len(containers)} containers to delete.")
    for container in containers:
        if container.id in whitelist:
            print(f"Skipping {container.id} as it is in the keep list.")
            continue
        response = client.containers.delete(container.id)
        print(response)

def main():
    choices = {
        "delete-all": delete_all,
        "delete-files": delete_files,
        "delete-vector-stores": delete_vector_stores,
        "delete-containers": delete_containers,
    }
    parser = argparse.ArgumentParser(
        description="CLI tool to delete OpenAI files, vector stores, and containers."
    )
    parser.add_argument("command", choices=[x for x in choices.keys()], help="command to execute")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}", help="show the version of the tool")
    parser.add_argument("--keep", nargs="+", metavar="ID", default=[], help="list of IDs to keep (e.g., file-123, vs_456, cntr_789)")
    args = parser.parse_args()
    client = openai.OpenAI()
    choices[args.command](client, args.keep)

if __name__ == "__main__":
    main()