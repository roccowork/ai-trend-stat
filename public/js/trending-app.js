/**
 * GitHub Trending 趋势分析 - 前端应用
 * 集成统计建模分析结果
 */

let trendingData = null;
let analysisData = null;
let currentPeriod = "daily";
let languageChart = null;
let starsChart = null;
let commitChart = null;

// 加载数据
async function loadData() {
    try {
        const [trendingResp, analysisResp] = await Promise.all([
            fetch("data/trending.json"),
            fetch("data/analysis.json")
        ]);

        if (!trendingResp.ok) throw new Error("trending.json 不存在");

        const trending = await trendingResp.json();
        const analysis = analysisResp.ok ? await analysisResp.json() : null;

        return { trending, analysis };
    } catch (error) {
        console.error("加载数据失败:", error);
        return null;
    }
}

// 渲染汇总卡片
function renderSummary(summary) {
    document.getElementById("total-projects").textContent = summary.total_projects || "-";
    document.getElementById("total-stars-period").textContent = "+" + formatNumber(summary.total_stars_period || 0);
    document.getElementById("total-stars").textContent = formatNumber(summary.total_stars || 0);
    document.getElementById("languages-count").textContent = summary.languages_count || "-";
}

// 渲染统计分析卡片
function renderStatsAnalysis(summary) {
    document.getElementById("avg-stars").textContent = formatNumber(summary.avg_stars || 0);
    document.getElementById("median-stars").textContent = formatNumber(summary.median_stars || 0);
    document.getElementById("avg-age").textContent = Math.round(summary.avg_age_days || 0);
    document.getElementById("total-commits").textContent = formatNumber(summary.total_recent_commits || 0);
}

// 渲染排行榜（带评分）
function renderRankings(projects, period) {
    const titles = {
        daily: "🔥 今日 Trending 排行",
        weekly: "📅 本周 Trending 排行",
        monthly: "📆 本月 Trending 排行"
    };
    document.getElementById("ranking-title").textContent = titles[period];

    const tbody = document.querySelector("#trending-table tbody");
    tbody.innerHTML = projects.map(project => {
        const scores = project.scores || {};
        const totalScore = scores.total;
        const scoreDisplay = (totalScore === null || totalScore === undefined || isNaN(totalScore)) ? "-" : totalScore.toFixed(1);
        const scoreClass = getScoreClass(totalScore);

        return `
        <tr>
            <td class="rank">${project.rank}</td>
            <td>
                <a href="${project.url}" target="_blank" class="project-name">
                    <strong>${project.name}</strong>
                    <span class="owner">@${project.owner}</span>
                </a>
            </td>
            <td class="description">${project.description || "-"}</td>
            <td><span class="lang-badge">${project.language || "-"}</span></td>
            <td class="stars-period">+${formatNumber(project.stars_period)}</td>
            <td class="stars-total">${formatNumber(project.stars)}</td>
            <td class="score ${scoreClass}" title="热度:${scores.heat || '-'} 活跃:${scores.activity || '-'} 成长:${scores.growth || '-'}">
                ${scoreDisplay}
            </td>
        </tr>
    `}).join("");
}

// 获取评分样式类
function getScoreClass(score) {
    if (score === null || score === undefined || isNaN(score)) return "score-na";
    if (score >= 70) return "score-high";
    if (score >= 50) return "score-medium";
    return "score-low";
}

