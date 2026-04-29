$env:GIT_LFS_SKIP_SMUDGE=1
$token = "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"
$repo_url = "https://user:$token@huggingface.co/datasets/dung5k/argo_workspaces"

git clone $repo_url hf_restore2
cd hf_restore2
git reset --hard cc61be4e3904b59517ac734c08a0e7ba817b1c9e
git push -f origin main
cd ..
Remove-Item -Recurse -Force hf_restore2
