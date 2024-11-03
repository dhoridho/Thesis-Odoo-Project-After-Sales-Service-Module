# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

class TokopediaAPIError(Exception):
    def __init__(self, tp_header):
        # self.message = "Tokopedia API error with the code {error_code}: {messages}."
        if tp_header.get('message'):
            self.message = "Tokopedia API error: {message} and request ID: {req_id}"
        elif tp_header.get('error'):
            self.message = "Tokopedia API error: {error}"
        elif tp_header.get('messages'):
            self.message = "Tokopedia API error: {messages}"
        else:
            self.message = "Tokopedia API error with the code {error_code}: {messages}"

        if tp_header.get('reason'):
            self.message = '%s\n\n Reason: {reason}' % self.message
        if tp_header.get('error_description'):
            self.message = '%s\n\n Reason: {error_description}' % self.message
        super(TokopediaAPIError, self).__init__(self.message.format(**tp_header))
