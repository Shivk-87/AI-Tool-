import os
import shutil
from src.indexer.fetcher import clone_repo

SAMPLE_REPO = "https://github.com/octocat/Hello-World.git"

def test_clone_sample_repo():
    dest = clone_repo(SAMPLE_REPO, "hello-world-sample")
    assert os.path.exists(dest)
    # cleanup
    shutil.rmtree(dest)

if __name__ == '__main__':
    test_clone_sample_repo()
    print('fetcher test passed')
