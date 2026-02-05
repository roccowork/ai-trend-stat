/**
 * AI 开源项目趋势分析 - 前端应用
 */

let pyodide = null;
let analysisResult = null;

// 初始化 Pyodide
async function initPyodide() {
    try {
        updateLoading("正在加载 Pyodide...");
        pyodide = await loadPyodide();

        updateLoading("正在安装依赖包...");
        await pyodide.loadPackage(["pandas", "numpy"]);

        // 加载分析代码
        updateLoading("正在初始化分析引擎...");
        await pyodide.runPythonAsync(`
import json
import pandas as pd
import numpy as np
from datetime import datetime

class TrendAnalyzer:
    def __init__(self, data):
        self.df = pd.DataFrame(data)
        self._preprocess()

    def _preprocess(self):
        date_cols = ["created_at", "updated_at", "pushed_at", "collected_at"]
        for col in date_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_datetime(self.df[col], errors='coerce')

        if "created_at" in self.df.columns:
            now = pd.Timestamp.utcnow()
            self.df["age_days"] = (now - self.df["created_at"]).dt.days

        if "stars" in self.df.columns and "age_days" in self.df.columns:
            self.df["stars_per_day"] = self.df["stars"] / self.df["age_days"].replace(0, 1)

    def get_top_projects(self, n=20, by="stars"):
        cols = ["name", "full_name", "description", "stars", "forks", "language", "url", "stars_per_day"]
        available_cols = [c for c in cols if c in self.df.columns]
        return self.df.nlargest(n, by)[available_cols].to_dict(orient="records")

    def get_fastest_growing(self, n=20):
        return self.get_top_projects(n, by="stars_per_day")

    def get_language_distribution(self):
        lang_counts = self.df["language"].value_counts().head(10)
        return {"labels": lang_counts.index.tolist(), "values": lang_counts.values.tolist()}

    def get_category_stats(self):
        topic_stats = {}
        for _, row in self.df.iterrows():
            topics = row.get("topics", [])
            if isinstance(topics, list):
                for topic in topics:
                    if topic not in topic_stats:
                        topic_stats[topic] = {"count": 0, "total_stars": 0}
                    topic_stats[topic]["count"] += 1
                    topic_stats[topic]["total_stars"] += row["stars"]
        sorted_topics = sorted(topic_stats.items(), key=lambda x: x[1]["count"], reverse=True)
        return dict(sorted_topics[:15])

    def get_summary_stats(self):
        return {
            "total_projects": len(self.df),
            "total_stars": int(self.df["stars"].sum()),
            "avg_stars": round(float(self.df["stars"].mean()), 1),
            "median_stars": float(self.df["stars"].median()),
            "total_forks": int(self.df["forks"].sum()),
            "languages_count": int(self.df["language"].nunique())
        }

def analyze_from_json(json_str):
    data = json.loads(json_str)
    analyzer = TrendAnalyzer(data)
    return json.dumps({
        "summary": analyzer.get_summary_stats(),
        "top_by_stars": analyzer.get_top_projects(20),
        "fastest_growing": analyzer.get_fastest_growing(20),
        "languages": analyzer.get_language_distribution(),
        "categories": analyzer.get_category_stats()
    })
        `);

        return true;
    } catch (error) {
        console.error("Pyodide 初始化失败:", error);
        return false;
    }
}

// 更新加载状态
function updateLoading(message) {
    document.querySelector("#loading p").textContent = message;
}

// 加载数据
async function loadData() {
    try {
        const response = await fetch("data/ai_projects.json");
        if (!response.ok) throw new Error("数据文件不存在");
        return await response.json();
    } catch (error) {
        console.error("加载数据失败:", error);
        // 返回示例数据用于演示
        return getSampleData();
    }
}

