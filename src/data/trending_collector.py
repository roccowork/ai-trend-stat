"""
GitHub Trending 数据采集器
从 GitHub Trending 页面爬取真正的趋势项目
"""
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from typing import Optional


class TrendingCollector:
    """GitHub Trending 采集器"""

    BASE_URL = "https://github.com/trending"
    API_BASE = "https://api.github.com"

    # AI 相关语言和关键词过滤（可选）
    AI_LANGUAGES = ["python", "jupyter-notebook", "c++", "rust", "go", "typescript"]
    AI_KEYWORDS = [
        "llm", "gpt", "ai", "ml", "deep", "neural", "transformer", "diffusion",
        "langchain", "llama", "mistral", "openai", "anthropic", "huggingface",
        "machine-learning", "artificial-intelligence", "chatbot", "agent",
        "embedding", "vector", "rag", "fine-tune", "inference", "model"
    ]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, github_token: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.github_token = github_token
        self.api_headers = {"Accept": "application/vnd.github+json"}
        if github_token:
            self.api_headers["Authorization"] = f"Bearer {github_token}"

    def fetch_trending(self, language: str = "", since: str = "daily") -> list:
        """
        获取 Trending 项目

        Args:
            language: 编程语言过滤 (空字符串表示全部)
            since: 时间范围 - daily/weekly/monthly

        Returns:
            项目列表
        """
        url = self.BASE_URL
        if language:
            url = f"{url}/{language}"

        params = {"since": since}

        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return self._parse_trending_page(resp.text, since)
        except Exception as e:
            print(f"Error fetching trending ({language}, {since}): {e}")
            return []

    def _parse_trending_page(self, html: str, since: str) -> list:
        """解析 Trending 页面 HTML"""
        soup = BeautifulSoup(html, "html.parser")
        projects = []

        # 找到所有项目行
        repo_list = soup.select("article.Box-row")

        for rank, repo in enumerate(repo_list, 1):
            try:
                project = self._parse_repo_item(repo, rank, since)
                if project:
                    projects.append(project)
            except Exception as e:
                print(f"Error parsing repo: {e}")
                continue

        return projects

    def _parse_repo_item(self, repo, rank: int, since: str) -> Optional[dict]:
        """解析单个项目"""
        # 项目名称和链接
        name_elem = repo.select_one("h2 a")
        if not name_elem:
            return None

        full_name = name_elem.get("href", "").strip("/")
        if not full_name or "/" not in full_name:
            return None

        owner, name = full_name.split("/", 1)

        # 描述
        desc_elem = repo.select_one("p")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # 编程语言
        lang_elem = repo.select_one("[itemprop='programmingLanguage']")
        language = lang_elem.get_text(strip=True) if lang_elem else None

        # 总 Stars
        stars_elem = repo.select_one("a[href$='/stargazers']")
        stars = self._parse_number(stars_elem.get_text(strip=True)) if stars_elem else 0

        # Forks
        forks_elem = repo.select_one("a[href$='/forks']")
        forks = self._parse_number(forks_elem.get_text(strip=True)) if forks_elem else 0

        # 今日/本周/本月新增 Stars
        stars_today_elem = repo.select_one("span.d-inline-block.float-sm-right")
        stars_period = 0
        if stars_today_elem:
            stars_text = stars_today_elem.get_text(strip=True)
            stars_period = self._parse_number(stars_text)

        # 贡献者
        contributors = []
        contrib_elems = repo.select("a img.avatar")
        for contrib in contrib_elems[:5]:
            alt = contrib.get("alt", "")
            if alt.startswith("@"):
                contributors.append(alt[1:])

        return {
            "rank": rank,
            "name": name,
            "full_name": full_name,
            "owner": owner,
            "description": description,
            "url": f"https://github.com/{full_name}",
            "language": language,
            "stars": stars,
            "forks": forks,
            "stars_period": stars_period,
            "period": since,
            "contributors": contributors,
            "collected_at": datetime.utcnow().isoformat()
        }

    def _parse_number(self, text: str) -> int:
        """解析数字 (支持 1.2k, 10k 等格式)"""
        if not text:
            return 0
        text = text.lower().replace(",", "").strip()
        # 提取数字部分
        match = re.search(r"([\d.]+)\s*([km])?", text)
        if not match:
            return 0

        num = float(match.group(1))
        suffix = match.group(2)

        if suffix == "k":
            num *= 1000
        elif suffix == "m":
            num *= 1000000

        return int(num)

    def collect_all_trending(self, filter_ai: bool = False) -> dict:
        """
        采集所有时间范围的 Trending 数据

        Args:
            filter_ai: 是否只保留 AI 相关项目

        Returns:
            按时间范围分组的数据
        """
        result = {
            "daily": [],
            "weekly": [],
            "monthly": [],
            "collected_at": datetime.utcnow().isoformat()
        }

        for since in ["daily", "weekly", "monthly"]:
            print(f"采集 {since} trending...")
            projects = self.fetch_trending(since=since)

            if filter_ai:
                projects = [p for p in projects if self._is_ai_related(p)]

            result[since] = projects
            print(f"  获取 {len(projects)} 个项目")

        return result

    def _is_ai_related(self, project: dict) -> bool:
        """判断项目是否与 AI 相关"""
        text = f"{project.get('name', '')} {project.get('description', '')}".lower()

        for keyword in self.AI_KEYWORDS:
            if keyword in text:
                return True

        return False

    def save_to_json(self, data: dict, filename: str):
        """保存数据到 JSON 文件"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_repo_details(self, full_name: str) -> Optional[dict]:
        """通过 GitHub API 获取仓库详细信息"""
        import time
        url = f"{self.API_BASE}/repos/{full_name}"
        try:
            resp = requests.get(url, headers=self.api_headers, timeout=10)
            if resp.status_code == 403:
                print(f"  API 限流，等待中...")
                time.sleep(60)
                resp = requests.get(url, headers=self.api_headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"  获取 {full_name} 详情失败: {e}")
            return None

    def get_commit_activity(self, full_name: str) -> list:
        """获取最近一年的提交活动（每周数据）"""
        import time
        url = f"{self.API_BASE}/repos/{full_name}/stats/commit_activity"
        try:
            resp = requests.get(url, headers=self.api_headers, timeout=10)
            if resp.status_code == 202:
                time.sleep(2)
                resp = requests.get(url, headers=self.api_headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"  获取 {full_name} 提交活动失败: {e}")
        return []

    def enrich_with_api_data(self, projects: list, max_projects: int = 10) -> list:
        """用 GitHub API 补充项目详细数据"""
        import time
        enriched = []

        for i, project in enumerate(projects[:max_projects]):
            print(f"  获取详情 ({i+1}/{min(len(projects), max_projects)}): {project['full_name']}")

            # 获取仓库详情
            details = self.get_repo_details(project["full_name"])
            if details:
                project["created_at"] = details.get("created_at")
                project["updated_at"] = details.get("updated_at")
                project["pushed_at"] = details.get("pushed_at")
                project["open_issues"] = details.get("open_issues_count", 0)
                project["watchers"] = details.get("watchers_count", 0)
                project["topics"] = details.get("topics", [])
                project["license"] = details.get("license", {}).get("spdx_id") if details.get("license") else None
                project["default_branch"] = details.get("default_branch")
                project["size_kb"] = details.get("size", 0)

            # 获取提交活动
            commit_activity = self.get_commit_activity(project["full_name"])
            if commit_activity:
                # 计算最近 4 周的提交数
                recent_commits = sum(week.get("total", 0) for week in commit_activity[-4:])
                total_commits = sum(week.get("total", 0) for week in commit_activity)
                project["recent_commits_4w"] = recent_commits
                project["total_commits_year"] = total_commits
                project["commit_activity"] = [week.get("total", 0) for week in commit_activity]

            enriched.append(project)
            time.sleep(0.5)  # 避免触发限流

        # 未补充详情的项目也加入
        enriched.extend(projects[max_projects:])
        return enriched

    def collect_with_stats(self, filter_ai: bool = False, enrich_top_n: int = 15) -> dict:
        """采集 Trending 并补充统计数据"""
        result = {
            "daily": [],
            "weekly": [],
            "monthly": [],
            "collected_at": datetime.utcnow().isoformat()
        }

        for since in ["daily", "weekly", "monthly"]:
            print(f"\n采集 {since} trending...")
            projects = self.fetch_trending(since=since)

            if filter_ai:
                projects = [p for p in projects if self._is_ai_related(p)]

            print(f"  获取 {len(projects)} 个项目，正在补充详细数据...")
            projects = self.enrich_with_api_data(projects, max_projects=enrich_top_n)

            result[since] = projects
            print(f"  {since} 完成")

        return result


if __name__ == "__main__":
    import os
    from pathlib import Path

    # 从环境变量获取 GitHub Token（可选但推荐）
    token = os.getenv("GITHUB_TOKEN")
    collector = TrendingCollector(github_token=token)

    print("开始采集 GitHub Trending 数据（含统计数据）...")
    if token:
        print("已配置 GitHub Token，API 限额更高")
    else:
        print("未配置 GITHUB_TOKEN，API 限额较低（60次/小时）")

    # 采集全部 trending 并补充 API 数据
    data = collector.collect_with_stats(filter_ai=False, enrich_top_n=10)

    # 保存路径
    script_dir = Path(__file__).parent.resolve()
    output_file = script_dir.parent.parent / "public" / "data" / "trending.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    collector.save_to_json(data, str(output_file))

    total = len(data["daily"]) + len(data["weekly"]) + len(data["monthly"])
    print(f"\n采集完成！")
    print(f"  今日: {len(data['daily'])} 个项目")
    print(f"  本周: {len(data['weekly'])} 个项目")
    print(f"  本月: {len(data['monthly'])} 个项目")
    print(f"  已保存至: {output_file}")
