from odoo import http

class MyUtilities:

    @staticmethod
    def get_remote_ip():
        # Get the remote IP address from the request object
        return http.request.httprequest.environ.get('REMOTE_ADDR')