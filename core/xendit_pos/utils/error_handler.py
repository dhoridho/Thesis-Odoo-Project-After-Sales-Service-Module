# -*- coding: utf-8 -*-
import json
import logging

class ErrorHandler():

    _logger = logging.getLogger(__name__)

    def handleError(self, action, message = None, status_code = 500):

        # Log the error message in odoo logging
        self.logError("{0} - status_code: {1} - message: {2}".format(action, status_code, message))

        # Return default error message if status_code is 500
        if message is None or status_code == 500:
            message = 'We encountered an issue while processing the payment. Please try again.'

        return {
                'error': {
                    'status_code': status_code,
                    'message': message
                }
            }

    def logError(self, message):
        self._logger.error(message)