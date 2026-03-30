from langchain.tools import tool
from dotenv import load_dotenv
import os
import httpx

load_dotenv()
api_key = os.getenv("BOCHA_API_KEY")


@tool
def search(query: str) -> str:
    """
    针对博查(Bocha) API 返回结构封装的搜索工具
    """
    print(f"🌐 [web_search] 开始搜索: {query}")
    url = "https://api.bocha.cn/v1/web-search"  # 确认是 ai-search 还是 search 接口
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"query": query, "count": 5}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            json_data = response.json()

    except Exception as e:
        return f"搜索调用失败: {str(e)}"

    # --- 核心解析逻辑 ---
    # 根据你提供的 JSON 路径进行提取
    results = []
    try:
        # 路径: data -> webPages -> value
        web_pages = json_data.get("data", {}).get("webPages", {}).get("value", [])

        for page in web_pages:
            title = page.get("name", "无标题")
            link = page.get("url", "无链接")
            snippet = page.get("snippet", "无内容描述")
            site_name = page.get("siteName", "")

            content = f"标题: {title} ({site_name})\n链接: {link}\n摘要: {snippet}\n"
            results.append(content)

    except KeyError:
        return "解析搜索结果时出错，返回结构可能已变化。"

    return "\n---\n".join(results) if results else "未找到相关搜索结果。"
