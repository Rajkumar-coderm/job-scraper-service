from pydantic import BaseModel
from typing import List


class Job(BaseModel):
    title: str
    company: str
    location: str
    salary: str
    experience: str
    skills: List[str]
    posted: str
    source: str
    job_link: str