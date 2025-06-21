from pydantic import BaseModel, Field, RootModel
from typing import TypedDict, Annotated
import uuid

class NSFWCharacter(BaseModel):
    name: str = Field(..., description="角色名")
    description: str = Field(..., description="角色描述")


class NSFWPlot(BaseModel):
    title: str | None = Field(default=None, description="The title of the plot.")
    overview: str | None = Field(default=None, description="A brief overview of the plot.")


class NSFWCharacterState(BaseModel):
    clothing: str = Field(..., description="The clothing state of the character after this section.")
    psychological: str = Field(..., description="The psychological state of the character after this section.")
    physiological: str = Field(..., description="The physiological state of the character after this section.")


class NSFWSection(BaseModel):
    title: str | None = Field(default=None, description="The title of the NSFW section.")
    overview: str | None = Field(default=None, description="A brief description of the NSFW section's plot.")
    content: str | None = Field(default=None, description="The content of the NSFW section.")
    after_state: dict[str, NSFWCharacterState] = Field(default_factory=dict, description="The state for each character after this section. Format: {character_name: NSFWCharacterState}.")
    
class NSFWChapter(BaseModel):
    title: str | None = Field(default=None, description="The title of the NSFW chapter.")
    overview: str | None = Field(default=None, description="A brief overview of the NSFW chapter.")
    sections: list[NSFWSection] = Field(default_factory=list, description="A list of NSFW sections in the chapter.")
    
    
class NSFWSectionResponse(BaseModel):
     sections: list[NSFWPlot] = Field(default_factory=list, description="A list of NSFW sections.")
    
class NSFWChapterResponse(BaseModel):
     chapters: list[NSFWPlot] = Field(default_factory=list, description="A list of NSFW chapters.")
 
class NSFWOverallDesign(BaseModel):
    title: str | None = Field(default=None, description="The title of the NSFW novel.")
    overview: str | None = Field(default=None, description="A brief overview of the NSFW novel's plot.")  
    characters: list[NSFWCharacter] = Field(default_factory=list, description="A list of main characters, each as an object with name and description.")
    
class NSFWNovel(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique id for the NSFW novel.")
    plot_requirements: str | None = Field(default=None, description="The plot requirements for the NSFW novel.")
    writing_requirements: str | None = Field(default=None, description="The writing requirements for the NSFW novel.")
    title: str | None = Field(default=None, description="The title of the NSFW novel.")
    overview: str | None = Field(default=None, description="A brief overview of the NSFW novel's plot.")
    language: str | None = Field(default=None, description="The language of the NSFW novel.")
    characters: list[NSFWCharacter] = Field(default_factory=list, description="A list of NSFW characters in the novel.")
    chapters: list[NSFWChapter] = Field(default_factory=list, description="A list of NSFW chapters in the novel.")
    exported_markdown: str | None = Field(default=None, description="The exported markdown of the novel.")

class ListModel[T](RootModel[T]):
    root: list[T]


    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self):
        return len(self.root)

class SectionContentResponse(BaseModel):
    content: str = Field(..., description="The generated content for the section.")
    current_state: dict[str, NSFWCharacterState] = Field(..., description="The updated state for each character after this section.")
    
class SectionContentDict(TypedDict):
    content: Annotated[str, ..., Field(description="The generated content for the section.")]
    current_state: Annotated[dict[str, dict], ..., Field(description="The updated state for each character after this section.")]

# 兼容旧NSFWNovel JSON数据，递归删除sections下的current_state字段（直接循环实现）
def clean_legacy_nsfw_novel_json(data: dict) -> dict:
    """
    兼容旧数据，递归删除 chapters[*].sections[*].current_state 字段
    """
    chapters = data.get("chapters", [])
    for chapter in chapters:
        sections = chapter.get("sections", [])
        for section in sections:
            if "after_state" in section:
                section.pop("after_state")
    return data