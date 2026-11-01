# Crate
## CS 4300 - Team 7

Crate is an online personal audio storage platform where you can store (copyright-free) media and access it anywhere.

[![Django Tests](https://github.com/CS4300-CS5300-FA26/team-7/actions/workflows/django.yml/badge.svg)](https://github.com/CS4300-CS5300-FA26/team-7/actions/workflows/django.yml)
[![Coverage](https://github.com/CS4300-CS5300-FA26/team-7/actions/workflows/coverage.yml/badge.svg)](https://github.com/CS4300-CS5300-FA26/team-7/actions/workflows/coverage.yml)
[![Behave Tests](https://github.com/CS4300-CS5300-FA26/team-7/actions/workflows/behave-tests.yml/badge.svg)](https://github.com/CS4300-CS5300-FA26/team-7/actions/workflows/behave-tests.yml)


## AI Usage

- Sprint 0-2: Claude - Helped decompose user stories and write Gherkin scenarios; we edited them to match our app and customer requirements.
- Sprint 0-2: Pardot - Reviewed our doc against the Sprint 0-2 requirements; we used the feedback to revise it.
- Sprint 0-2: Pardot - Wrote the "AI Usage" section of the README file.

- Sprint 0-3: Claude - Assisted with Deployment setup and Configuration.

- Sprint 1: Claude - Assisted with playlist model, views, and html page
- Sprint 1: Claude - Assisted with automatic metadata pulling on the song upload page and tests thereof
- Sprint 1: Claude - Helped assign songs to individual users
- Sprint 1: Claude - Helped with Cloudinary Wiring, and Testing.
- Sprint 1: Claude - Helped with Behave Tests.

- Sprint 2: Claude - Assisted with diagnosing playback issues and tests for the audio player

## Dev Guide To Run The App

- Make sure you are in the team-7 Directory
- Create and activate your virtual environment
- Run "pip install -r requirements.txt"
- Run $env:DJANGO_DEBUG="True"  or export DJANGO_DEBUG=True if on linux
- Run "python manage.py makemigrations"
- Run "python manage.py migrate"
- Run "python manage.py runserver"
- Click on link produced by runserver command

## [Deployed Webapp link](https://crate-app-c51a747af77b.herokuapp.com/)
