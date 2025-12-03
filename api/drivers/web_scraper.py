"""
Web scraper driver for extracting data from websites.
"""

import json
import requests
from typing import Dict, Any, List
from .base import BaseDriver, DriverResponse


class WebScraperDriver(BaseDriver):
    type = "web_scraper"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """Scrape data from a website."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return DriverResponse({
                "status": "error",
                "error": "beautifulsoup4 package not installed. Run: pip install beautifulsoup4"
            })

        # Get configuration
        url = node.get("data", {}).get("url", "")
        method = node.get("data", {}).get("method", "css")  # css or xpath
        selector = node.get("data", {}).get("selector", "")
        extract = node.get("data", {}).get("extract", "text")  # text, html, attr
        attr_name = node.get("data", {}).get("attr_name", "href")
        multiple = node.get("data", {}).get("multiple", True)
        timeout = int(node.get("data", {}).get("timeout", 30))
        headers_str = node.get("data", {}).get("headers", "")

        # Support {input} placeholder in URL
        input_data = context.get("input", "")
        if isinstance(input_data, (dict, list)):
            input_str = json.dumps(input_data)
        else:
            input_str = str(input_data)

        url = url.replace("{input}", input_str) if url else input_str

        if not url:
            return DriverResponse({
                "status": "error",
                "error": "URL is required"
            })

        if not selector:
            return DriverResponse({
                "status": "error",
                "error": "Selector is required"
            })

        try:
            # Parse headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            if headers_str:
                try:
                    custom_headers = json.loads(headers_str)
                    headers.update(custom_headers)
                except json.JSONDecodeError:
                    # Fall back to line-by-line format
                    for line in headers_str.strip().split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            headers[key.strip()] = value.strip()

            # Fetch page
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract data based on method
            results = []

            if method == "css":
                elements = soup.select(selector)
            elif method == "xpath":
                # BeautifulSoup doesn't support XPath directly, suggest using lxml
                return DriverResponse({
                    "status": "error",
                    "error": "XPath not supported yet. Use CSS selectors instead."
                })
            else:
                return DriverResponse({
                    "status": "error",
                    "error": f"Unknown method: {method}. Use 'css' or 'xpath'."
                })

            # Extract content from elements
            for element in elements:
                if extract == "text":
                    results.append(element.get_text(strip=True))
                elif extract == "html":
                    results.append(str(element))
                elif extract == "attr":
                    attr_value = element.get(attr_name)
                    if attr_value:
                        results.append(attr_value)

                # If not multiple, return first result only
                if not multiple and results:
                    break

            # Return results
            if not multiple:
                output = results[0] if results else None
            else:
                output = results

            return DriverResponse({
                "status": "ok",
                "output": output,
                "count": len(results) if multiple else (1 if results else 0),
                "url": url,
                "selector": selector,
            })

        except requests.exceptions.Timeout:
            return DriverResponse({
                "status": "error",
                "error": f"Request timed out after {timeout} seconds"
            })
        except requests.exceptions.HTTPError as e:
            return DriverResponse({
                "status": "error",
                "error": f"HTTP error: {e.response.status_code} - {str(e)}"
            })
        except requests.exceptions.RequestException as e:
            return DriverResponse({
                "status": "error",
                "error": f"Request failed: {str(e)}"
            })
        except Exception as e:
            return DriverResponse({
                "status": "error",
                "error": f"Scraping error: {str(e)}"
            })
