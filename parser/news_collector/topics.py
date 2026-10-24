"""Transparent multilingual hints, not a trained semantic classifier."""
import re

TERMS = {
    "ai": r"\b(?:AI|LLM|GPT\w*|OpenAI|Anthropic|DeepSeek|ChatGPT|Nvidia|machine learning|artificial intelligence)\b|искусственн\w* интеллект|нейросет\w*|машинн\w* обучен|人工智能|大模型",
    "business": r"\b(?:business|compan\w*|revenue|profit\w*|acquisition\w*|merger\w*|startup\w*|funding|IPO|earnings)\b|бизнес\w*|компани\w*|выручк\w*|прибыл\w*|стартап\w*|сделк\w*|企业|公司",
    "economy": r"\b(?:econom\w*|inflation|GDP|tariff\w*|trade|interest rates|unemployment|central bank)\b|эконом\w*|инфляц\w*|ВВП|ключев\w* ставк|безработиц\w*|пошлин\w*|经济|贸易",
    "finance": r"\b(?:bank\w*|stock\w*|bond\w*|invest\w*|market\w*|currency|credit|fintech)\b|банк\w*|финанс\w*|инвест\w*|акци[яийю]\w*|облигац\w*|кредит\w*|金融|投资",
    "technology": r"\b(?:tech\w*|software|chip\w*|semiconductor\w*|cloud|data cent\w*|cyber\w*|robot\w*)\b|технолог\w*|процессор\w*|микросхем\w*|кибер\w*|робот\w*|дата-?центр\w*|科技|芯片",
    "energy": r"\b(?:energy|oil|gas|renewable\w*|electricity)\b|нефт\w*|энерг\w*|газ[а-я]*|электр\w*|能源",
}
PATTERNS = {key: re.compile(value, re.I) for key, value in TERMS.items()}


def classify(title, description, text):
    lead = title + " " + (description or "")
    body = text[:12000]
    scores = {key: min(10, len(pattern.findall(lead)) * 3 + len(pattern.findall(body)))
              for key, pattern in PATTERNS.items()}
    return [key for key, score in scores.items() if score], min(100, sum(scores.values()) * 2)
