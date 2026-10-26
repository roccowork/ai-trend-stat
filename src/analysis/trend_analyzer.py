"""
GitHub Trending 项目趋势分析器
使用 statsmodels 进行统计建模
"""
import json
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


def clean_for_json(obj: Any) -> Any:
    """清理数据使其可以序列化为 JSON（处理 NaN、Infinity 等）"""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif hasattr(obj, 'item'):  # numpy types
        return clean_for_json(obj.item())
    return obj


def num(value: Any, default: float) -> float:
    """取数值；缺失或 NaN（没补充到 API 详情的项目）时用默认值，避免评分变成 NaN、排序错乱"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(v) or math.isinf(v) else v


def load_pandas():
    """延迟加载 pandas"""
    import pandas as pd
    return pd


def load_statsmodels():
    """延迟加载 statsmodels"""
    import statsmodels.api as sm
    return sm


class TrendingAnalyzer:
    """Trending 项目统计分析器"""

    def __init__(self, data: dict):
        """
        Args:
            data: trending.json 的数据结构 {"daily": [...], "weekly": [...], "monthly": [...]}
        """
        self.pd = load_pandas()
        self.raw_data = data
        self.daily = self.pd.DataFrame(data.get("daily", []))
        self.weekly = self.pd.DataFrame(data.get("weekly", []))
        self.monthly = self.pd.DataFrame(data.get("monthly", []))
        self._preprocess()

    def _preprocess(self):
        """数据预处理"""
        for df in [self.daily, self.weekly, self.monthly]:
            if df.empty:
                continue

            # 转换日期
            date_cols = ["created_at", "updated_at", "pushed_at"]
            for col in date_cols:
                if col in df.columns:
                    df[col] = self.pd.to_datetime(df[col], errors="coerce")

            # 计算项目年龄（天）
            if "created_at" in df.columns:
                now = self.pd.Timestamp.now("UTC")
                df["age_days"] = (now - df["created_at"]).dt.days

            # 计算历史日均 Star
            if "stars" in df.columns and "age_days" in df.columns:
                df["historical_stars_per_day"] = df["stars"] / df["age_days"].replace(0, 1)

    def calculate_project_scores(self, period: str = "daily") -> List[Dict]:
        """
        计算项目综合评分

        评分维度：
        - 热度分 (40%): 基于期间新增 Stars
        - 活跃分 (30%): 基于近期提交数
        - 成长分 (20%): 当前增速 vs 历史增速
        - 成熟分 (10%): 基于项目年龄和总 Stars

        Returns:
            带评分的项目列表
        """
        df = getattr(self, period, self.daily)
        if df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            project = clean_for_json(row.to_dict())

            # 热度分 (0-100): 基于期间新增 Stars 排名
            stars_period = num(row.get("stars_period"), 0)
            max_stars_period = num(df["stars_period"].max(), 1) if "stars_period" in df.columns else 1
            heat_score = (stars_period / max(max_stars_period, 1)) * 100

            # 活跃分 (0-100): 基于近4周提交
            recent_commits = num(row.get("recent_commits_4w"), 0)
            max_commits = num(df["recent_commits_4w"].max(), 1) if "recent_commits_4w" in df.columns else 1
            activity_score = (recent_commits / max(max_commits, 1)) * 100 if recent_commits else 50

            # 成长分 (0-100): 当前日增速 vs 历史日增速
            historical_rate = num(row.get("historical_stars_per_day"), 0)
            period_days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 1)
            current_rate = stars_period / period_days if stars_period else 0

            if historical_rate > 0:
                growth_ratio = current_rate / historical_rate
                growth_score = min(growth_ratio * 50, 100)  # 2倍历史增速 = 满分
            else:
                growth_score = 50

            # 成熟分 (0-100): 基于项目年龄和总 Stars
            age_days = num(row.get("age_days"), 365)
            total_stars = num(row.get("stars"), 0)
            # 成熟项目：年龄 > 180天 且 Stars > 1000
            maturity_score = min((age_days / 365) * 30 + (total_stars / 10000) * 70, 100)

            # 综合评分
            total_score = (
                heat_score * 0.4 +
                activity_score * 0.3 +
                growth_score * 0.2 +
                maturity_score * 0.1
            )

            project["scores"] = {
                "total": round(total_score, 1),
                "heat": round(heat_score, 1),
                "activity": round(activity_score, 1),
                "growth": round(growth_score, 1),
                "maturity": round(maturity_score, 1)
            }

            results.append(project)

        # 按总分排序
        results.sort(key=lambda x: x["scores"]["total"], reverse=True)
        return results

    def analyze_commit_trends(self, period: str = "daily") -> Dict:
        """分析提交趋势"""
        df = getattr(self, period, self.daily)
        if df.empty or "commit_activity" not in df.columns:
            return {"error": "无提交数据"}

        all_activity = []
        for _, row in df.iterrows():
            activity = row.get("commit_activity")
            # 确保是列表类型且非空
            if isinstance(activity, list) and len(activity) > 0:
                all_activity.append(activity)

        if not all_activity:
            return {"error": "无提交数据"}

        # 聚合所有项目的提交活动
        max_len = max(len(a) for a in all_activity)
        aggregated = [0] * max_len

        for activity in all_activity:
            for i, val in enumerate(activity):
                if i < max_len:
                    aggregated[i] += val

        # 计算趋势（最近12周 vs 之前12周）
        if len(aggregated) >= 24:
            recent = sum(aggregated[-12:])
            previous = sum(aggregated[-24:-12])
            trend = ((recent - previous) / max(previous, 1)) * 100
        else:
            trend = 0

        return {
            "weekly_commits": aggregated[-12:] if len(aggregated) >= 12 else aggregated,
            "trend_percent": round(trend, 1),
            "trend_direction": "up" if trend > 5 else ("down" if trend < -5 else "stable")
        }

    def fit_growth_model(self, project: Dict) -> Dict:
        """
        对单个项目拟合增长模型

        使用线性回归分析提交活动趋势
        """
        commit_activity = project.get("commit_activity", [])
        if not commit_activity or len(commit_activity) < 4:
            return {"error": "数据不足"}

        try:
            sm = load_statsmodels()

            # 准备数据
            y = np.array(commit_activity[-12:])  # 最近12周
            X = np.arange(len(y))
            X = sm.add_constant(X)

            # 线性回归
            model = sm.OLS(y, X).fit()

            slope = model.params[1]
            r_squared = model.rsquared

            return {
                "model": "linear",
                "slope": round(float(slope), 2),  # 每周提交变化
                "r_squared": round(float(r_squared), 3),
                "trend": "increasing" if slope > 0.5 else ("decreasing" if slope < -0.5 else "stable"),
                "confidence": "high" if r_squared > 0.7 else ("medium" if r_squared > 0.4 else "low")
            }
        except Exception as e:
            return {"error": str(e)}

    def predict_stars(self, project: Dict, days: int = 30) -> Dict:
        """预测项目未来 Stars 增长"""
        stars_period = project.get("stars_period", 0)
        period = project.get("period", "daily")
        current_stars = project.get("stars", 0)

        # 计算日均增长
        period_days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 1)
        daily_rate = stars_period / period_days

        # 简单线性预测
        predicted_gain = daily_rate * days
        predicted_total = current_stars + predicted_gain

        # 计算置信区间 (±20% 波动)
        lower = current_stars + predicted_gain * 0.8
        upper = current_stars + predicted_gain * 1.2

        return {
            "current_stars": current_stars,
            "daily_rate": round(daily_rate, 1),
            "predicted_gain": round(predicted_gain),
            "predicted_total": round(predicted_total),
            "confidence_interval": {
                "lower": round(lower),
                "upper": round(upper)
            },
            "prediction_days": days
        }

    def get_language_stats(self, period: str = "daily") -> Dict:
        """编程语言统计分析"""
        df = getattr(self, period, self.daily)
        if df.empty:
            return {}

        lang_stats = df.groupby("language").agg({
            "stars": "sum",
            "stars_period": "sum",
            "name": "count"
        }).rename(columns={"name": "project_count"})

        lang_stats["avg_stars_period"] = lang_stats["stars_period"] / lang_stats["project_count"]
        lang_stats = lang_stats.sort_values("stars_period", ascending=False)

        return {
            "labels": lang_stats.index.tolist(),
            "project_counts": lang_stats["project_count"].tolist(),
            "total_stars": lang_stats["stars"].tolist(),
            "period_stars": lang_stats["stars_period"].tolist(),
            "avg_growth": lang_stats["avg_stars_period"].round(1).tolist()
        }

    def get_summary_statistics(self, period: str = "daily") -> Dict:
        """获取汇总统计"""
        df = getattr(self, period, self.daily)
        if df.empty:
            return {}

        stats = {
            "total_projects": len(df),
            "total_stars": int(df["stars"].sum()),
            "total_stars_period": int(df["stars_period"].sum()) if "stars_period" in df.columns else 0,
            "avg_stars": round(float(df["stars"].mean()), 1),
            "median_stars": round(float(df["stars"].median()), 1),
            "languages_count": df["language"].nunique(),
        }

        if "age_days" in df.columns:
            stats["avg_age_days"] = round(float(df["age_days"].mean()), 0)
            stats["youngest_project"] = df.loc[df["age_days"].idxmin(), "name"] if not df["age_days"].isna().all() else None

        if "recent_commits_4w" in df.columns:
            stats["total_recent_commits"] = int(df["recent_commits_4w"].sum())
            stats["avg_recent_commits"] = round(float(df["recent_commits_4w"].mean()), 1)

        return stats

    def generate_full_analysis(self) -> Dict:
        """生成完整分析报告"""
        result = {
            "collected_at": self.raw_data.get("collected_at"),
            "daily": {
                "summary": self.get_summary_statistics("daily"),
                "projects": self.calculate_project_scores("daily"),
                "languages": self.get_language_stats("daily"),
                "commit_trends": self.analyze_commit_trends("daily")
            },
            "weekly": {
                "summary": self.get_summary_statistics("weekly"),
                "projects": self.calculate_project_scores("weekly"),
                "languages": self.get_language_stats("weekly"),
                "commit_trends": self.analyze_commit_trends("weekly")
            },
            "monthly": {
                "summary": self.get_summary_statistics("monthly"),
                "projects": self.calculate_project_scores("monthly"),
                "languages": self.get_language_stats("monthly"),
                "commit_trends": self.analyze_commit_trends("monthly")
            }
        }
        # 清理 NaN 值
        return clean_for_json(result)


# 供 Pyodide 调用的入口函数
def analyze_trending(json_str: str) -> str:
    """从 JSON 字符串分析 Trending 数据"""
    data = json.loads(json_str)
    analyzer = TrendingAnalyzer(data)
    result = analyzer.generate_full_analysis()
    return json.dumps(result, default=str)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 读取 trending.json
    data_file = Path(__file__).parent.parent.parent / "public" / "data" / "trending.json"

    if not data_file.exists():
        print(f"数据文件不存在: {data_file}")
        sys.exit(1)

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    analyzer = TrendingAnalyzer(data)
    report = analyzer.generate_full_analysis()

    # 保存分析结果
    output_file = data_file.parent / "analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    print(f"分析完成，结果已保存至: {output_file}")

    # 打印摘要
    daily = report["daily"]
    print(f"\n=== 今日 Trending 统计 ===")
    print(f"项目数: {daily['summary'].get('total_projects', 0)}")
    print(f"总新增 Stars: {daily['summary'].get('total_stars_period', 0)}")
    print(f"平均 Stars: {daily['summary'].get('avg_stars', 0)}")

    if daily["projects"]:
        print(f"\n=== Top 5 项目评分 ===")
        for p in daily["projects"][:5]:
            scores = p.get("scores", {})
            print(f"  {p['name']}: 总分 {scores.get('total', 0)} (热度:{scores.get('heat', 0)} 活跃:{scores.get('activity', 0)})")
