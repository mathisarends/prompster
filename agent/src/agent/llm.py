from llmify import ChatOpenAI

def create_llm():
    return ChatOpenAI(model="gpt-5.4-mini")