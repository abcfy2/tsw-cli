# Reference:
# https://github.com/mermaid-js/mermaid-live-editor/discussions/1291#discussioncomment-6837936
import base64
import json
import zlib

import requests


def _js_string_to_byte(data):
    return bytes(data, "ascii")


def _js_bytes_to_string(data):
    return data.decode("ascii")


def _js_btoa(data):
    return base64.urlsafe_b64encode(data)


def _pako_deflate(data):
    compress = zlib.compressobj(9, zlib.DEFLATED, 15, 8, zlib.Z_DEFAULT_STRATEGY)
    compressed_data = compress.compress(data)
    compressed_data += compress.flush()
    return compressed_data


def generate_pako_link(graphMarkdown: str):
    jGraph = {"code": graphMarkdown, "mermaid": {"theme": "default"}}
    byteStr = _js_string_to_byte(json.dumps(jGraph))
    deflated = _pako_deflate(byteStr)
    dEncode = _js_btoa(deflated)
    link = "http://mermaid.ink/img/pako:" + _js_bytes_to_string(dEncode)
    return link


def generate_image_dataurl(link: str):
    r = requests.get(link)
    return f"data:image/png;base64,{base64.b64encode(r.content).decode()}"
