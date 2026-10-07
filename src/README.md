# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher-only sign-up and unregister actions
- Public view of activity rosters
- Teacher login with credentials stored as password hashes in a local JSON file

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Run the application:

   ```
   python -m uvicorn src.app:app --reload
   ```

   To run the test suite, install the development dependencies and run:

   ```sh
   pip install -r requirements-dev.txt
   python -m unittest discover -s tests -v
   ```

3. Open your browser and go to:
   - Website: http://localhost:8000/
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                     | Log in as a teacher                                                 |
| GET    | `/auth/me`                                                        | Get the current teacher session                                     |
| POST   | `/auth/logout`                                                    | End the current teacher session                                     |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher registers a student for an activity                         |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher unregisters a student                                       |

## Teacher access

Copy `src/teachers.example.json` to `src/teachers.json`, then add assigned teacher accounts from the repository root:

```sh
cp src/teachers.example.json src/teachers.json
python -m src.auth teacher-username
```

The command prompts for the password twice and writes only a salted PBKDF2 hash to the JSON file. `src/teachers.json` is git-ignored. To use a different path, set `TEACHER_CREDENTIALS_FILE` before starting the API. The login file is local configuration; do not commit it or expose its contents. Teacher sessions expire after eight hours and are invalidated when the server restarts.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and participant data is stored in memory, which means it will be reset when the server restarts. Teacher credentials are stored separately in the local JSON file described above.