// 示例数据
function getSampleData() {
    return [
        { id: 1, name: "transformers", full_name: "huggingface/transformers", description: "State-of-the-art ML for PyTorch, TensorFlow, JAX", url: "https://github.com/huggingface/transformers", stars: 125000, forks: 25000, language: "Python", topics: ["transformers", "nlp", "machine-learning"], created_at: "2018-10-29T00:00:00Z", updated_at: "2024-01-15T00:00:00Z", pushed_at: "2024-01-15T00:00:00Z" },
        { id: 2, name: "langchain", full_name: "langchain-ai/langchain", description: "Building applications with LLMs", url: "https://github.com/langchain-ai/langchain", stars: 85000, forks: 12000, language: "Python", topics: ["llm", "ai-agent", "rag"], created_at: "2022-10-01T00:00:00Z", updated_at: "2024-01-15T00:00:00Z", pushed_at: "2024-01-15T00:00:00Z" },
        { id: 3, name: "stable-diffusion", full_name: "CompVis/stable-diffusion", description: "Latent Text-to-Image Diffusion", url: "https://github.com/CompVis/stable-diffusion", stars: 65000, forks: 10000, language: "Python", topics: ["stable-diffusion", "diffusion-model", "computer-vision"], created_at: "2022-08-10T00:00:00Z", updated_at: "2024-01-15T00:00:00Z", pushed_at: "2024-01-15T00:00:00Z" },
        { id: 4, name: "llama", full_name: "meta-llama/llama", description: "Open foundation and chat models", url: "https://github.com/meta-llama/llama", stars: 55000, forks: 9000, language: "Python", topics: ["llm", "large-language-model"], created_at: "2023-02-24T00:00:00Z", updated_at: "2024-01-15T00:00:00Z", pushed_at: "2024-01-15T00:00:00Z" },
        { id: 5, name: "ollama", full_name: "ollama/ollama", description: "Get up and running with Llama 2 and other LLMs locally", url: "https://github.com/ollama/ollama", stars: 52000, forks: 3500, language: "Go", topics: ["llm", "local-llm"], created_at: "2023-06-26T00:00:00Z", updated_at: "2024-01-15T00:00:00Z", pushed_at: "2024-01-15T00:00:00Z" },
        { id: 6, name: "pytorch", full_name: "pytorch/pytorch", description: "Tensors and Dynamic neural networks in Python", url: "https://github.com/pytorch/pytorch", stars: 78000, forks: 21000, language: "Python", topics: ["deep-learning", "neural-network", "machine-learning"], created_at: "2016-08-13T00:00:00Z", updated_at: "2024-01-15T00:00:00Z", pushed_at: "2024-01-15T00:00:00Z" },
        { id: 7, name: "whisper", full_name: "openai/whisper", description: "Robust Speech Recognition via Large-Scale Weak Supervision", url: "https://github.com/openai/whisper", stars: 58000, forks: 6500, language: "Python", topics: ["speech-recognition", "nlp", "transformer"], created_at: "2022-09-21T00:00:00Z", updated_at: "2024-01-15T00:00:00Z", pushed_at: "2024-01-15T00:00:00Z" },
        { id: 8, name: "comfyui", full_name: "comfyanonymous/ComfyUI", description: "Modular Stable Diffusion GUI", url: "https://github.com/comfyanonymous/ComfyUI", stars: 35000, forks: 3700, language: "Python", topics: ["stable-diffusion", "diffusion-model", "gui"], created_at: "2023-01-17T00:00:00Z", updated_at: "2024-01-15T00:00:00Z", pushed_at: "2024-01-15T00:00:00Z" },
        { id: 9, name: "tensorflow", full_name: "tensorflow/tensorflow", description: "An Open Source Machine Learning Framework", url: "https://github.com/tensorflow/tensorflow", stars: 182000, forks: 74000, language: "C++", topics: ["machine-learning", "deep-learning", "neural-network"], created_at: "2015-11-07T00:00:00Z", updated_at: "2024-01-15T00:00:00Z", pushed_at: "2024-01-15T00:00:00Z" },
        { id: 10, name: "AutoGPT", full_name: "Significant-Gravitas/AutoGPT", description: "AutoGPT is the vision of accessible AI for everyone", url: "https://github.com/Significant-Gravitas/AutoGPT", stars: 160000, forks: 42000, language: "Python", topics: ["ai-agent", "gpt", "autonomous-agents"], created_at: "2023-03-16T00:00:00Z", updated_at: "2024-01-15T00:00:00Z", pushed_at: "2024-01-15T00:00:00Z" },
    ];
}

