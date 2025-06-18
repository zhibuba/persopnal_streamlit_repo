import dotenv
import logging

dotenv.load_dotenv()

from langchain_openai import ChatOpenAI
from langchain.globals import set_debug, set_verbose
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from glom import glom

from domains import *
from persist import persist_novel_state

# 配置logging
logging.basicConfig(filename="nsfw.log", level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')

class LLMLoggingCallbackHandler(BaseCallbackHandler): 

    def on_llm_start(self, *args, **kwargs):
        logging.info(f"LLM started with args: {args}, kwargs: {kwargs}")

    def on_llm_end(self, *args, **kwargs):
        logging.info(f"LLM ended with args: {args}, kwargs: {kwargs}")

    def on_llm_error(self, *args, **kwargs):
        logging.error(f"LLM error with args: {args}, kwargs: {kwargs}")
    


json_method = 'json_mode'

set_verbose(True)
set_debug(True)

NSFW_OBJECTIVE = f"""
Your primary goal is to generate content that is as erotic, explicit, and logically coherent as possible, while maintaining narrative quality and following all user requirements.

Always output in valid JSON format as required.
"""

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
    # 可根据需要添加更多模型
]

class NsfwNovelWriter:
    def __init__(self, model_name=MODEL_OPTIONS[0]):
    
        self.set_model(model_name)
        self.state = NSFWNovel()
        
    def set_model(self, model_name: str):
        self.model = ChatOpenAI(
            model=model_name,
            base_url="https://openrouter.ai/api/v1",
            callbacks=[LLMLoggingCallbackHandler()],
            model_kwargs={
                "extra_body": {
                    "safety_settings": [
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    ],
                    "provider": {
                        "order": ["google-vertex"]
                    }       
                },
                
            }
        )

    @persist_novel_state
    def design_overall(self, plot_requirements: str, writing_requirements: str):
        """
        生成小说概要（先推断语言，再生成概要和角色列表）。
        """
        # 1. 先推断语言（直接用llm.invoke）
        inferred_language = self.model.with_retry().invoke([
            SystemMessage(content="""
Infer the most appropriate language for the following NSFW novel requirements. Only return the language name (e.g., Chinese, English, Japanese, etc.), do not explain.
"""),
            HumanMessage(content=f"{plot_requirements}\n{writing_requirements}")
        ]).content

        # 2. 再生成概要和角色列表
        system_message = SystemMessage(content=f"""
You are a professional NSFW novel writer.
{NSFW_OBJECTIVE}
You are responsible for designing the overall plot and main characters for the novel. Focus on creativity, diversity, and logical consistency in the plot and character design.

**Additional Requirements:**
- The `overview` must clearly and logically outline the main storyline from beginning to end, including the key stages, major events, and turning points. Avoid vague or purely atmospheric descriptions.
- The `overview` should be structured and easy to follow, allowing the reader to grasp the full narrative arc at a glance. Use paragraphs or bullet points to clarify the main progression (e.g., beginning, development, climax, resolution).
- The `overview` must reflect the concrete development of the story, not just background or setting.
- Also include a concise list of the novel's design ideas or key creative concepts , summarizing the intended style, themes, and unique features of the novel, in the same language as the overview.

Return your answer in the following JSON format:
```json
{{
  "title": "The title of the NSFW novel",
  "overview": "A clear, structured overview of the NSFW novel's main plot, from start to finish, with key stages and turning points, and a list of design ideas.",
  "language": "The language of the NSFW novel",
  "characters": [{{"name": "the name of the character", "description": "the description and role"}}, ...]
}}
```
""")
        human_message = HumanMessage(content=f"""
Plot Requirements: {plot_requirements}
Writing Requirements: {writing_requirements}
Language: {inferred_language}
Design an overall plot for a NSFW novel based on the requirements above. The design should include a title, a clear and structured overview of the plot (with main storyline and key turning points), and a list of design ideas or key creative concepts. Then, based on the title and overview, design a list of main characters for the NSFW novel. For each character, return an object with name and description fields.
""")
        llm = self.model.with_structured_output(NSFWOverallDesign, method=json_method).with_retry()
        result: NSFWOverallDesign = llm.invoke([
            system_message,
            human_message
        ])
        self.state.plot_requirements = plot_requirements
        self.state.writing_requirements = writing_requirements
        self.state.title = result.title
        self.state.overview = result.overview
        self.state.language = inferred_language
        self.state.characters = result.characters
        # 初始化各角色状态（已删除 current_state）

    @persist_novel_state
    def design_chapters(self, chapter_count=None):
        """
        根据小说的标题、概要、语言、角色生成章概要(NSFWPlots)，并更新state.chapters。
        可指定章数，若为None则自动。
        """
        system_message = SystemMessage(content=f"""
You are a professional NSFW novel writer.
{NSFW_OBJECTIVE}
You are responsible for designing the overall chapter structure and chapter overviews for the novel.

**Requirements:**
- Return a list of chapters, each as an object with `title` and `overview` fields.
- Each chapter overview must focus on the main storyline progression of the entire novel, outlining the key stage, major events, and global turning points for that chapter.
- Emphasize the logical relationship and progression between chapters, ensuring each chapter builds upon the previous and sets up the next.
- Highlight the chapter's role in the overall narrative arc, including any phase climax or major plot twist.
- The main characters should reach sexual climax or significant emotional turning points in each chapter, with a focus on character development and relationship dynamics.
- State the participants and ways of NSFW actions in this chapter clearly if there are nsfw actions in this chapter.
- Avoid vague or fragmented summaries; provide a clear, structured framework for the novel's development.
- Do NOT include chapter numbers or sequence indicators in the chapter titles.

Return your answer in the following JSON format:
```json
{{
  "chapters": [
    {{"title": "The title of the first chapter", "overview": "A brief overview of the chapter1's main plot, nsfw actions and its role in the overall story"}},
    {{"title": "The title of the second chapter", "overview": "A brief overview of the chapter2's main plot, nsfw actions and its role in the overall story"}}
  ]
}}
```
""")
        extra = ""
        if chapter_count:
            extra += f"\nThe novel should have exactly {chapter_count} chapters."
        human_message = HumanMessage(content=f"""
Language: {self.state.language}
Title: {self.state.title}
Overview: {self.state.overview}
Characters: {[{'name': c.name, 'description': c.description} for c in self.state.characters]}
{extra}
Plot Requirements: {self.state.plot_requirements}
Writing Requirements: {self.state.writing_requirements}
Based on the above information, design a summary and a list of main plots/chapters for the NSFW novel. Return a JSON object with a `chapters` field containing the list of chapters, each with a title and overview, all in the specified language.
""")
        llm = self.model.with_structured_output(NSFWChapterResponse, method=json_method).with_retry()
        result: NSFWChapterResponse = llm.invoke([
            system_message,
            human_message
        ])
        self.state.chapters = [NSFWChapter(title=plot.title, overview=plot.overview, sections=glom(self.state.chapters, f'{idx}.sections', default=[]) ) for idx, plot in enumerate(result.chapters)]

    @persist_novel_state
    def design_sections(self, chapter_index: int, section_count: int | None = None, user_feedback: str | None = None):
        """
        根据指定章概要，生成该章的sections概要(NSFWPlot)，并更新state.chapters[chapter_index].sections（仅title和overview）。
        可指定节数，若为None则自动。
        """
        chapter = self.state.chapters[chapter_index]
        system_message = SystemMessage(content=f"""
You are a professional NSFW novel writer.
{NSFW_OBJECTIVE}
You are responsible for designing the section structure and section overviews for the current chapter.

**Requirements:**
- Return a list of sections, each as an object with `title` and `overview` fields, in a JSON object with a `sections` field.
- Each section overview must focus on the concrete plot development within this chapter, including specific events, character conflicts, emotional changes, and minor turning points.
- Ensure each section advances the chapter's main storyline, with a clear beginning, development, climax, and resolution for that section.
- Emphasize how each section serves the chapter's main plot and deepens character relationships or conflicts.
- State the participants and ways of NSFW actions in this section clearly if there are nsfw actions in this section.
- Avoid vague or generic summaries; provide actionable, detailed frameworks for subsequent writing.
- Do NOT include section numbers or sequence indicators in the section titles.

Return your answer in the following JSON format:
```json
{{
  "sections": [
    {{"title": "The title of the first section", "overview": "A brief but complete description of the section's plot, nsfw actions (if exist) and its function in the chapter"}},
    {{"title": "The title of the second section", "overview": "A brief but complete description of the section's plot, nsfw actions (if exist) and its function in the chapter"}}
  ]
}}
```
""")
        extra = ""
        if section_count:
            extra = f"\nThis chapter should have exactly {section_count} sections."
        human_message = HumanMessage(content=f"""
Language: {self.state.language}
Novel Title: {self.state.title}
User Novel-Level Plot Requirements: {self.state.plot_requirements}
User Writing Requirements: {self.state.writing_requirements}
Novel Overview: {self.state.overview}
Chapter Title: {chapter.title}
Chapter Overview: {chapter.overview}
Characters: {[{'name': c.name, 'description': c.description} for c in self.state.characters]}
{extra}


Based on the above information, design a list of sections for this chapter. Each section should have a title and a brief overview, all in the specified language.
""")
        llm = self.model.with_structured_output(NSFWSectionResponse, method=json_method).with_retry()
        messages = [
            system_message,
            human_message
        ]
        if user_feedback:
            # 如果有用户反馈，添加之前的章节小节内容和用户反馈
            messages.append(AIMessage(content=NSFWSectionResponse(
                sections=[NSFWSection(title=s.title, overview=s.overview, content=s.content) for s in chapter.sections]).model_dump_json()))
            messages.append(HumanMessage(content=user_feedback))

        result: NSFWSectionResponse = llm.invoke(messages)
        chapter.sections = [
            NSFWSection(title=section.title, overview=section.overview, content=glom(chapter.sections, f'{idx}.content', default=None))
            for idx, section in enumerate(result.sections)
        ]

    @persist_novel_state
    def write_content(self, chapter_index: int, section_index: int, user_feedback: str | None = None) -> SectionContentResponse:
        """
        Generate the content for the specified chapter and section, and return a SectionContentResponse.
        If this is the first section of the chapter and there is a previous chapter, pass the last section content of the previous chapter as context.
        The prompt uses markdown structure, and all instructions are in English. The current chapter and section overview are included in the final instruction paragraph.
        LLM should return a JSON object: {"content": "...", "current_state": {character_name: {state_info}}}
        """
        chapter = self.state.chapters[chapter_index]
        section = chapter.sections[section_index]
        all_chapter_summaries = self._get_chapter_summaries()
        all_section_summaries = self._get_section_summaries(chapter)
        character_md = self._get_character_md()
        prev_section = self._get_prev_section(chapter_index, section_index)
        prev_content = prev_section.content if prev_section else None
        prev_after_state = prev_section.after_state if prev_section else None
        system_message = SystemMessage(content=f"""
You are a professional NSFW novel writer.
{NSFW_OBJECTIVE}
You are writing the full content for a single section of the novel. You must update the state of each character based on the events in this section, and ensure the writing is immersive and highly erotic while remaining logical.

**Dynamic Guidance:**
- Before writing, analyze the current section’s plot function (setup, conflict, climax, resolution, etc.) and the current state of each character.
- If the section is a buildup, transition, or conflict, focus on emotional, psychological, and relationship development. Keep erotic content and character state changes moderate and gradual.
- If the section is a climax or major turning point, you may intensify erotic content and allow more significant state changes.
- Always ensure the pacing of erotic content and character state progression matches the narrative needs of the current section and the overall story arc.

**Content Formatting Requirements:**
- Write the full content for the current section only (do not include section or chapter titles)
- The content must be clearly and reasonably divided into natural paragraphs, with each paragraph separated by a blank line.
- Do not include any special characters to replace or divide words related to NSFW content.

**Characters State Updating Requirement:**
- In the returned JSON, the `current_state` for each character must include their clothing state, psychological state, and physiological state after the events of this section.
- For the `clothing` field, provide a natural language description, including whether the character is naked, the specific situation of nudity, the types and state of remaining clothes, the position and integrity of clothes, and any dynamic process (e.g., being stripped, clothes torn, etc.).
- For the `psychological` field, provide a description of the character's emotional and mental state, such as embarrassment, excitement, shame, desire, or loss of control.
- For the `physiological` field, provide a description of the character's bodily reactions, such as blushing, rapid breathing, arousal, trembling, or other physical responses.
- For any character who does not appear or is not affected in this section, return their state as it was at the end of the previous section (or the initial state if this is the first section).

Return your answer in the following JSON format:
```json
{{
  "content": "<The full content of this section as a string>",
  "current_state": {{
    "character_name1": {{"clothing": "...", "psychological": "...", "physiological": "..."}},
    "character_name2": {{"clothing": "...", "psychological": "...", "physiological": "..."}}
  }}
}}
```
""")
        human_message = HumanMessage(content=f"""
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
{prev_after_state}

## User Writing Requirements
{self.state.writing_requirements}

{'**Previous Section Content:**\n' + prev_content if prev_content else ''}

---

The language must be {self.state.language}. Make the content as erotic, logical, and interesting as possible.\n\nCurrent chapter overview: {chapter.overview}\nCurrent section overview: {section.overview}\n.
""")
        llm = self.model.with_structured_output(SectionContentResponse, method=json_method).with_retry()
        messages= [
            system_message,
            human_message
        ]
        if user_feedback:
            messages.append(AIMessage(content=SectionContentResponse(
                content=section.content, current_state=section.after_state).model_dump_json()))
            messages.append(HumanMessage(content=user_feedback))
        result: SectionContentResponse = llm.invoke(messages)
        section.content = result.content
        # 存储每节之后的各角色状态
        section.after_state = {k: NSFWCharacterState(**v) if not isinstance(v, NSFWCharacterState) else v for k, v in result.current_state.items()}
        return result

    def _get_prev_section(self, chapter_index, section_index) -> NSFWSection | None:
        """
        获取上一节的section对象（如有），否则返回None。
        """
        if section_index > 0:
            return self.state.chapters[chapter_index].sections[section_index - 1]
        elif chapter_index > 0 and self.state.chapters[chapter_index - 1].sections:
            prev_chapter = self.state.chapters[chapter_index - 1]
            return prev_chapter.sections[-1]
        return None
    
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

    @persist_novel_state
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