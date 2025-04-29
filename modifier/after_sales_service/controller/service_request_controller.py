from odoo import http
from odoo.http import request
import base64
from datetime import date
import logging
from werkzeug.utils import redirect


_logger = logging.getLogger(__name__)


class ServiceRequestController(http.Controller):

    @http.route('/service-request', type='http', auth="public", website=True)
    def service_request_form(self, **kwargs):
        """Render the service request form."""
        try:
            user_partner = request.env.user.partner_id if request.env.user.id != http.request.env.ref('base.public_user').id else None
            products = request.env['product.product'].sudo().search_read(
                [('sale_ok', '=', True)], ['id', 'name']
            )
            if not products:
                _logger.warning("No products available with sale_ok=True.")

            return request.render('after_sales_service.service_request_template', {
                'logged_in_customer': user_partner,
                'products': products,
                'current_date': date.today().strftime('%Y-%m-%d'),
            })

        except Exception as e:
            _logger.error(f"Error rendering service request form: {str(e)}")
            return request.render('after_sales_service.service_request_template', {
                'error': f"An error occurred: {str(e)}"
            })

    @http.route('/service-request-submit', type='http', methods=['POST'], auth="public", website=True, csrf=True)
    def service_request_submit(self, **kwargs):
        """Process the service request form submission."""
        try:
            _logger.info("Processing Service Request Submission")
            _logger.info(f"Request Data: {kwargs}")

            vals = {
                'partner_id': int(kwargs.get('partner_id')),
                'product_id': int(kwargs.get('product_id')),
                'request_date': kwargs.get('request_date'),
                'description': kwargs.get('description'),
                'state': 'draft'
            }
            _logger.info(f"Creating Service Request with Data: {vals}")

            service_request = request.env['service.request'].sudo().create(vals)
            _logger.info(f"Service Request Created: {service_request.id}")

            # Handle attachments
            attachments = request.httprequest.files.getlist('attachments')
            for attachment in attachments:
                if attachment:
                    file_data = attachment.read()
                    request.env['ir.attachment'].sudo().create({
                        'name': attachment.filename,
                        'res_model': 'service.request',
                        'res_id': service_request.id,
                        'type': 'binary',
                        'datas': base64.b64encode(file_data),
                    })
                    _logger.info(f"Attachment Added: {attachment.filename}")

            return request.render('after_sales_service.service_request_success_template', {
                'request_number': service_request.name
            })

        except Exception as e:
            request.env.cr.rollback()
            _logger.error(f"Error processing service request: {str(e)}")
            return request.render('after_sales_service.service_request_template', {
                'error': f"An unexpected error occurred: {str(e)}"
            })