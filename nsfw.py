import dotenv
import logging

dotenv.load_dotenv()

from langchain_openai import ChatOpenAI
from langchain.globals import set_debug, set_verbose
from langchain_core.callbacks.base import BaseCallbackHandler

from domains import *

# 配置logging
logging.basicConfig(filename="nsfw.log", level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')

class LLMLoggingCallbackHandler(BaseCallbackHandler): 

    def on_llm_start(self, *args, **kwargs):
        logging.info(f"LLM started with args: {args}, kwargs: {kwargs}")

    def on_llm_end(self, *args, **kwargs):
        logging.info(f"LLM ended with args: {args}, kwargs: {kwargs}")

    def on_llm_error(self, *args, **kwargs):
        logging.error(f"LLM error with args: {args}, kwargs: {kwargs}")
    
model = ChatOpenAI(model="google/gemini-2.5-flash-preview-05-20",
    base_url="https://openrouter.ai/api/v1",
    callbacks=[LLMLoggingCallbackHandler()],
    model_kwargs={
        "extra_body": {"safety_settings": [
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        ]
        }
    })

json_method = 'json_mode'

set_verbose(True)
set_debug(True)

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
          Then, based on the title and overview, design a list of main characters for the NSFW novel. For each character, return an object with name and description fields.
          You should return a JSON object with the following structure:
          {{
              "title": "The title of the NSFW novel",
              "overview": "A brief overview of the NSFW novel's plot",
              "language": "The language of the NSFW novel",
              "characters": [{{"name": "角色名", "description": "描述..."}}, ...]
          }}
        '''
        llm = self.model.with_structured_output(NSFWOverallDesign, method=json_method)
        result: NSFWOverallDesign = llm.invoke(prompt)
        self.state.requirements = requirements
        self.state.title = result.title
        self.state.overview = result.overview
        self.state.language = result.language
        self.state.characters = result.characters
        # 初始化各角色状态
        self.state.current_state = {c.name: "(Initial State)" for c in result.characters}

    def design_chapters(self):
        """
        根据小说的标题、概要、语言、角色生成章节概要(NSFWPlots)，并更新state.chapters。
        """
        prompt = f'''
          You are a professional NSFW novel writer.
          Language: {self.state.language}
          Title: {self.state.title}
          Overview: {self.state.overview}
          Characters: {[{"name": c.name, "description": c.description} for c in self.state.characters]}
          
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
          Characters: {[{"name": c.name, "description": c.description} for c in self.state.characters]}
          
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

    def write_section_content(self, chapter_index: int, section_index: int) -> SectionContentResponse:
        """
        Generate the content for the specified chapter and section, and return a SectionContentResponse.
        If this is the first section of the chapter and there is a previous chapter, pass the last section content of the previous chapter as context.
        The prompt uses markdown structure, and all instructions are in English. The current chapter and section overview are included in the final instruction paragraph.
        LLM should return a JSON object: {"content": "...", "current_state": {character_name: {state_info}}}
        """
        chapter = self.state.chapters[chapter_index]
        section = chapter.sections[section_index]
        prev_content = None
        if section_index > 0:
            prev_content = chapter.sections[section_index - 1].content
        elif chapter_index > 0 and self.state.chapters[chapter_index - 1].sections:
            prev_chapter = self.state.chapters[chapter_index - 1]
            prev_content = prev_chapter.sections[-1].content
        all_chapter_summaries = self._get_chapter_summaries()
        all_section_summaries = self._get_section_summaries(chapter)
        character_md = self._get_character_md()
        current_state_str = str(self.state.current_state) if self.state.current_state else '{}'
        prompt = f'''
# NSFW Novel Writing Task

## Book Title
{self.state.title}

## Book Overview
{self.state.overview}

## All Chapter Summaries
{all_chapter_summaries}

## Characters
{character_md}

## All Section Summaries in Current Chapter
{all_section_summaries}

## Current Character States (for incremental update)
{current_state_str}

{'**Previous Section Content:**\n' + prev_content if prev_content else ''}

---

Write the full content for the current section only (do not include section or chapter titles). The language must be {self.state.language}. Make the content as erotic, logical, and interesting as possible.\n\nCurrent chapter overview: {chapter.overview}\nCurrent section overview: {section.overview}\n\nAfter the content, return a JSON object with two fields: content (the section content as a string) and current_state (the updated state for each character, as a dict, incrementally updated based on this section).
'''
        llm = self.model
        result = llm.with_structured_output(SectionContentResponse).invoke(prompt)
        section.content = result.content
        self.state.current_state = result.current_state
        return result

    def _get_chapter_summaries(self):
        return "\n".join([
            f"- **{idx+1}. {c.title or f'Chapter {idx+1}'}**: {c.overview or ''}" for idx, c in enumerate(self.state.chapters)
        ])

    def _get_section_summaries(self, chapter):
        return "\n".join([
            f"    - **{sidx+1}. {s.title or f'Section {sidx+1}'}**: {s.overview or ''}" for sidx, s in enumerate(chapter.sections)
        ])

    def _get_character_md(self):
        return "\n".join([
            f"- **{c.name}**: {c.description}" for c in self.state.characters
        ])

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
            lines.append(self._get_character_md())
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