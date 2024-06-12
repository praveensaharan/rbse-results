from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, BackgroundTasks


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
