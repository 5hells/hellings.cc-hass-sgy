"""Integration tests for Schoology API - makes real API requests with standalone client logic."""

import asyncio
import os
import datetime

import pytest
import aiohttp
import async_timeout
import bs4 as bs
import pytz
from dotenv import load_dotenv

load_dotenv()


def notnone(value):
    """Helper to assert that a value is not None."""
    if value is None:
        raise ValueError("Expected value to be not None")
    return value


@pytest.fixture
def session(event_loop):
    """Create an aiohttp session with threading resolver (not aiodns)."""
    from aiohttp import ThreadedResolver

    resolver = ThreadedResolver(loop=event_loop)
    connector = aiohttp.TCPConnector(resolver=resolver, loop=event_loop)
    sess = aiohttp.ClientSession(connector=connector, loop=event_loop)
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
    })
    yield sess
    event_loop.run_until_complete(sess.close())


@pytest.fixture
def credentials():
    """Get credentials from environment."""
    username = os.getenv("SGY_USERNAME")
    password = os.getenv("SGY_PASSWORD")
    api_base = os.getenv("API_BASE", "holyghostprep.schoology.com")

    if not username or not password:
        pytest.skip("USERNAME and PASSWORD environment variables required")

    return {"username": username, "password": password, "api_base": api_base}


async def schoology_login(
    session: aiohttp.ClientSession, username: str, password: str, api_base: str
) -> dict:
    """Login to Schoology and return cookies."""
    async with async_timeout.timeout(10):
        base_resp = await session.get(f"https://{api_base}/", allow_redirects=True)
        base_resp.raise_for_status()
        login_url = str(base_resp.url)

    print(f"Login URL: {login_url}")

    async with async_timeout.timeout(10):
        response = await session.get(login_url)
        response.raise_for_status()
        login_page = await response.text()

    form = bs.BeautifulSoup(login_page, features="html.parser")
    form_elem = form.find(id="s-user-login-form")
    if not form_elem:
        raise ValueError(f"Login form not found. Page: {login_page[:500]}...")

    form_action = form_elem.get("action") or login_url
    if not form_action.startswith("http"):
        if form_action.startswith("/"):
            form_action = f"https://{api_base}{form_action}"
        else:
            form_action = f"{login_url}/{form_action}"

    post_data = {
        "mail": username,
        "pass": password,
    }

    for input_tag in form_elem.find_all("input"):
        input_name = input_tag.get("name")
        if input_name and input_name not in ["mail", "pass"]:
            post_data[input_name] = input_tag.get("value", "")

    print(f"Posting to: {form_action}")

    async with async_timeout.timeout(10):
        response = await session.post(
            form_action,
            data=post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=True,
        )
        response.raise_for_status()
        body = await response.text()

    print(f"After login, final URL: {response.url}")
    print(f"Response status: {response.status}")
    print(f"Cookies in jar: {len(list(session.cookie_jar))}")

    if "Invalid username or password" in body or "login" in str(response.url).lower():
        if "invalid" in body.lower():
            raise ValueError("Invalid credentials")
        else:
            raise ValueError("Login failed - still on login page")

    cookies = {}
    for cookie in session.cookie_jar:
        cookies[cookie.key] = cookie.value

    return cookies


async def get_announcements(
    session: aiohttp.ClientSession, api_base: str, cookies: dict
) -> list:
    """Get announcements from Schoology."""
    async with async_timeout.timeout(10):
        response = await session.get(
            f"https://{api_base}/home/feed?page=0",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            },
        )
        response.raise_for_status()
    
        data = await response.json()


    html = data.get("output", "")
    soup = bs.BeautifulSoup(html, features="html.parser")
    announcements = []

    for announcement in soup.select("ul.s-edge-feed li"):
        pfp = announcement.select_one(".profile-picture a img")
        title_elem = announcement.select_one(".long-username a")
        created = announcement.select_one(".created .small.gray")
        group_to = announcement.select_one("a[href^='/group/']")
        date_elem = created
        likes = (
            int(
                notnone(announcement.select_one(".s-like-sentence a"))
                .get_text(strip=True)
                .split()[0]
            )
            if announcement.select_one(".s-like-sentence a")
            else 0
        )

        comments = []
        for comment in announcement.select(
            "#s_comments .s_comments_level .discussion-card"
        ):
            author_elem = comment.select_one(".comment-author a")
            content_elem = comment.select_one(".comment-body-wrapper")
            comment_likes = (
                int(
                    notnone(comment.select_one(".s-like-comment-icon")).get_text(
                        strip=True
                    )
                )
                if comment.select_one(".s-like-comment-icon")
                else 0
            )

            if author_elem and content_elem:
                comments.append(
                    {
                        "author": author_elem.get_text(strip=True),
                        "content": content_elem.get_text(strip=True),
                        "likes": comment_likes,
                    }
                )

        if title_elem and date_elem:
            announcements.append(
                {
                    "title": title_elem.get_text(strip=True),
                    "date": date_elem.get_text(strip=True),
                    "profile_picture": pfp["src"] if pfp else None,
                    "group": group_to.get_text(strip=True) if group_to else None,
                    "created": created.get_text(strip=True) if created else None,
                    "likes": likes,
                    "comments": comments,
                }
            )

    return announcements


