"""Sample API Client."""

from __future__ import annotations

from datetime import time
import datetime
import socket
from typing import Any
import contextlib
import typing
import logging

import aiohttp
import async_timeout
import bs4 as bs
import pytz
import asyncio


_LOGGER = logging.getLogger(__name__)

# Cache timezone to avoid blocking I/O in event loop
_EASTERN_TZ = pytz.timezone("US/Eastern")


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
    ) -> None:
        """Sample API Client."""
        self._username = username
        self._password = password
        self._session = session
        self._api_base = api_base
        self._cookies: dict[str, str] = {}
        # Ensure session has proper User-Agent header
        if "User-Agent" not in self._session.headers:
            self._session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            })

    async def async_login(self) -> dict:
        """
        Authenticate with the API, follow redirects and store cookies.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            }
            
            async with async_timeout.timeout(10):
                base_resp = await self._session.get(
                    f"https://{self._api_base}/",
                    allow_redirects=True,
                    headers=headers,
                )
                base_resp.raise_for_status()
                login_url = str(base_resp.url)

            _LOGGER.debug("Login URL: %s", login_url)

            async with async_timeout.timeout(10):
                response = await self._session.get(login_url, headers=headers)
                response.raise_for_status()
                login_page = await response.text()

            form = bs.BeautifulSoup(login_page, features="html.parser")
            form_elem = form.find(id="s-user-login-form")
            if not form_elem:
                msg = f"Login form not found. Expected form with id='s-user-login-form'"
                raise IntegrationBlueprintApiClientError(msg)

            form_action = form_elem.get("action") or login_url
            if not form_action.startswith("http"):
                if form_action.startswith("/"):
                    form_action = f"https://{self._api_base}{form_action}"
                else:
                    form_action = f"{login_url}/{form_action}"

            post_data = {
                "mail": self._username,
                "pass": self._password,
            }
            for input_tag in form_elem.find_all("input"):
                input_name = input_tag.get("name")
                if input_name and input_name not in ["mail", "pass"]:
                    post_data[input_name] = input_tag.get("value", "")

            async with async_timeout.timeout(10):
                response = await self._session.post(
                    form_action,
                    data=post_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
                    },
                    allow_redirects=True,
                )
                response.raise_for_status()
                body = await response.text()

            _LOGGER.debug("After login, final URL: %s", response.url)
            _LOGGER.debug("Response status: %s", response.status)
            _LOGGER.debug("Cookies in jar: %s", len(list(self._session.cookie_jar)))

            if "Invalid username or password" in body or "login" in str(response.url).lower():
                if "invalid" in body.lower():
                    msg = "Invalid credentials"
                    _LOGGER.warning("Login failed: %s", msg)
                    raise IntegrationBlueprintApiClientAuthenticationError(msg)
                else:
                    msg = "Login failed - still on login page"
                    _LOGGER.warning("Login failed: %s", msg)
                    raise IntegrationBlueprintApiClientError(msg)

            cookies = {}
            for cookie in self._session.cookie_jar:
                cookies[cookie.key] = cookie.value
                self._cookies[cookie.key] = cookie.value

            _LOGGER.info("Successfully logged in to Schoology, obtained %d cookies", len(cookies))
            return cookies
        except TimeoutError as exception:
            msg = f"Timeout error during login - {exception}"
            _LOGGER.error("Login timeout: %s", exception)
            raise IntegrationBlueprintApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error during login - {exception}"
            _LOGGER.error("Login network error: %s", exception)
            raise IntegrationBlueprintApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened during login! - {exception}"
            _LOGGER.exception("Unexpected login error: %s", exception)
            raise IntegrationBlueprintApiClientError(
                msg,
            ) from exception

    async def async_get_announcements(self) -> Any:
        """Get announcements using the AJAX feed endpoint and parse the HTML output."""
        r = await self._api_wrapper(
            method="get",
            url=f"https://{self._api_base}/home/feed?page=0",
            headers={
                "Cookie": "; ".join(f"{k}={v}" for k, v in self._cookies.items()),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            },
        )

        html = r.get("output", "")

        if not html:
            return []

        soup = bs.BeautifulSoup(html, features="html.parser")
        announcements = []
        for announcement in soup.select("ul.s-edge-feed li"):
            pfp = announcement.select_one(".profile-picture a img")
            title_elem = announcement.select_one(".long-username a")
            created = announcement.select_one(".created .small.gray")
            group_to = announcement.select_one("a[href^='/group/']")
            date_elem = created
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
        _LOGGER.debug("Retrieved %d announcements", len(announcements))
        return announcements


    async def async_get_upcoming_events(self) -> Any:
        """Get upcoming scheduled events from the API."""
        r = await self._api_wrapper(
            method="get",
            url=f"https://{self._api_base}/home/upcoming_ajax",
            headers={
                "Cookie": "; ".join(f"{k}={v}" for k, v in self._cookies.items()),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            }
        )
        html = r.get("html", "")
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
                # 1768262399
                start_ts = int(str(notnone(element.get("data-start"))))
                dt_with_tz = datetime.datetime.fromtimestamp(start_ts, tz=_EASTERN_TZ)
                title = element.find(class_="event-title")
                group_elem = element.select_one(".realm-title-group") or element.select_one(".realm-title-course-title .realm-main-titles")
                group = group_elem.get_text(strip=True) if group_elem else None
                if title:
                    events.append({
                        "title": title.get_text(strip=True),
                        "date": current_date,
                        "time": dt_with_tz.strftime("%I:%M %p"),
                        "group": group,
                    })
        _LOGGER.debug("Retrieved %d upcoming events", len(events))
        return events
    
    async def async_get_upcoming_assignments(self) -> Any:
        r = await self._api_wrapper(
            method="get",
            url=f"https://{self._api_base}/home/upcoming_submissions_ajax",
            headers={
                "Cookie": "; ".join(f"{k}={v}" for k, v in self._cookies.items()),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            }
        )
        html = r.get("html", "")
        soup = bs.BeautifulSoup(html, features="html.parser")
        assignments = []
        upcoming_list = soup.find(class_="upcoming-list")
        if not upcoming_list:
            return []
        for element in upcoming_list.find_all(recursive=False):
            if "upcoming-event" in element.attrs.get("class", []):
                title = next(iter(notnone(element.find(class_="event-title")).children), None)
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
                    assignments.append({
                        "title": title.get_text(strip=True),
                        "group": group,
                        "due": due,
                    })
        _LOGGER.debug("Retrieved %d upcoming assignments", len(assignments))
        return assignments

    async def async_get_overdue_assignments(self) -> Any:
        """Get overdue assignments from the API."""
        r = await self._api_wrapper(
            method="get",
            url=f"https://{self._api_base}/home/overdue_submissions_ajax",
            headers={
                "Cookie": "; ".join(f"{k}={v}" for k, v in self._cookies.items()),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            }
        )
        html = r.get("html", "")
        soup = bs.BeautifulSoup(html, features="html.parser")
        assignments = []
        upcoming_list = soup.find(class_="upcoming-list")
        if not upcoming_list:
            return []
        for element in upcoming_list.find_all(recursive=False):
            if "upcoming-event" in element.attrs.get("class", []):
                title = next(iter(notnone(element.find(class_="event-title")).children), None)
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
                    assignments.append({
                        "title": title.get_text(strip=True),
                        "group": group,
                        "due": due,
                    })
        _LOGGER.debug("Retrieved %d overdue assignments", len(assignments))
        return assignments

    async def async_get_data(self) -> Any:
        """Compatibility helper used by the config flow to validate credentials."""
        await self.async_login()
        return await self.async_get_announcements()

    async def async_get_all(self) -> dict[str, Any]:
        """Fetch all Schoology data for sensors in one pass."""
        _LOGGER.debug("Starting fetch of all Schoology data")
        # Ensure logged in before fetching endpoints
        await self.async_login()
        _LOGGER.debug("Login successful, fetching data endpoints")
        announcements, upcoming_events, upcoming_assignments, overdue_assignments = await asyncio.gather(
            self.async_get_announcements(),
            self.async_get_upcoming_events(),
            self.async_get_upcoming_assignments(),
            self.async_get_overdue_assignments(),
        )
        result = {
            "announcements": announcements,
            "upcoming_events": upcoming_events,
            "upcoming_assignments": upcoming_assignments,
            "overdue_assignments": overdue_assignments,
        }
        _LOGGER.info("Successfully fetched all data: %d announcements, %d events, %d upcoming assignments, %d overdue assignments",
                    len(announcements), len(upcoming_events), len(upcoming_assignments), len(overdue_assignments))
        return result

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
        _LOGGER.debug("Making %s request to %s", method.upper(), url)
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
                result = await response.json()
                _LOGGER.debug("Successfully received response from %s", url)
                return result

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            _LOGGER.error("API request timeout for %s: %s", url, exception)
            raise IntegrationBlueprintApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            _LOGGER.error("API request network error for %s: %s", url, exception)
            raise IntegrationBlueprintApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            _LOGGER.exception("Unexpected API error for %s: %s", url, exception)
            raise IntegrationBlueprintApiClientError(
                msg,
            ) from exception
