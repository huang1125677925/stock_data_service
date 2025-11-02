from typing import List, Dict, Optional
from git import Repo


DEFAULT_REPO_PATH = '/Users/huangchuang/stock_analyse'


def get_git_commits_info(repo_path: Optional[str] = None, limit: Optional[int] = None) -> List[Dict]:
    """
    获取指定仓库的提交信息。

    参数：
    - repo_path (str, 可选): 仓库本地路径，默认使用预设路径。
    - limit (int, 可选): 限制返回的提交数量（从最近开始）。

    返回：
    - list[dict]: 每个提交包含 commit_id、authored_datetime、author_name、message。
    """
    path = repo_path or DEFAULT_REPO_PATH
    repo = Repo(path)

    commits_iter = repo.iter_commits()
    if limit and isinstance(limit, int) and limit > 0:
        commits = list(commits_iter)[:limit]
    else:
        commits = list(commits_iter)

    records = []
    for c in commits:
        records.append({
            # 'commit_id': c.hexsha,
            'authored_datetime': c.authored_datetime.isoformat(),
            # 'author_name': getattr(c.author, 'name', None),
            'message': c.message.strip(),
        })

    return records