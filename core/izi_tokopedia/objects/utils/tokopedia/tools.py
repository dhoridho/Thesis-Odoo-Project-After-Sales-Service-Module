# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from .exception import TokopediaAPIError


def validate_response(response):
    if response.status_code != 200:
        if response.status_code not in [400, 500]:
            response.raise_for_status()
        # result = response.json()
        if 'header' in response.json():
            header_response = response.json()['header']
            if 'data' in response.json() and response.json()['data']:
                data_response = response.json()['data']
                if 'fail_data' in data_response:
                    if data_response.get('fail_data') == 1:
                        error_description = data_response.get('failed_rows_data')[0]
                        header_response.update({
                            'error_description': error_description.get('error')
                        })
            raise TokopediaAPIError(header_response)
        else:
            raise TokopediaAPIError(response.json())
    else:
        res_response = response.headers['Content-Type'].split(';')[0]
        if res_response == 'application/json':
            if 'error' in response.json():
                if response.json()['error']:
                    raise TokopediaAPIError(response.json())
            if 'data' in response.json() and response.json()['data']:
                resp = response.json()['data']
                if 'fail_data' in resp:
                    if resp.get('fail_data') == 1:
                        raise TokopediaAPIError(resp.get('failed_rows_data')[0])
    return response

def sanitize_response(response):
    # return response.json()['data']
    if 'error' in response.json():
        if response.json()['error']:
            raise TokopediaAPIError(response.json())
    if 'fail_data' in response.json()['data']:
        resp = response.json()['data']
        if resp.get('fail_data') == 1:
            raise TokopediaAPIError(resp.get('failed_rows_data')[0])
    return response.json()['data']

def pagination_get_pages(limit=0, per_page=50):
    pages = []  # tuple of page number and total item per page
    page = 1

    if 0 < limit <= per_page:
        pages.append((page, limit))
    elif limit > per_page:
        total_page = limit // per_page
        remainder = limit % per_page

        while page <= total_page:
            pages.append((page, per_page))
            page += 1

        if remainder > 0:
            pages.append((total_page + 1, remainder))

    return pages


def pagination_datetime_range(from_date, to_date, max_interval_day=3):
    date_ranges = []
    one_second = relativedelta(seconds=1)
    one_minute = relativedelta(minutes=1)
    max_interval_day = timedelta(days=max_interval_day)
    def interval_day(fr, to): return to - fr

    if from_date == to_date:
        return [(from_date - one_minute, to_date + one_minute)]

    while from_date < to_date:
        if interval_day(from_date, to_date) <= max_interval_day:
            date_ranges.append((from_date, to_date))
            from_date = to_date + one_second
        else:
            start_interval_day = from_date
            end_interval_day = from_date + max_interval_day

            if end_interval_day > to_date:
                end_interval_day = to_date
                from_date = to_date + one_second

            date_ranges.append((start_interval_day, end_interval_day))
            if from_date != to_date:
                from_date = end_interval_day + one_second
    return date_ranges


def pagination_date_range(from_date, to_date, max_interval_day=3):
    date_ranges = []
    max_interval_day = timedelta(days=max_interval_day)
    def interval_day(fr, to): return to - fr

    if from_date == to_date:
        return [(from_date, to_date)]

    while from_date < to_date:
        if interval_day(from_date, to_date) <= max_interval_day:
            date_ranges.append((from_date, to_date))
            from_date = to_date
        else:
            start_interval_day = from_date
            end_interval_day = from_date + max_interval_day

            if end_interval_day > to_date:
                end_interval_day = to_date
                from_date = to_date

            date_ranges.append((start_interval_day, end_interval_day))
            if from_date != to_date:
                from_date = end_interval_day
    return date_ranges
