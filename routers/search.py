from fastapi import APIRouter, HTTPException, BackgroundTasks
from models import SearchRequest
from redis_utils import save_results_to_redis, get_results_from_redis
from results_utils import search_results_by_name, extract_student_info, get_result1, get_result2
import uuid

router = APIRouter()


@router.post("/search")
async def search(search_request: SearchRequest, background_tasks: BackgroundTasks):
    uuid_str = str(uuid.uuid4())
    background_tasks.add_task(
        search_results_by_name_and_save, search_request.name, search_request.url, uuid_str)
    return {"message": "Processing started", "uuid": uuid_str}


@router.get("/results/{uuid_str}")
async def get_results(uuid_str: str):
    result = await get_results_from_redis(uuid_str)
    return result


async def search_results_by_name_and_save(name, url, uuid_str):
    results = await search_results_by_name(name, url)
    if results:
        await save_results_to_redis(results, uuid_str)


@router.get("/result")
async def get_result_html(rollno: str, student_class: str):
    urls = {
        '10th': 'https://rajasthan-10th-result.indiaresults.com/rj/bser/class-10-result-2024/result.asp',
        '12th-science': 'https://rj-12-science-result.indiaresults.com/rj/bser/class-12-science-result-2024/result.asp',
        '12th-arts': 'https://rj-12-arts-result.indiaresults.com/rj/bser/class-12-arts-result-2024/result.asp',
        '12th-commerce': 'https://rj-12-commerce-result.indiaresults.com/rj/bser/class-12-commerce-result-2024/result.asp'
    }

    if student_class not in urls:
        raise HTTPException(status_code=400, detail="Invalid class provided")

    url = urls[student_class]

    if student_class == '10th':
        html_content = await get_result1(url, rollno)
        resu = await extract_student_info(html_content)
        return {"html_content": resu}
    else:
        student_info = await get_result2(url, rollno)
        return {"html_content": student_info}
