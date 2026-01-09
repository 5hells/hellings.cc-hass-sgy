"""Sample API Client."""

from __future__ import annotations

from datetime import time
import datetime
import socket
from typing import Any
import contextlib
import typing

import aiohttp
import async_timeout
import bs4 as bs
import pytz
import asyncio


class IntegrationBlueprintApiClientError(Exception):
    """Exception to indicate a general API error."""


class IntegrationBlueprintApiClientCommunicationError(
    IntegrationBlueprintApiClientError,
):
    """Exception to indicate a communication error."""


class IntegrationBlueprintApiClientAuthenticationError(
    IntegrationBlueprintApiClientError,
):
    """Exception to indicate an authentication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise IntegrationBlueprintApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()

T = typing.TypeVar("T")
def notnone(value: T | None) -> T:
    """Helper to assert that a value is not None."""
    if value is None:
        raise ValueError("Expected value to be not None")
    return value

class IntegrationBlueprintApiClient:
    """Sample API Client."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        api_base: str = "x.schoology.com",
        cookies: dict | None = None,
    ) -> None:
        """Sample API Client."""
        self._username = username
        self._password = password
        self._session = session
        self._api_base = api_base
        self._cookies: dict[str, str] = {}
        if cookies:
            self.set_cookies(cookies)

    async def async_login(self) -> dict:
        """
        Authenticate with the API, follow redirects and store cookies.
        """
        try:
            async with async_timeout.timeout(10):
                base_resp = await self._session.request(
                    method="get",
                    url=f"https://{self._api_base}",
                )
                _verify_response_or_raise(base_resp)
                school = base_resp.url.query.get("school")

            login_url = f"https://{self._api_base}/login"
            if school:
                login_url = f"{login_url}?school={school}"

            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method="get",
                    url=login_url,
                )
                _verify_response_or_raise(response)
                login_page = await response.text()

            form = bs.BeautifulSoup(login_page, features="html.parser")
            form = form.find(id="s-user-login-form")
            if not form:
                msg = "Login form not found"
                raise IntegrationBlueprintApiClientError(msg)

            for input_tag in form.find_all("input"):
                if input_tag.get("name") == "mail":
                    input_tag["value"] = self._username
                if input_tag.get("name") == "pass":
                    input_tag["value"] = self._password

            post_data = {
                input_tag["name"]: input_tag.get("value", "")
                for input_tag in form.find_all("input")
                if input_tag.get("name")
            }

            if school and "school" not in post_data:
                post_data["school"] = school

            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method="post",
                    url=login_url,
                    data=post_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                _verify_response_or_raise(response)
                body = await response.text()

            if "Invalid username or password" in body:
                msg = "Invalid credentials"
                raise IntegrationBlueprintApiClientAuthenticationError(msg)

            cookies = {name: morsel.value for name, morsel in response.cookies.items()}
            if cookies:
                self.set_cookies(cookies)

            return cookies

        except TimeoutError as exception:
            msg = f"Timeout error during login - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error during login - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(msg) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened during login - {exception}"
            raise IntegrationBlueprintApiClientError(msg) from exception

    async def async_get_announcements(self) -> Any:
        """Get announcements using the AJAX feed endpoint and parse the HTML output."""
        r = await self._api_wrapper(
            method="get",
            url=f"https://{self._api_base}/home/feed?page=0",
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Cookie": "; ".join(f"{k}={v}" for k, v in self._cookies.items()),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            },
        )

        html = ""
        if isinstance(r, dict):
            html = r.get("output") or r.get("json", {}).get("html") or r.get("html") or r.get("body", "")
        elif isinstance(r, str):
            html = r

        if not html:
            return []

        soup = bs.BeautifulSoup(html, features="html.parser")
        announcements = []
        for announcement in soup.select("ul.s-edge-feed li"):
            pfp = announcement.select_one(".profile-picture a img")
            title_elem = announcement.select_one(".long-username a")
            created = announcement.select_one(".created .small.gray")
            group_to = announcement.select_one("a[href^='/group/']")
            date_elem = announcement.select_one("time")
            likes = int(notnone(announcement.select_one(".s-like-sentence a")).get_text(strip=True).split()[0]) if announcement.select_one(".s-like-sentence a") else 0
            comments = []
            for comment in announcement.select("#s_comments .s_comments_level .discussion-card"):
                pfp_c = comment.select_one(".profile-picture a img")
                author_elem = comment.select_one(".comment-author a")
                content_elem = comment.select_one(".comment-body-wrapper")
                comment_likes = int(notnone(comment.select_one(".s-like-comment-icon")).get_text(strip=True)) if comment.select_one(".s-like-comment-icon") else 0
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


    async def async_get_upcoming_events(self) -> Any:
        """Get upcoming scheduled events from the API."""
        r = await self._api_wrapper(
            method="get",
            url=f"https://{self._api_base}/home/upcoming_ajax",
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Cookie": "; ".join(f"{k}={v}" for k, v in self._cookies.items()),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            }
        )
        json = r.get("json", {})
        html = json.get("html", "")
        soup = bs.BeautifulSoup(html, features="html.parser")
        events = []
        current_date = ""
        for element in notnone(soup.find(class_="upcoming-list")).children:
            e = notnone(element if isinstance(element, bs.Tag) else None)
            if "date-header" in e.attrs["class"]:
                current_date = notnone(next(iter(e.children))).get_text(strip=True)
            elif "upcoming-event" in e.attrs["class"]:
                # 1768262399
                start_ts = int(str(notnone(e.get("data-start"))))
                eastern_tz = pytz.timezone("US/Eastern")
                dt_with_tz = datetime.datetime.fromtimestamp(start_ts, tz=eastern_tz)
                title = e.find(class_="event-title")
                group = notnone(e.select_one(".realm-title-group")).get_text(strip=True) if e.select_one(".realm-title-group") else None
                if title and time:
                    events.append({
                        "title": title.get_text(strip=True),
                        "date": current_date,
                        "time": dt_with_tz.strftime("%I:%M %p"),
                        "group": group,
                    })
        return events
    
    async def async_get_upcoming_assignments(self) -> Any:
        r = await self._api_wrapper(
            method="get",
            url=f"https://{self._api_base}/home/upcoming_submissions_ajax",
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Cookie": "; ".join(f"{k}={v}" for k, v in self._cookies.items()),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            }
        )
        json = r.get("json", {})
        html = json.get("html", "")
        soup = bs.BeautifulSoup(html, features="html.parser")
        assignments = []
        for element in notnone(soup.find(class_="upcoming-list")).children:
            e = notnone(element if isinstance(element, bs.Tag) else None)
            if "upcoming-event" in e.attrs["class"]:
                title = next(iter(notnone(e.find(class_="event-title")).children), None)
                group = notnone(e.select_one(".realm-title-course-title .realm-main-titles")).get_text(strip=True) if e.select_one(".realm-title-course-title .realm-main-titles") else None
                due = notnone(e.find_all(class_="readonly-title event-subtitle")[0]).get_text(strip=True) if e.find(class_="due-date") else None
                if notnone(due).startswith("Due "):
                    due = notnone(due)[4:]
                if title:
                    assignments.append({
                        "title": title.get_text(strip=True),
                        "group": group,
                        "due": due,
                    })
        return assignments

    async def async_get_overdue_assignments(self) -> Any:
        r = await self._api_wrapper(
            method="get",
            url=f"https://{self._api_base}/home/overdue_submissions_ajax",
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Cookie": "; ".join(f"{k}={v}" for k, v in self._cookies.items()),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            }
        )
        json = r.get("json", {})
        html = json.get("html", "")
        soup = bs.BeautifulSoup(html, features="html.parser")
        assignments = []
        for element in notnone(soup.find(class_="overdue-list")).children:
            e = notnone(element if isinstance(element, bs.Tag) else None)
            if "overdue-event" in e.attrs["class"]:
                title = next(iter(notnone(e.find(class_="event-title")).children), None)
                group = notnone(e.select_one(".realm-title-course-title .realm-main-titles")).get_text(strip=True) if e.select_one(".realm-title-course-title .realm-main-titles") else None
                due = notnone(e.find_all(class_="readonly-title event-subtitle")[0]).get_text(strip=True) if e.find(class_="due-date") else None
                if notnone(due).startswith("Due "):
                    due = notnone(due)[4:]
                if title:
                    assignments.append({
                        "title": title.get_text(strip=True),
                        "group": group,
                        "due": due,
                    })
        return assignments

    async def async_get_data(self) -> Any:
        """Compatibility helper used by the config flow to validate credentials."""
        await self.async_login()
        return await self.async_get_announcements()

    async def async_get_all(self) -> dict[str, Any]:
        """Fetch all Schoology data for sensors in one pass."""
        # Ensure logged in before fetching endpoints
        await self.async_login()
        announcements, upcoming_events, upcoming_assignments, overdue_assignments = await asyncio.gather(
            self.async_get_announcements(),
            self.async_get_upcoming_events(),
            self.async_get_upcoming_assignments(),
            self.async_get_overdue_assignments(),
        )
        return {
            "announcements": announcements,
            "upcoming_events": upcoming_events,
            "upcoming_assignments": upcoming_assignments,
            "overdue_assignments": overdue_assignments,
        }

    def set_cookies(self, cookies: dict) -> None:
        """Store cookies and update the session cookie jar."""
        self._cookies.update(cookies)
        with contextlib.suppress(Exception):
            self._session.cookie_jar.update_cookies(self._cookies)

    def get_cookies(self) -> dict:
        """Return stored cookies."""
        return dict(self._cookies)

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    cookies=self._cookies or None,
                )
                _verify_response_or_raise(response)
                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise IntegrationBlueprintApiClientError(
                msg,
            ) from exception
