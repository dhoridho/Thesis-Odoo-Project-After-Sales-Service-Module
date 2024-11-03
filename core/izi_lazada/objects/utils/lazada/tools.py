# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from dateutil.relativedelta import relativedelta
from datetime import timedelta


from .exception import LazadaAPIError


def validate_response(response):
    if response.code != '0':
        raise LazadaAPIError(response.body)
    return response


def sanitize_response(response):
    return response.body['data']


def process_response(response):
    return sanitize_response(validate_response(response))


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
    one_second = relativedelta(seconds=1)
    interval_day = relativedelta(days=max_interval_day)

    while from_date < to_date:
        total_days = (to_date - from_date).days

        if total_days <= max_interval_day:
            date_ranges.append((from_date, to_date))
            from_date = to_date
        else:
            start_interval_day = from_date
            end_interval_day = from_date + interval_day

            if end_interval_day > to_date:
                end_interval_day = to_date
                from_date = to_date

            date_ranges.append((start_interval_day, end_interval_day))
            if from_date != to_date:
                from_date = end_interval_day + one_second
    return date_ranges