async def get_upcoming_events(
    session: aiohttp.ClientSession, api_base: str, cookies: dict
) -> list:
    """Get upcoming events from Schoology."""
    async with async_timeout.timeout(10):
        response = await session.get(
            f"https://{api_base}/home/upcoming_ajax",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            },
        )
        response.raise_for_status()
        data = await response.json()

    html = data.get("html", "")
    soup = bs.BeautifulSoup(html, features="html.parser")
    events = []
    current_date = ""

    upcoming_list = soup.find(class_="upcoming-list")
    if not upcoming_list:
        return []

    for element in upcoming_list.find_all(recursive=False):
        if "date-header" in element.attrs.get("class", []):
            current_date = notnone(next(iter(element.children))).get_text(strip=True)
        elif "upcoming-event" in element.attrs.get("class", []):
            start_ts = int(str(notnone(element.get("data-start"))))
            eastern_tz = pytz.timezone("US/Eastern")
            dt_with_tz = datetime.datetime.fromtimestamp(start_ts, tz=eastern_tz)
            title = element.find(class_="event-title")
            group_elem = element.select_one(".realm-title-group") or element.select_one(".realm-title-course-title .realm-main-titles")
            group = group_elem.get_text(strip=True) if group_elem else None

            if title:
                events.append(
                    {
                        "title": title.get_text(strip=True),
                        "date": current_date,
                        "time": dt_with_tz.strftime("%I:%M %p"),
                        "group": group,
                    }
                )

    return events


async def get_upcoming_assignments(
    session: aiohttp.ClientSession, api_base: str, cookies: dict
) -> list:
    """Get upcoming assignments from Schoology."""
    async with async_timeout.timeout(10):
        response = await session.get(
            f"https://{api_base}/home/upcoming_submissions_ajax",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            },
        )
        response.raise_for_status()
        data = await response.json()

    html = data.get("html", "")
    soup = bs.BeautifulSoup(html, features="html.parser")
    assignments = []

    upcoming_list = soup.find(class_="upcoming-list")
    if not upcoming_list:
        return []

    for element in upcoming_list.find_all(recursive=False):
        if "upcoming-event" in element.attrs.get("class", []):
            title = next(
                iter(notnone(element.find(class_="event-title")).children), None
            )
            group = (
                notnone(
                    element.select_one(".realm-title-course-title .realm-main-titles")
                ).get_text(strip=True)
                if element.select_one(".realm-title-course-title .realm-main-titles")
                else None
            )
            due = (
                notnone(
                    element.find_all(class_="readonly-title event-subtitle")[0]
                ).get_text(strip=True)
                if element.find(class_="due-date")
                else None
            )

            if due and notnone(due).startswith("Due "):
                due = notnone(due)[4:]

            if title:
                assignments.append(
                    {
                        "title": title.get_text(strip=True),
                        "group": group,
                        "due": due,
                    }
                )

    return assignments


async def get_overdue_assignments(
    session: aiohttp.ClientSession, api_base: str, cookies: dict
) -> list:
    """Get overdue assignments from Schoology."""
    async with async_timeout.timeout(10):
        response = await session.get(
            f"https://{api_base}/home/overdue_submissions_ajax",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            },
        )
        response.raise_for_status()
        data = await response.json()

    html = data.get("html", "")
    soup = bs.BeautifulSoup(html, features="html.parser")
    assignments = []

    upcoming_list = soup.find(class_="upcoming-list")
    if not upcoming_list:
        return []

    for element in upcoming_list.find_all(recursive=False):
        if "upcoming-event" in element.attrs.get("class", []):
            title = next(
                iter(notnone(element.find(class_="event-title")).children), None
            )
            group = (
                notnone(
                    element.select_one(".realm-title-course-title .realm-main-titles")
                ).get_text(strip=True)
                if element.select_one(".realm-title-course-title .realm-main-titles")
                else None
            )
            due = (
                notnone(
                    element.find_all(class_="readonly-title event-subtitle")[0]
                ).get_text(strip=True)
                if element.find(class_="due-date")
                else None
            )

            if due and notnone(due).startswith("Due "):
                due = notnone(due)[4:]

            if title:
                assignments.append(
                    {
                        "title": title.get_text(strip=True),
                        "group": group,
                        "due": due,
                    }
                )

    return assignments




