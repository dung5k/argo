from huggingface_hub import HfApi

api = HfApi(token="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")
repo_id = "dung5k/argo_workspaces"

commits = api.list_repo_commits(repo_id=repo_id, repo_type="dataset")
for c in commits[9:15]:
    print(f"Commit: {c.commit_id} - {c.title}")
