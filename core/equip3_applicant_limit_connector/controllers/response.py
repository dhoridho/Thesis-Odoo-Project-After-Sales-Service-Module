# -*- coding: utf-8 -*-

from math import ceil
import json
from datetime import datetime

from odoo.exceptions import *

from .helpers import *


class APIResponse:
    status_code = 200
    content = False
    paging = {}
    message = ""
    token = ''

    def set_status_code(self, response_status_code):
        self.status_code = response_status_code
        self.message = STATUS_CODE[response_status_code]

    def set_not_found(self):
        self.status_code = 404
        self.message = STATUS_CODE[404]

    def set_content(self, response_content):
        self.content = response_content

    def set_pages(self, pages_count):
        self.paging['pages'] = pages_count

    def set_current_page(self, page_number):
        self.paging['current_page'] = page_number

    def process_page(self, model, domain):
        pages = model.search_count(domain) / PAGE_DATA_LIMIT
        self.set_pages(ceil(pages))

    def get_records_by_page(self, model, domain, page=1, paging=False):
        if paging:
            self.process_page(model, domain)

        offset = 0
        if page > 1:
            offset = (page * PAGE_DATA_LIMIT) - PAGE_DATA_LIMIT

        record_ids = model.search([], limit=PAGE_DATA_LIMIT, offset=offset)

        self.set_current_page(page)
        if record_ids:
            return record_ids
        else:
            return []

    def get_response(self):
        if self.status_code == 404:
            self.content = False

        response = {
            'status_code': self.status_code,
            'message': self.message,
            'content': self.content,
            'paging': self.paging,
        }
        return response
