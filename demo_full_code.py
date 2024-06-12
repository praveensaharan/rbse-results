from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import json
import uuid
from redis import Redis
from dotenv import load_dotenv
import os
from typing import Dict

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_url = os.getenv("REDIS_URL")
redis = Redis.from_url(redis_url)


class SearchRequest(BaseModel):
    name: str
    url: str


async def extract_roll_numbers_and_details(table):
    roll_numbers = []
    names = []
    fathernames = []
    for row in table.find_all('tr', {'align': 'left'})[1:]:
        cells = row.find_all('td')
        roll_no = cells[2].text.strip() if len(cells) > 2 else ""
        name = cells[1].text.strip() if len(cells) > 1 else ""
        fathername = cells[3].text.strip() if len(cells) > 3 else ""

        roll_numbers.append(roll_no)
        names.append(name)
        fathernames.append(fathername)

    return roll_numbers, names, fathernames


async def save_results_to_redis(results, uuid_str):
    # Store in Redis for 10 minutes
    redis.setex(uuid_str, 600, json.dumps(results))


async def get_form_data_and_post(session, url, name):
    response = session.get(f"{url}query.htm")
    soup = BeautifulSoup(response.content, 'html.parser')
    form = soup.find('form', attrs={'name': 'FrontPage_Form2'})
    input_element = form.find('input', attrs={'name': 'name'})
    input_element['value'] = name
    name_value = input_element['value']

    if len(name_value) < 3:
        raise HTTPException(
            status_code=400, detail="Please enter at least 3 characters in the name field.")
    elif len(name_value) > 50:
        raise HTTPException(
            status_code=400, detail="Please enter at most 50 characters in the name field.")

    response = session.post(f"{url}name-results.aspx", data={
        input_element['name']: name_value
    })

    return response


async def parse_results_page(response_content):
    soup = BeautifulSoup(response_content, 'html.parser')
    midd_part_div = soup.find('div', id='midd_part')
    if midd_part_div:
        midd_contDiv_div = midd_part_div.find('div', id='midd_contDiv')
        if midd_contDiv_div:
            tables = midd_contDiv_div.find_all('table')
            if tables:
                return tables[0]
            else:
                raise HTTPException(
                    status_code=404, detail="No tables found inside midd_contDiv.")
        else:
            raise HTTPException(
                status_code=404, detail="midd_contDiv div not found.")
    else:
        raise HTTPException(status_code=404, detail="midd_part div not found.")
    return None


async def navigate_to_page(session, url, name_value, viewstate, viewstate_generator, page_number):
    page_event_target = 'GridView1'
    page_event_argument = f'Page${page_number}'

    post_data = {
        '__EVENTTARGET': page_event_target,
        '__EVENTARGUMENT': page_event_argument,
        '__VIEWSTATE': viewstate,
        '__VIEWSTATEGENERATOR': viewstate_generator,
        'name': name_value
    }

    response = session.post(f"{url}name-results.aspx", data=post_data)
    return response


async def search_results_by_name(name, url):
    session = requests.Session()

    response = await get_form_data_and_post(session, url, name)
    if response is None:
        return []

    results = []

    first_table = await parse_results_page(response.content)

    error_msg = first_table.find(
        'span', {'id': 'lblErrorMsg'}) if first_table else None

    if error_msg and "No Record Found" in error_msg.text:
        return []

    if first_table:
        roll_numbers, names, fathernames = await extract_roll_numbers_and_details(first_table)
        results.extend(zip(roll_numbers, names, fathernames))

    result_soup = BeautifulSoup(response.content, 'html.parser')
    viewstate = result_soup.find('input', {'id': '__VIEWSTATE'})['value']
    viewstate_generator = result_soup.find(
        'input', {'id': '__VIEWSTATEGENERATOR'})['value']
    name_value = name

    previous_content = response.content
    page_number = 2

    while True:
        response = await navigate_to_page(session, url, name_value, viewstate, viewstate_generator, page_number)
        if response.content == previous_content:
            break
        previous_content = response.content
        next_table = await parse_results_page(response.content)
        if next_table:
            roll_numbers, names, fathernames = await extract_roll_numbers_and_details(next_table)
            results.extend(zip(roll_numbers, names, fathernames))
        page_number += 1

    results_json = [{"roll_number": roll, "name": name,
                     "father_name": fname} for roll, name, fname in results]
    return results_json


async def search_results_by_name_and_save(name, url, uuid_str):
    results = await search_results_by_name(name, url)
    if results:
        await save_results_to_redis(results, uuid_str)