@pytest.mark.asyncio
async def test_login_success(session, credentials):
    """Test successful login with real Schoology credentials."""
    cookies = await schoology_login(
        session,
        credentials["username"],
        credentials["password"],
        credentials["api_base"],
    )

    assert cookies is not None
    assert isinstance(cookies, dict)
    assert len(cookies) > 0


@pytest.mark.asyncio
async def test_login_invalid_credentials(session, credentials):
    """Test login failure with invalid credentials."""
    with pytest.raises(ValueError, match="Invalid credentials"):
        await schoology_login(
            session, "invalid@example.com", "wrong_password", credentials["api_base"]
        )


@pytest.mark.asyncio
async def test_get_announcements(session, credentials):
    """Test getting announcements from real Schoology API."""
    cookies = await schoology_login(
        session,
        credentials["username"],
        credentials["password"],
        credentials["api_base"],
    )

    announcements = await get_announcements(session, credentials["api_base"], cookies)

    assert isinstance(announcements, list)

    if len(announcements) > 0:
        announcement = announcements[0]
        assert "title" in announcement
        assert "date" in announcement
        assert "likes" in announcement
        assert "comments" in announcement
        assert isinstance(announcement["title"], str)
        assert isinstance(announcement["likes"], int)
        assert isinstance(announcement["comments"], list)


@pytest.mark.asyncio
async def test_get_upcoming_events(session, credentials):
    """Test getting upcoming events from real Schoology API."""
    cookies = await schoology_login(
        session,
        credentials["username"],
        credentials["password"],
        credentials["api_base"],
    )

    events = await get_upcoming_events(session, credentials["api_base"], cookies)

    assert isinstance(events, list)

    if len(events) > 0:
        event = events[0]
        assert "title" in event
        assert "date" in event
        assert "time" in event
        assert isinstance(event["title"], str)
        assert isinstance(event["date"], str)
        assert isinstance(event["time"], str)


@pytest.mark.asyncio
async def test_get_upcoming_assignments(session, credentials):
    """Test getting upcoming assignments from real Schoology API."""
    cookies = await schoology_login(
        session,
        credentials["username"],
        credentials["password"],
        credentials["api_base"],
    )

    assignments = await get_upcoming_assignments(
        session, credentials["api_base"], cookies
    )

    assert isinstance(assignments, list)

    if len(assignments) > 0:
        assignment = assignments[0]
        assert "title" in assignment
        assert "due" in assignment
        assert isinstance(assignment["title"], str)
        if assignment["due"] is not None:
            assert isinstance(assignment["due"], str)


@pytest.mark.asyncio
async def test_get_overdue_assignments(session, credentials):
    """Test getting overdue assignments from real Schoology API."""
    cookies = await schoology_login(
        session,
        credentials["username"],
        credentials["password"],
        credentials["api_base"],
    )

    assignments = await get_overdue_assignments(
        session, credentials["api_base"], cookies
    )

    assert isinstance(assignments, list)

    if len(assignments) > 0:
        assignment = assignments[0]
        assert "title" in assignment
        assert "due" in assignment
        assert isinstance(assignment["title"], str)
        if assignment["due"] is not None:
            assert isinstance(assignment["due"], str)

import logging

LOGGER = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_get_all_data(session, credentials, caplog):
    """Test getting all data types in one test."""
    cookies = await schoology_login(
        session,
        credentials["username"],
        credentials["password"],
        credentials["api_base"],
    )

    with caplog.at_level(logging.DEBUG):
        LOGGER.debug(f"Logged in successfully, obtained {len(cookies)} cookies.")
        LOGGER.debug(f"Cookies: {cookies}")

    announcements = await get_announcements(session, credentials["api_base"], cookies)
    events = await get_upcoming_events(session, credentials["api_base"], cookies)
    upcoming = await get_upcoming_assignments(session, credentials["api_base"], cookies)
    overdue = await get_overdue_assignments(session, credentials["api_base"], cookies)

    assert isinstance(announcements, list)
    assert isinstance(events, list)
    assert isinstance(upcoming, list)
    assert isinstance(overdue, list)

    with caplog.at_level(logging.DEBUG):
        LOGGER.debug(f"Announcements: {len(announcements)}")
        LOGGER.debug(f"Upcoming Events: {len(events)}")
        LOGGER.debug(f"Upcoming Assignments: {len(upcoming)}")
        LOGGER.debug(f"Overdue Assignments: {len(overdue)}")