// 分析数据
async function analyzeData(data) {
    const jsonStr = JSON.stringify(data);
    const result = await pyodide.runPythonAsync(`analyze_from_json('${jsonStr.replace(/'/g, "\\'")}')`);
    return JSON.parse(result);
}

// 渲染汇总卡片
function renderSummary(summary) {
    document.getElementById("total-projects").textContent = summary.total_projects.toLocaleString();
    document.getElementById("total-stars").textContent = formatNumber(summary.total_stars);
    document.getElementById("avg-stars").textContent = formatNumber(summary.avg_stars);
    document.getElementById("languages-count").textContent = summary.languages_count;
    document.getElementById("summary").style.display = "grid";
}

// 渲染排行榜
function renderRankings(topByStars, fastestGrowing) {
    renderTable("stars-table", topByStars, ["name", "description", "stars", "language"]);
    renderTable("growing-table", fastestGrowing, ["name", "stars_per_day", "stars", "language"]);
    document.getElementById("rankings").style.display = "block";
}

// 渲染表格
function renderTable(tableId, data, columns) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    tbody.innerHTML = data.map((item, index) => `
        <tr>
            <td>${index + 1}</td>
            <td><a href="${item.url}" target="_blank">${item.name}</a></td>
            ${columns.slice(1).map(col => {
                if (col === "description") {
                    return `<td class="description">${item[col] || "-"}</td>`;
                } else if (col === "stars" || col === "forks") {
                    return `<td>${formatNumber(item[col])}</td>`;
                } else if (col === "stars_per_day") {
                    return `<td>${item[col]?.toFixed(1) || "-"}</td>`;
                }
                return `<td>${item[col] || "-"}</td>`;
            }).join("")}
        </tr>
    `).join("");
}

// 渲染图表
function renderCharts(languages, categories) {
    // 语言分布饼图
    new Chart(document.getElementById("language-chart"), {
        type: "doughnut",
        data: {
            labels: languages.labels,
            datasets: [{
                data: languages.values,
                backgroundColor: [
                    "#00d4ff", "#7c3aed", "#f59e0b", "#10b981", "#ef4444",
                    "#6366f1", "#ec4899", "#14b8a6", "#f97316", "#8b5cf6"
                ]
            }]
        },
        options: {
            plugins: {
                legend: { position: "right", labels: { color: "#888" } }
            }
        }
    });

    // 主题统计柱状图
    const topicLabels = Object.keys(categories).slice(0, 10);
    const topicValues = topicLabels.map(t => categories[t].count);

    new Chart(document.getElementById("topics-chart"), {
        type: "bar",
        data: {
            labels: topicLabels,
            datasets: [{
                label: "项目数",
                data: topicValues,
                backgroundColor: "#00d4ff"
            }]
        },
        options: {
            indexAxis: "y",
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: "#888" }, grid: { color: "rgba(255,255,255,0.05)" } },
                y: { ticks: { color: "#888" }, grid: { display: false } }
            }
        }
    });

    document.getElementById("charts").style.display = "grid";
}

// 格式化数字
function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "K";
    return num.toString();
}

// 标签页切换
function initTabs() {
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            tab.classList.add("active");
            document.getElementById(tab.dataset.tab).classList.add("active");
        });
    });
}

// 主函数
async function main() {
    initTabs();

    const pyodideReady = await initPyodide();
    if (!pyodideReady) {
        updateLoading("Pyodide 加载失败，请刷新页面重试");
        return;
    }

    updateLoading("正在加载项目数据...");
    const data = await loadData();

    updateLoading("正在分析数据...");
    analysisResult = await analyzeData(data);

    // 隐藏加载，显示内容
    document.getElementById("loading").style.display = "none";

    renderSummary(analysisResult.summary);
    renderRankings(analysisResult.top_by_stars, analysisResult.fastest_growing);
    renderCharts(analysisResult.languages, analysisResult.categories);
}

// 启动
document.addEventListener("DOMContentLoaded", main);
