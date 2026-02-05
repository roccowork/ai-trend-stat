/**
 * Cloudflare Worker - AI 趋势分析 API
 */

export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);

        // CORS 头
        const corsHeaders = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        };

        // 处理 OPTIONS 请求
        if (request.method === "OPTIONS") {
            return new Response(null, { headers: corsHeaders });
        }

        // 路由
        switch (url.pathname) {
            case "/api/projects":
                return handleGetProjects(env, corsHeaders);

            case "/api/refresh":
                return handleRefresh(env, corsHeaders);

            case "/api/stats":
                return handleGetStats(env, corsHeaders);

            default:
                return new Response(JSON.stringify({ error: "Not Found" }), {
                    status: 404,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
        }
    }
};

// 获取项目列表
async function handleGetProjects(env, corsHeaders) {
    try {
        // 从 KV 存储读取缓存数据
        let data = await env.AI_TRENDS_KV?.get("projects", "json");

        if (!data) {
            // 如果没有缓存，返回空数组
            data = [];
        }

        return new Response(JSON.stringify(data), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
    } catch (error) {
        return new Response(JSON.stringify({ error: error.message }), {
            status: 500,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
    }
}

// 刷新数据（从 GitHub 拉取）
async function handleRefresh(env, corsHeaders) {
    try {
        const projects = await fetchGitHubProjects(env.GITHUB_TOKEN);

        // 存储到 KV
        if (env.AI_TRENDS_KV) {
            await env.AI_TRENDS_KV.put("projects", JSON.stringify(projects), {
                expirationTtl: 3600 // 1小时过期
            });
        }

        return new Response(JSON.stringify({
            success: true,
            count: projects.length
        }), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
    } catch (error) {
        return new Response(JSON.stringify({ error: error.message }), {
            status: 500,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
    }
}

// 获取统计概要
async function handleGetStats(env, corsHeaders) {
    try {
        let data = await env.AI_TRENDS_KV?.get("projects", "json") || [];

        const stats = {
            total_projects: data.length,
            total_stars: data.reduce((sum, p) => sum + (p.stars || 0), 0),
            total_forks: data.reduce((sum, p) => sum + (p.forks || 0), 0),
            languages: [...new Set(data.map(p => p.language).filter(Boolean))].length,
            last_updated: await env.AI_TRENDS_KV?.get("last_updated") || null
        };

        return new Response(JSON.stringify(stats), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
    } catch (error) {
        return new Response(JSON.stringify({ error: error.message }), {
            status: 500,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
    }
}

// 从 GitHub 获取 AI 项目
async function fetchGitHubProjects(token) {
    const topics = ["llm", "large-language-model", "stable-diffusion", "machine-learning", "deep-learning"];
    const allProjects = [];
    const seen = new Set();

    const headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Trends-Analyzer"
    };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    for (const topic of topics) {
        try {
            const response = await fetch(
                `https://api.github.com/search/repositories?q=topic:${topic}+stars:>1000&sort=stars&per_page=50`,
                { headers }
            );

            if (!response.ok) continue;

            const data = await response.json();
            for (const repo of data.items || []) {
                if (!seen.has(repo.id)) {
                    seen.add(repo.id);
                    allProjects.push({
                        id: repo.id,
                        name: repo.name,
                        full_name: repo.full_name,
                        description: repo.description,
                        url: repo.html_url,
                        stars: repo.stargazers_count,
                        forks: repo.forks_count,
                        language: repo.language,
                        topics: repo.topics,
                        created_at: repo.created_at,
                        updated_at: repo.updated_at,
                        pushed_at: repo.pushed_at
                    });
                }
            }
        } catch (e) {
            console.error(`Error fetching ${topic}:`, e);
        }
    }

    return allProjects.sort((a, b) => b.stars - a.stars);
}
