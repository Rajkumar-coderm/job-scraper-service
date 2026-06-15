from pydantic import BaseModel
from typing import List


class HRContact(BaseModel):
    name: str = "N/A"
    email: str = "N/A"
    phone: str = "N/A"


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
    hr_contact: HRContact = HRContact()


class JobSearchResponse(BaseModel):
    success: bool
    keyword: str
    location: str
    date_filter: str
    total_jobs: int
    jobs: List[Job]