// 渲染图表
function renderCharts(projects, languages) {
    // 销毁旧图表
    if (languageChart) languageChart.destroy();
    if (starsChart) starsChart.destroy();

    // 语言分布（使用分析数据）
    if (languages && languages.labels) {
        languageChart = new Chart(document.getElementById("language-chart"), {
            type: "doughnut",
            data: {
                labels: languages.labels.slice(0, 8),
                datasets: [{
                    data: languages.project_counts.slice(0, 8),
                    backgroundColor: [
                        "#00d4ff", "#7c3aed", "#f59e0b", "#10b981",
                        "#ef4444", "#6366f1", "#ec4899", "#14b8a6"
                    ]
                }]
            },
            options: {
                plugins: {
                    legend: { position: "right", labels: { color: "#888" } }
                }
            }
        });
    }

    // Stars 增长 Top 10
    const top10 = [...projects].sort((a, b) => (b.stars_period || 0) - (a.stars_period || 0)).slice(0, 10);

    starsChart = new Chart(document.getElementById("stars-chart"), {
        type: "bar",
        data: {
            labels: top10.map(p => p.name),
            datasets: [{
                label: "新增 Stars",
                data: top10.map(p => p.stars_period || 0),
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
}

// 渲染提交趋势图表
function renderCommitTrends(commitTrends) {
    if (commitChart) commitChart.destroy();

    if (!commitTrends || commitTrends.error) {
        document.getElementById("commit-section").style.display = "none";
        return;
    }

    document.getElementById("commit-section").style.display = "block";

    // 更新趋势指示器
    const trendValue = document.getElementById("trend-value");
    const percent = commitTrends.trend_percent || 0;
    const direction = commitTrends.trend_direction || "stable";

    let trendText = "";
    let trendClass = "";

    if (direction === "up") {
        trendText = `↑ ${percent.toFixed(1)}%`;
        trendClass = "trend-up";
    } else if (direction === "down") {
        trendText = `↓ ${Math.abs(percent).toFixed(1)}%`;
        trendClass = "trend-down";
    } else {
        trendText = "→ 稳定";
        trendClass = "trend-stable";
    }

    trendValue.textContent = trendText;
    trendValue.className = `trend-value ${trendClass}`;

    // 绘制提交趋势图
    const weeklyCommits = commitTrends.weekly_commits || [];
    const labels = weeklyCommits.map((_, i) => `W${i + 1}`);

    commitChart = new Chart(document.getElementById("commit-chart"), {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "提交数",
                data: weeklyCommits,
                borderColor: "#10b981",
                backgroundColor: "rgba(16, 185, 129, 0.1)",
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: "#888" }, grid: { color: "rgba(255,255,255,0.05)" } },
                y: { ticks: { color: "#888" }, grid: { color: "rgba(255,255,255,0.05)" } }
            }
        }
    });
}

// 切换时间范围
function switchPeriod(period) {
    currentPeriod = period;

    // 更新按钮状态
    document.querySelectorAll(".period-tab").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.period === period);
    });

    // 获取数据
    let projects = trendingData[period] || [];
    let periodAnalysis = analysisData ? analysisData[period] : null;

    // 如果有分析数据，使用带评分的项目列表
    if (periodAnalysis && periodAnalysis.projects) {
        projects = periodAnalysis.projects;
    }

    // 渲染各部分
    if (periodAnalysis && periodAnalysis.summary) {
        renderSummary(periodAnalysis.summary);
        renderStatsAnalysis(periodAnalysis.summary);
        document.getElementById("stats-analysis").style.display = "block";
    } else {
        // 回退到基础统计
        const basicSummary = {
            total_projects: projects.length,
            total_stars_period: projects.reduce((sum, p) => sum + (p.stars_period || 0), 0),
            total_stars: projects.reduce((sum, p) => sum + (p.stars || 0), 0),
            languages_count: new Set(projects.map(p => p.language).filter(Boolean)).size
        };
        renderSummary(basicSummary);
        document.getElementById("stats-analysis").style.display = "none";
    }

    renderRankings(projects, period);
    renderCharts(projects, periodAnalysis ? periodAnalysis.languages : null);
    renderCommitTrends(periodAnalysis ? periodAnalysis.commit_trends : null);
}

// 格式化数字
function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return "-";
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "K";
    return Math.round(num).toString();
}

// 格式化日期时间
function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
    });
}

// 初始化时间范围切换
function initPeriodTabs() {
    document.querySelectorAll(".period-tab").forEach(btn => {
        btn.addEventListener("click", () => {
            switchPeriod(btn.dataset.period);
        });
    });
}

// 主函数
async function main() {
    initPeriodTabs();

    // 加载数据
    const data = await loadData();

    if (!data || !data.trending) {
        document.querySelector("#loading p").textContent = "数据加载失败，请刷新重试";
        return;
    }

    trendingData = data.trending;
    analysisData = data.analysis;

    // 隐藏加载，显示内容
    document.getElementById("loading").style.display = "none";
    document.getElementById("period-selector").style.display = "flex";
    document.getElementById("summary").style.display = "grid";
    document.getElementById("rankings").style.display = "block";
    document.getElementById("charts").style.display = "grid";
    document.getElementById("update-info").style.display = "block";

    // 显示更新时间
    const collectedAt = analysisData?.collected_at || trendingData.collected_at;
    if (collectedAt) {
        document.getElementById("update-time").textContent = formatDateTime(collectedAt);
    }

    // 默认显示今日数据
    switchPeriod("daily");
}

// 启动
document.addEventListener("DOMContentLoaded", main);
