from odoo import http
from odoo.http import request
import base64
import json
from datetime import datetime,date


class ServiceRequestController(http.Controller):

    @http.route('/service/request', type='http', auth="public", website=True)
    def service_request_form(self, **kwargs):
        """Display the service request form."""
        user_partner = request.env.user.partner_id if request.env.user.id != http.request.env.ref('base.public_user').id else None

        # Get relevant sale orders for the customer
        sale_orders = False
        if user_partner:
            sale_orders = request.env['sale.order'].sudo().search([
                ('partner_id', '=', user_partner.id),
                ('state', 'in', ['sale', 'done'])
            ])

        return request.render('after_sales_service.service_request_form_template', {
            'logged_in_customer': user_partner,
            'sale_orders': sale_orders,
            'datetime': date.today().strftime('%Y-%m-%d'),
        })

    @http.route('/service/get_products', type='json', auth="public", website=True)
    def get_products(self, sale_order_id=None):
        """Return products based on sale order or all products if no sale order."""
        try:
            if sale_order_id:
                # Get products from specific sale order
                sale_order = request.env['sale.order'].sudo().browse(int(sale_order_id))
                products = [(line.product_id.id, line.product_id.name)
                            for line in sale_order.order_line]
            else:
                # Get all sellable products
                products = request.env['product.product'].sudo().search_read(
                    [('sale_ok', '=', True)],
                    ['id', 'name']
                )
                products = [(p['id'], p['name']) for p in products]

            return {'products': products}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/service/request/submit', type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def submit_service_request(self, **kwargs):
        """Process the service request submission."""
        try:
            # Create service request
            vals = {
                'customer_id': int(kwargs.get('customer_id')),
                'product_id': int(kwargs.get('product_id')),
                'request_date': kwargs.get('request_date'),
                'description': kwargs.get('description'),
                'state': 'draft'
            }

            # Add sale order if provided
            if kwargs.get('sale_order_id'):
                vals['sale_order_id'] = int(kwargs.get('sale_order_id'))

            service_request = request.env['service.request'].sudo().create(vals)

            # Process attachments
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

            return request.render('after_sales_service.service_request_success_template', {
                'request_number': service_request.name
            })

        except Exception as e:
            return request.render('after_sales_service.service_request_form_template', {
                'error': f'Error submitting service request: {str(e)}'
            })