from pydantic import BaseModel, Field, RootModel
import uuid
from datetime import datetime
from persist import persist_novel_state


class NSFWCharacter(BaseModel):
    name: str = Field(..., description="角色名")
    description: str = Field(..., description="角色描述")


class NSFWPlot(BaseModel):
    title: str | None = Field(default=None, description="The title of the plot.")
    overview: str | None = Field(default=None, description="A brief overview of the plot.")


class NSFWPlots(BaseModel):
    title: str | None = Field(default=None, description="The title of the NSFW plots.")
    summary: str | None = Field(default=None, description="A summary of the NSFW plots."),
    plots: list[NSFWPlot] = Field(..., description="A list of NSFW plots.")

    class Config:
        json_schema_extra = {
            "example": {
                "summary": "这是一个NSFW情节的总结，包含多个情节设计。",
                "plots": [
                    {
                        "title": "情节标题1",
                        "overview": "情节概述1"
                    },
                    {
                        "title": "情节标题2",
                        "overview": "情节概述2"
                    }
                ]
            }
        }


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
     sections: list[NSFWChapter] = Field(default_factory=list, description="A list of NSFW sections.")
    
class NSFWChapterResponse(BaseModel):
     chapters: list[NSFWChapter] = Field(default_factory=list, description="A list of NSFW chapters.")
 
class NSFWOverallDesign(BaseModel):
    title: str | None = Field(default=None, description="The title of the NSFW novel.")
    overview: str | None = Field(default=None, description="A brief overview of the NSFW novel's plot.")  
    language: str | None = Field(default=None, description="The language of the NSFW novel.")
    characters: list[NSFWCharacter] = Field(default_factory=list, description="A list of main characters, each as an object with name and description.")
    
class NSFWNovel(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique id for the NSFW novel.")
    requirements: str | None = Field(default=None, description="The requirements for the NSFW novel.")
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
    current_state: dict = Field(..., description="The updated state for each character after this section.")