async def get_result1(url, rollno):
    data = {'Rollno': rollno}
    response = requests.post(url, data=data)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        div3 = soup.find('div', attrs={'id': 'wrapper_rj'})

        div1_in_div3 = div3.find('div', attrs={'id': 'content_DIV'})
        table = div1_in_div3.find('table')

        tbody = table.find('tr')
        td = tbody.find_all('td')[1]

        div = td.find_all('div', attrs={'align': 'left'})

        return str(div)


async def get_result2(url, rollno):
    data = {'Rollno': rollno}
    response = requests.post(url, data=data)
    soup = BeautifulSoup(response.text, 'html.parser')
    div3 = soup.find('div', attrs={'id': 'wrapper_rj'})
    soups = div3.find('table', attrs={'id': 'table97'})
    personal_table = BeautifulSoup(str(soups), 'lxml')
    personal_details = {}

    if personal_table:
        rows = personal_table.find_all('tr')

        roll_row = rows[1]
        name_row = rows[2]
        father_row = rows[3]
        mother_row = rows[4]
        school_row = rows[5]
        subjects_row = rows[10:16]
        total_marks_row = rows[-4]
        percentage_row = rows[-3]

        personal_details['roll_number'] = roll_row.find_all('td')[
            1].get_text(strip=True)
        personal_details['name'] = name_row.find_all(
            'td')[1].get_text(strip=True)
        personal_details['father_name'] = father_row.find_all('td')[
            1].get_text(strip=True)
        personal_details['mother_name'] = mother_row.find_all('td')[
            1].get_text(strip=True)
        personal_details['school'] = school_row.find_all(
            'td')[1].get_text(strip=True)
        personal_details['total_marks'] = total_marks_row.find_all('td')[
            1].get_text(strip=True)
        personal_details['percentage'] = percentage_row.find_all('td')[
            1].get_text(strip=True)

        subject_marks = []
        for row in subjects_row:
            cells = row.find_all('td')
            if len(cells) >= 6:
                subject = cells[0].get_text(strip=True)
                marks = cells[5].get_text(strip=True)
                subject_marks.append({"subject": subject, "marks": marks})

        personal_details['subject_marks'] = subject_marks

        return personal_details


async def extract_student_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    personal_details = {}
    personal_table = soup.find('table', attrs={'bordercolor': '#DDDDDD'})
    if personal_table:
        rows = personal_table.find_all('tr')
        roll_row = rows[1]
        name_row = rows[2]
        father_row = rows[3]
        mother_row = rows[4]
        school_row = rows[5]
        subjects_row = rows[10:16]
        percentage_row = rows[-3]
        total_marks_row = rows[-4]

        personal_details['roll_number'] = roll_row.find_all('td')[
            1].get_text(strip=True)
        personal_details['name'] = name_row.find_all(
            'td')[1].get_text(strip=True)
        personal_details['father_name'] = father_row.find_all('td')[
            1].get_text(strip=True)
        personal_details['mother_name'] = mother_row.find_all('td')[
            1].get_text(strip=True)
        personal_details['school'] = school_row.find_all(
            'td')[1].get_text(strip=True)
        personal_details['percentage'] = percentage_row.find_all('td')[
            1].get_text(strip=True)
        personal_details['total_marks'] = total_marks_row.find_all('td')[
            1].get_text(strip=True)

        subject_marks = []
        for row in subjects_row:
            cells = row.find_all('td')
            if len(cells) >= 6:
                subject = cells[0].text.strip()
                marks = cells[5].text.strip()
                subject_marks.append({"subject": subject, "marks": marks})

        personal_details['subject_marks'] = subject_marks

        return json.dumps(personal_details, indent=4)


@app.post("/search")
async def search(search_request: SearchRequest, background_tasks: BackgroundTasks):
    uuid_str = str(uuid.uuid4())
    background_tasks.add_task(
        search_results_by_name_and_save, search_request.name, search_request.url, uuid_str)
    return {"message": "Processing started", "uuid": uuid_str}


@app.get("/results/{uuid_str}")
async def get_results(uuid_str: str):
    result = redis.get(uuid_str)
    if result is None:
        raise HTTPException(
            status_code=404, detail="Results not found or expired")
    return json.loads(result)


@app.get("/")
async def read_root():
    return {"message": "Welcome to the API"}


@app.get("/result")
async def get_result_html(rollno: str, student_class: str):
    urls: Dict[str, str] = {
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
