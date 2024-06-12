# FastAPI Student Results API

This project is a FastAPI-based web service for searching and retrieving student results based on their names and roll numbers. It includes functionality for extracting and processing data from a given URL and storing results temporarily in Redis.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Endpoints](#endpoints)
- [Environment Variables](#environment-variables)
- [License](#license)

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/praveensaharan/rbse-results.git
   cd rbse-results
   ```

2. **Create a virtual environment and activate it**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the required dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:

   Create a `.env` file in the project root directory and add the following environment variable:

   ```plaintext
   REDIS_URL=redis://localhost:6379/0
   ```

5. **Run the application**:

   ```bash
   uvicorn main:app --reload
   ```

## Usage

After starting the FastAPI server, you can access the API documentation at `http://127.0.0.1:8000/docs`.

## Project Structure

- **main.py**: The entry point of the application.
- **models.py**: Contains Pydantic models.
- **utils.py**: Contains utility functions for parsing HTML and extracting data.
- **redis_utils.py**: Contains utility functions for interacting with Redis.
- **results_utils.py**: Contains functions for handling result retrieval.
- **routers/search.py**: Contains the search-related endpoints.

## Endpoints

### POST /search

Initiates a background task to search for student results based on the provided name and URL.

- **Request Body**:

  ```json
  {
    "name": "student_name",
    "url": "results_page_url"
  }
  ```

- **Response**:
  ```json
  {
    "message": "Processing started",
    "uuid": "unique_identifier"
  }
  ```

### GET /results/{uuid_str}

Retrieves the results of the search task associated with the given UUID.

- **Response**:
  ```json
  {
      "results": [...]
  }
  ```

### GET /result

Retrieves the HTML content for the student's results based on the provided roll number and class.

- **Query Parameters**:

  - `rollno`: The roll number of the student.
  - `student_class`: The class of the student (e.g., `10th`, `12th-science`, `12th-arts`, `12th-commerce`).

- **Response**:
  ```json
  {
    "html_content": "..."
  }
  ```

## Environment Variables

- **REDIS_URL**: The URL for the Redis instance.

## License

This project is licensed under the MIT License.
