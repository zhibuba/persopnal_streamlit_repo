from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain.globals import set_debug, set_verbose
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator, Optional, Callable
from threading import Thread

MODEL_OPTIONS = [
    "deepseek/deepseek-chat-v3-0324",
    "deepseek/deepseek-chat-v3-0324:free",
    "deepseek/deepseek-r1-0528",
    "deepseek/deepseek-r1-0528:free",
    "google/gemini-2.5-flash-preview-05-20",
    "google/gemini-2.5-pro-preview",
    "google/gemini-2.0-flash-001",
    "x-ai/grok-3-mini-beta",
    "x-ai/grok-3-beta",
    "openai/gpt-4.1-mini-2025-04-14"
    # More models can be added as needed
]

LANG_OPTIONS = ["Chinese (Simp.)", "English", "Japanese", "Korean", "French", "German", "Spanish"]

set_debug(True)
set_verbose(True)

class LLMTranslator:
    def __init__(self, model_name: str = MODEL_OPTIONS[0], chunk_size: int = 1500) -> None:
        self.llm: ChatOpenAI = ChatOpenAI(model_name=model_name, base_url="https://openrouter.ai/api/v1")
        self.text_splitter: RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=0)
        self.prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
            ('system',
                "You are a professional translation assistant. Please translate the user's input into {tgt_lang}, keeping the original tone and formatting. Only return the translated text, without any explanation or additional information."
            ),
            ("human", "{text}")
        ])
        self.chain = self.prompt | self.llm

    def translate_parallel(
        self, 
        text: str, 
        tgt_lang: str, 
        max_workers: int = 6, 
        worker_thread_initializer: Optional[Callable[[Thread], None]] = None,
        progress_callback: Optional[Callable[[int, int, list[Optional[str]]], None]] = None
    ) -> str:
        chunks: list[str] = self.text_splitter.split_text(text)
        results: list[Optional[str]] = [None] * len(chunks)
        def translate_chunk(i: int, chunk: str) -> None:
            result = self.chain.invoke({"tgt_lang": tgt_lang, "text": chunk})
            results[i] = result.content
            if progress_callback:
                progress_callback(i + 1, len(chunks), results)
        with ThreadPoolExecutor(max_workers=max_workers, initargs=worker_thread_initializer) as executor:
            futures = [executor.submit(translate_chunk, i, chunk) for i, chunk in enumerate(chunks)]
            if worker_thread_initializer:
                for thread in executor._threads:
                    worker_thread_initializer(thread)
        for future in as_completed(futures):
            try:
                future.result()  # Ensure any exceptions are raised
            except Exception as e:
                print(f"Error translating chunk: {e}")
        return "".join(results)  # type: ignore

    def translate_stream(
        self, 
        text: str, 
        tgt_lang: str, 
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Generator[str, None, None]:
        chunks: list[str] = self.text_splitter.split_text(text)
        total_chunks = len(chunks)
        for idx, chunk in enumerate(chunks):
            stream = self.chain.stream({"tgt_lang": tgt_lang, "text": chunk})
            chunk_result = ""
            for part in stream:
                chunk_result += part.content
                yield part.content
            if progress_callback:
                progress_callback(idx + 1, total_chunks, chunk_result)
