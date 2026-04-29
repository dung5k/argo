$env:GIT_LFS_SKIP_SMUDGE=1
git clone https://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@huggingface.co/datasets/dung5k/argo_workspaces hf_restore
cd hf_restore
git reset --hard cc61be4e3904b59517ac734c08a0e7ba817b1c9e
git push -f origin main
cd ..
Remove-Item -Recurse -Force hf_restore
