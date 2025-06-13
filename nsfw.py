import dotenv
import logging

dotenv.load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.callbacks.base import BaseCallbackHandler

from domains import *

# 配置logging
logging.basicConfig(filename="llm_log.txt", level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')

class LLMLoggingCallbackHandler(BaseCallbackHandler):
    def __init__(self, log_file: str):
        self.log_file = log_file  # 保留但不直接用

    def on_llm_start(self, *args, **kwargs):
        logging.info(f"LLM started with args: {args}, kwargs: {kwargs}")

    def on_llm_end(self, *args, **kwargs):
        logging.info(f"LLM ended with args: {args}, kwargs: {kwargs}")

    def on_llm_error(self, *args, **kwargs):
        logging.error(f"LLM error with args: {args}, kwargs: {kwargs}")
    
model = ChatOpenAI(model="google/gemini-2.5-flash-preview-05-20",
    base_url="https://openrouter.ai/api/v1",
    callbacks=[LLMLoggingCallbackHandler("llm_log.txt")],
    model_kwargs={})

json_method = 'json_mode'

class NsfwNovelWriter:
    def __init__(self):
        self.model = model
        self.state = NSFWNovel()

    def design_overall(self, requirements: str):
        """
        生成小说概要（由LLM推断语言或用户指定），并直接生成角色列表。
        """
        prompt = f'''
          You are a professional NSFW novel writer.
          You should determine the language of the NSFW novel make it same as the requirements unless the requirements explicitly specify a language.

          Design an overall plot for a NSFW novel based on the following requirements: {requirements}
          The design should include a title and a brief overview of the plot, both in the determined language.
          Then, based on the title and overview, design a list of main characters for the NSFW novel. For each character, return a single string that contains the name and all other descriptions, merged together.
          You should return a JSON object with the following structure:
          {{
              "title": "The title of the NSFW novel",
              "overview": "A brief overview of the NSFW novel's plot",
              "language": "The language of the NSFW novel",
              "characters": ["角色名：描述...", ...]
          }}
        '''
        llm = self.model.with_structured_output(NSFWOverallDesign, method=json_method)
        result: NSFWOverallDesign = llm.invoke(prompt)
        self.state.requirements = requirements
        self.state.title = result.title
        self.state.overview = result.overview
        self.state.language = result.language
        self.state.characters = result.characters

    def design_chapters(self):
        """
        根据小说的标题、概要、语言、角色生成章节概要(NSFWPlots)，并更新state.chapters。
        """
        prompt = f'''
          You are a professional NSFW novel writer.
          Language: {self.state.language}
          Title: {self.state.title}
          Overview: {self.state.overview}
          Characters: {self.state.characters}
          
          Based on the above information, design a summary and a list of main plots/chapters for the NSFW novel. Each plot should have a title and a brief overview, all in the specified language.
          You should return a JSON object with the following structure without any additional fields:
          ```json
            [
                {{
                    "title": "The title of the chapter 1",
                    "overview": "A brief overview of the chapter1"
                }},
                {{
                    "title": "The title of the chapter 2",
                    "overview": "A brief overview of the chapter2"
                }},
            ]
            ```
        '''
        llm = self.model.with_structured_output(ListModel[NSFWPlot], method=json_method)
        result: ListModel[NSFWPlot] = llm.invoke(prompt)
        # 将返回的plots写入state.chapters
        self.state.chapters = [NSFWChapter(title=plot.title, overview=plot.overview, sections=[]) for plot in result.root]

    def design_sections(self, chapter_index: int):
        """
        根据指定章节概要，生成该章节的sections概要(NSFWPlot)，并更新state.chapters[chapter_index].sections（仅title和overview）。
        """
        if chapter_index < 0 or chapter_index >= len(self.state.chapters):
            raise IndexError("chapter_index out of range")
        chapter = self.state.chapters[chapter_index]
        prompt = f'''
          You are a professional NSFW novel writer.
          Language: {self.state.language}
          Title: {self.state.title}
          Overview: {self.state.overview}
          Chapter Title: {chapter.title}
          Chapter Overview: {chapter.overview}
          Characters: {self.state.characters}
          
          Based on the above information, design a list of sections for this chapter. Each section should have a title and a brief overview, all in the specified language.
          You should return a JSON array of objects, each like:
          {{
              "title": "The title of the section",
              "overview": "A brief description of the section's plot"
          }}
        '''
        llm = self.model.with_structured_output(ListModel[NSFWPlot], method=json_method)
        result = llm.invoke(prompt)
        self.state.chapters[chapter_index].sections = [
            NSFWSection(title=section.title, overview=section.overview, content=None)
            for section in result.root
        ]

    def write_section_content(self, chapter_index: int, section_index: int):
        """
        为指定章节和小节生成正文内容，并写入state.chapters[chapter_index].sections[section_index].content。
        上一小节正文（如有）也会放入prompt。
        """
        chapter = self.state.chapters[chapter_index]
        section = chapter.sections[section_index]
        prev_content = None
        if section_index > 0:
            prev_content = chapter.sections[section_index - 1].content
        prompt = f'''
          You are a professional NSFW novel writer.
          Language: {self.state.language}
          Title: {self.state.title}
          Overview: {self.state.overview}
          Chapter Title: {chapter.title}
          Chapter Overview: {chapter.overview}
          Section Title: {section.title}
          Section Overview: {section.overview}
          Characters: {self.state.characters}
          {'Previous Section Content: ' + prev_content if prev_content else ''}

          Based on the above information, write the full content for this section in the specified language.
          Make the content as erotic, logical, and interesting as possible.
          You should return a string as the content.
        '''
        llm = self.model
        result = llm.invoke(prompt).content
        section.content = result

    def export_markdown(self) -> str:
        """
        导出当前 state 为完整小说的 markdown 文本，结构分明，适合阅读，并自动生成目录。
        并将结果写入 self.state.exported_markdown。
        """
        lines = []
        # 标题
        if self.state.title:
            lines.append(f"# {self.state.title}\n")
        # 概要
        if self.state.overview:
            lines.append(f"**小说概要：**\n{self.state.overview}\n")
        # 目录
        toc = []
        if self.state.characters:
            toc.append(f"- [角色列表](#角色列表)")
        for cidx, chapter in enumerate(self.state.chapters):
            chapter_title = chapter.title or f"章节{cidx+1}"
            anchor = chapter_title.replace(' ', '').replace('#', '')
            toc.append(f"- [{chapter_title}](#{anchor})")
            for sidx, section in enumerate(chapter.sections):
                section_title = section.title or f"小节{sidx+1}"
                section_anchor = section_title.replace(' ', '').replace('#', '')
                toc.append(f"    - [{section_title}](#{section_anchor})")
        if toc:
            lines.append("## 目录\n" + "\n".join(toc) + "\n")
        # 角色
        if self.state.characters:
            lines.append("## 角色列表\n")
            for idx, char in enumerate(self.state.characters):
                lines.append(f"- {char}")
            lines.append("")
        # 章节
        for cidx, chapter in enumerate(self.state.chapters):
            chapter_title = chapter.title or f"章节{cidx+1}"
            lines.append(f"## {chapter_title}\n")
            if chapter.overview:
                lines.append(f"> {chapter.overview}\n")
            # 小节
            for sidx, section in enumerate(chapter.sections):
                section_title = section.title or f"小节{sidx+1}"
                lines.append(f"### {section_title}\n")
                if section.overview:
                    lines.append(f"> {section.overview}\n")
                if section.content:
                    lines.append(section.content.strip() + "\n")
        md = "\n".join(lines)
        self.state.exported_markdown = md
        return md