from pydantic import BaseModel, Field, RootModel


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


class NSFWSection(BaseModel):
    title: str | None = Field(default=None, description="The title of the NSFW section.")
    overview: str | None = Field(default=None, description="A brief description of the NSFW section's plot.")
    content: str | None = Field(default=None, description="The content of the NSFW section.")
    
class NSFWChapter(BaseModel):
    title: str | None = Field(default=None, description="The title of the NSFW chapter.")
    overview: str | None = Field(default=None, description="A brief overview of the NSFW chapter.")
    sections: list[NSFWSection] = Field(default_factory=list, description="A list of NSFW sections in the chapter.")
 
class NSFWOverallDesign(BaseModel):
    title: str | None = Field(default=None, description="The title of the NSFW novel.")
    overview: str | None = Field(default=None, description="A brief overview of the NSFW novel's plot.")  
    language: str | None = Field(default=None, description="The language of the NSFW novel.")
    
class NSFWNovel(BaseModel):
    requirements: str | None = Field(default=None, description="The requirements for the NSFW novel.")
    title: str | None = Field(default=None, description="The title of the NSFW novel.")
    overview: str | None = Field(default=None, description="A brief overview of the NSFW novel's plot.")
    language: str | None = Field(default=None, description="The language of the NSFW novel.")
    characters: list[str] = Field(default_factory=list, description="A list of NSFW characters in the novel.")
    chapters: list[NSFWChapter] = Field(default_factory=list, description="A list of NSFW chapters in the novel.")


class ListModel[T](RootModel[T]):
    root: list[T]


    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self):
        return len(self.root)