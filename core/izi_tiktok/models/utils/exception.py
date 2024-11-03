# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
import logging
import json

_logger = logging.getLogger(__name__)


class TiktokAPIError(Exception):

    def __init__(self, tts_header):
        if tts_header.get('message'):
            self.message = "Tiktok API error with the code {error}: {message}"
        else:
            self.message = "Tiktok API error with the code {error} and request ID: {request_id}"

        if tts_header.get('response') != '':
            self.message + ' caused by {response}'
        # _logger.error(json.dumps(sp_header, indent=1))
        super(TiktokAPIError, self).__init__(self.message.format(**tts_header))
