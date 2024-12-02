from odoo import http
from odoo.http import request
import json
import base64
import logging
from werkzeug.utils import redirect

_logger = logging.getLogger(__name__)

class WarrantyClaimController(http.Controller):

    @http.route('/warranty/claim', type='http', auth="public", website=True)
    def warranty_claim_form(self, **kwargs):
        """Display the warranty claim form with pre-filled customer details if logged in."""
        user_partner = request.env.user.partner_id if request.env.user.id != http.request.env.ref('base.public_user').id else None

        # Get relevant sale orders for the customer
        domain = [('partner_id', '=', user_partner.id)] if user_partner else []
        sale_orders = request.env['sale.order'].sudo().search(domain)

        return request.render('after_sales_service.warranty_claim_form_template', {
            'logged_in_customer': user_partner,
            'sale_orders': sale_orders,
        })

    @http.route('/warranty/get_order_products', type='http', auth="public", website=True)
    def get_order_products(self, sale_order_id, **kwargs):
        """Return products from a specific sale order."""
        try:
            sale_order = request.env['sale.order'].sudo().browse(int(sale_order_id))
            products = []
            for line in sale_order.order_line:
                products.append({
                    'id': line.product_id.id,
                    'name': line.product_id.name
                })
            return json.dumps({'products': products})
        except Exception as e:
            return json.dumps({'error': str(e)})

    @http.route('/warranty/claim/submit', type='http', auth="public", methods=['POST'], website=True, csrf=True)
    def submit_warranty_claim(self, **kwargs):
        """Process the warranty claim form submission with multiple products."""
        try:
            sale_order_id = int(kwargs.get('sale_order_id', 0))
            customer_id = int(kwargs.get('customer_id', 0))

            # Validate sale order
            sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
            if not sale_order.exists() or not sale_order.order_line:
                _logger.error(f"Invalid Sale Order: {sale_order_id}")
                return request.render('after_sales_service.warranty_claim_form_template', {
                    'error': 'Invalid Sale Order or no products available for this order.'
                })

            _logger.info(f"Processing claims for Sale Order ID: {sale_order_id}, Customer ID: {customer_id}")

            # Process each product claim
            product_claim_count = len([k for k in kwargs if k.startswith('product_claims')]) // 3
            for i in range(product_claim_count):
                product_id = int(kwargs.get(f'product_claims[{i}][product_id]', 0))
                description = kwargs.get(f'product_claims[{i}][description]', '')

                # Debug: Log the product ID and sale order lines
                _logger.info(f"Selected Product ID: {product_id}")
                _logger.info(f"Sale Order Lines: {[line.product_id.id for line in sale_order.order_line]}")

                # Validate product belongs to sale order
                if not any(int(line.product_id.id) == int(product_id) for line in sale_order.order_line):
                    _logger.error(f"Invalid product selection in claim #{i + 1}")
                    return request.render('after_sales_service.warranty_claim_form_template', {
                        'error': f'Invalid product selection in claim #{i + 1}'
                    })

                # Create warranty claim
                claim = request.env['warranty.claim'].sudo().create({
                    'customer_id': customer_id,
                    'product_id': product_id,
                    'sale_order_id': sale_order_id,
                    'description': description,
                })
                _logger.info(f"Warranty Claim Created: {claim.id}")

                # Process attachments
                attachments = request.httprequest.files.getlist(f'product_claims[{i}][attachments]')
                for attachment in attachments:
                    if attachment:
                        file_data = attachment.read()
                        request.env['ir.attachment'].sudo().create({
                            'name': attachment.filename,
                            'res_model': 'warranty.claim',
                            'res_id': claim.id,
                            'type': 'binary',
                            'datas': base64.b64encode(file_data),
                        })
                        _logger.info(f"Attachment added: {attachment.filename}")

            return request.render('after_sales_service.warranty_claim_success_template', {})

        except Exception as e:
            _logger.error(f"Error processing warranty claim: {str(e)}")
            return request.render('after_sales_service.warranty_claim_form_template', {
                'error': f'Error processing claims: {str(e)}'
            })

