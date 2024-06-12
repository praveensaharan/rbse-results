import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException
import json
from utils import extract_roll_numbers_and_details, parse_results_page


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
        roll_numbers, names, fathernames = await extract_roll_numbers_and_details(
            first_table)
        results.extend(zip(roll_numbers, names, fathernames))

    result_soup = BeautifulSoup(response.content, 'html.parser')
    viewstate = result_soup.find('input', {'id': '__VIEWSTATE'})['value']
    viewstate_generator = result_soup.find(
        'input', {'id': '__VIEWSTATEGENERATOR'})['value']
    name_value = name

    previous_content = response.content
    page_number = 2

    while True:
        response = await navigate_to_page(
            session, url, name_value, viewstate, viewstate_generator, page_number)
        if response.content == previous_content:
            break
        previous_content = response.content
        next_table = await parse_results_page(response.content)
        if next_table:
            roll_numbers, names, fathernames = await extract_roll_numbers_and_details(
                next_table)
            results.extend(zip(roll_numbers, names, fathernames))
        page_number += 1

    results_json = [{"roll_number": roll, "name": name,
                     "father_name": fname} for roll, name, fname in results]
    return results_json


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
