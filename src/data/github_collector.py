"""
GitHub AI 开源项目数据采集器
"""
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Optional

class GitHubCollector:
    """GitHub API 数据采集"""

    BASE_URL = "https://api.github.com"

    # AI 相关搜索关键词
    AI_TOPICS = [
        "llm", "large-language-model", "gpt", "transformer",
        "stable-diffusion", "diffusion-model", "computer-vision",
        "machine-learning", "deep-learning", "neural-network",
        "nlp", "chatbot", "ai-agent", "rag", "vector-database"
    ]

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {"Accept": "application/vnd.github+json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def search_repos(self, query: str, sort: str = "stars", per_page: int = 100) -> list:
        """搜索仓库"""
        url = f"{self.BASE_URL}/search/repositories"
        params = {
            "q": query,
            "sort": sort,
            "order": "desc",
            "per_page": per_page
        }

        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json().get("items", [])

    def get_repo_stats(self, owner: str, repo: str) -> dict:
        """获取仓库详细统计"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def get_star_history(self, owner: str, repo: str, per_page: int = 100) -> list:
        """获取 Star 历史（通过 Stargazers API）"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/stargazers"
        headers = {**self.headers, "Accept": "application/vnd.github.star+json"}

        resp = requests.get(url, headers=headers, params={"per_page": per_page})
        resp.raise_for_status()
        return resp.json()

    def get_commit_activity(self, owner: str, repo: str) -> list:
        """获取最近一年的提交活动"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/stats/commit_activity"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 202:
            # GitHub 正在计算，等待后重试
            time.sleep(2)
            resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def collect_ai_projects(self, min_stars: int = 1000) -> list:
        """采集 AI 相关热门项目"""
        all_projects = []
        seen = set()

        for topic in self.AI_TOPICS:
            query = f"topic:{topic} stars:>{min_stars}"
            try:
                repos = self.search_repos(query)
                for repo in repos:
                    if repo["id"] not in seen:
                        seen.add(repo["id"])
                        all_projects.append(self._extract_repo_data(repo))
                time.sleep(1)  # 避免触发限流
            except Exception as e:
                print(f"Error collecting {topic}: {e}")

        return sorted(all_projects, key=lambda x: x["stars"], reverse=True)

    def _extract_repo_data(self, repo: dict) -> dict:
        """提取仓库关键数据"""
        return {
            "id": repo["id"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "description": repo.get("description", ""),
            "url": repo["html_url"],
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "open_issues": repo["open_issues_count"],
            "language": repo.get("language"),
            "topics": repo.get("topics", []),
            "created_at": repo["created_at"],
            "updated_at": repo["updated_at"],
            "pushed_at": repo["pushed_at"],
            "collected_at": datetime.utcnow().isoformat()
        }

    def save_to_json(self, data: list, filename: str):
        """保存数据到 JSON 文件"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import os
    from pathlib import Path

    # 从环境变量获取 token（可选）
    token = os.getenv("GITHUB_TOKEN")
    collector = GitHubCollector(token)

    print("开始采集 AI 开源项目数据...")
    projects = collector.collect_ai_projects(min_stars=500)

    # 使用绝对路径
    script_dir = Path(__file__).parent.resolve()
    output_file = script_dir.parent.parent / "public" / "data" / "ai_projects.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    collector.save_to_json(projects, str(output_file))

    print(f"采集完成，共 {len(projects)} 个项目，已保存至 {output_file}")
