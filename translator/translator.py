from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
import os

MODEL_OPTIONS = [
    "google/gemini-2.5-flash-preview-05-20",
    "google/gemini-2.5-pro-preview",
    "google/gemini-2.0-flash-001",
    "x-ai/grok-3-mini-beta",
    "x-ai/grok-3-beta",
    "deepseek/deepseek-chat-v3-0324",
    "deepseek/deepseek-chat-v3-0324:free",
    "deepseek/deepseek-r1-0528",
    "deepseek/deepseek-r1-0528:free",
    "openai/gpt-4.1-mini-2025-04-14"
    # More models can be added as needed
]

LANG_OPTIONS = ["Chinese", "English", "Japanese", "Korean", "French", "German", "Spanish"]

class LLMTranslator:
    def __init__(self, model_name=MODEL_OPTIONS[0], chunk_size=1500):
        self.llm = ChatOpenAI(model_name=model_name, base_url="https://openrouter.ai/api/v1")
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ('system',
                "You are a professional translation assistant. Please translate the user's input into {tgt_lang}, keeping the original tone and formatting. Only return the translated text, without any explanation or additional information."
            ),
            ("human", "{text}")
        ])
        self.chain = self.prompt | self.llm

    def translate(self, text, tgt_lang):
        chunks = self.text_splitter.split_text(text)
        results = []
        for chunk in chunks:
            result = self.chain.invoke({"tgt_lang": tgt_lang, "text": chunk})
            results.append(result.content)
        return "".join(results)

    def stream_translate(self, text, tgt_lang):
        chunks = self.text_splitter.split_text(text)
        for chunk in chunks:
            stream = self.chain.stream({"tgt_lang": tgt_lang, "text": chunk})
            for part in stream:
                yield part.content

# Example usage
# translator = LLMTranslator(api_key="your-openai-key")
# result = translator.translate("Your long text...", tgt_lang="English")
# print(result)
