#!/usr/bin/env python3
"""
camera_discovery.py — ONVIF Camera Discovery Tool

Reads an ONVIF WS-Discovery XML response (file or stdin), parses ProbeMatch
elements, extracts camera info, and prints JSON.

Requirements implemented:
  - Parse ONVIF ProbeMatch elements
  - Extract: uuid, model, name, location, service_url, ip
  - Output valid JSON to stdout
  - --input (default stdin), --timeout
  - Graceful errors: timeout, parse errors, missing fields
"""

import argparse
import json
import re
import signal
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse


class TimeoutError(Exception):
    pass


def _alarm_handler(signum, frame):
    raise TimeoutError("Discovery timed out")


def parse_args():
    """Parse command line arguments."""
    p = argparse.ArgumentParser(description="Parse ONVIF WS-Discovery XML and output discovered cameras as JSON.")
    p.add_argument(
        "--input",
        default="-",
        help="Path to XML file (default: stdin). Use '-' for stdin.",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Timeout in seconds for reading/parsing (default: 5).",
    )
    return p.parse_args()


def _text(elem):
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def _extract_uuid(endpoint_str: str) -> str:
    # Common formats:
    #   urn:uuid:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    #   uuid:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    m = re.search(r"uuid:([0-9a-fA-F-]{36})", endpoint_str)
    if m:
        return m.group(1).lower()
    # fallback: if exactly 36 chars w/ dashes
    m2 = re.search(r"([0-9a-fA-F-]{36})", endpoint_str)
    return m2.group(1).lower() if m2 else ""


def _extract_ip_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        return host
    except Exception:
        return ""


def parse_onvif_response(xml_content: str):
    """Parse ONVIF WS-Discovery XML and return list of camera dicts."""
    # Namespaces vary across vendors; we search by local-name patterns where possible.
    # Still, define common namespaces for faster lookups if present.
    ns = {
        "s": "http://www.w3.org/2003/05/soap-envelope",
        "a": "http://schemas.xmlsoap.org/ws/2004/08/addressing",
        "d": "http://schemas.xmlsoap.org/ws/2005/04/discovery",
        "dn": "http://www.onvif.org/ver10/network/wsdl",
        "tds": "http://www.onvif.org/ver10/device/wsdl",
    }

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Malformed XML: {e}") from e

    cameras = []

    # ProbeMatch can be in various namespaces; easiest is to search by tag suffix
    def iter_probematch_elements(r):
        for el in r.iter():
            if el.tag.endswith("ProbeMatch"):
                yield el

    for pm in iter_probematch_elements(root):
        # Try to find Address (endpoint / UUID)
        address = ""
        for el in pm.iter():
            if el.tag.endswith("Address"):
                address = _text(el)
                break
        uuid = _extract_uuid(address)

        # Service URL usually in XAddrs
        service_url = ""
        for el in pm.iter():
            if el.tag.endswith("XAddrs"):
                # XAddrs may contain multiple URLs space-separated
                xaddrs = _text(el)
                if xaddrs:
                    service_url = xaddrs.split()[0]
                break

        ip = _extract_ip_from_url(service_url)

        # Vendor specific scopes contain model/name/location as URIs.
        # Example scope patterns:
        #   onvif://www.onvif.org/name/AXIS%20P3265-LVE
        #   onvif://www.onvif.org/hardware/P3265-LVE
        #   onvif://www.onvif.org/location/LoadingDockA
        name = ""
        model = ""
        location = ""

        scopes_text = ""
        for el in pm.iter():
            if el.tag.endswith("Scopes"):
                scopes_text = _text(el)
                break

        # Parse scopes tokens (space-separated)
        if scopes_text:
            tokens = scopes_text.split()
            for t in tokens:
                if "/name/" in t and not name:
                    name = t.split("/name/", 1)[1]
                elif "/hardware/" in t and not model:
                    model = t.split("/hardware/", 1)[1]
                elif "/location/" in t and not location:
                    location = t.split("/location/", 1)[1]

            # Decode common URL encoding %20 for readability (basic)
            name = name.replace("%20", " ").strip()
            model = model.replace("%20", " ").strip()
            location = location.replace("%20", " ").strip()

        # Graceful handling of missing fields: keep empty strings
        cameras.append(
            {
                "uuid": uuid,
                "model": model,
                "name": name,
                "location": location,
                "service_url": service_url,
                "ip": ip,
            }
        )

    return cameras


def main():
    args = parse_args()

    # Timeout handling (unix only; ok for interview task)
    if args.timeout and args.timeout > 0:
        signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(args.timeout)

    try:
        if args.input == "-" or args.input is None:
            xml_content = sys.stdin.read()
        else:
            with open(args.input, "r", encoding="utf-8") as f:
                xml_content = f.read()

        cameras = parse_onvif_response(xml_content)
        # Always output valid JSON
        print(json.dumps(cameras, indent=2))
        return 0

    except TimeoutError:
        # Graceful timeout error
        print(json.dumps({"error": "timeout", "message": f"Timed out after {args.timeout}s"}))
        return 2
    except FileNotFoundError:
        print(json.dumps({"error": "file_not_found", "message": f"Input file not found: {args.input}"}))
        return 2
    except ValueError as e:
        print(json.dumps({"error": "parse_error", "message": str(e)}))
        return 2
    except Exception as e:
        print(json.dumps({"error": "unknown_error", "message": str(e)}))
        return 2
    finally:
        # Disable alarm
        try:
            signal.alarm(0)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())