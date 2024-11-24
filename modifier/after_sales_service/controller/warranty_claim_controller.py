from odoo import http
from odoo.http import request
import json
import base64


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

    @http.route('/warranty/claim/submit', type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def submit_warranty_claim(self, **kwargs):
        """Process the warranty claim form submission with multiple products."""
        try:
            sale_order_id = int(kwargs.get('sale_order_id', 0))
            sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
            customer_id = int(kwargs.get('customer_id', 0))

            # Process each product claim
            for i in range(len([k for k in kwargs if k.startswith('product_claims')])):
                product_id = int(kwargs.get(f'product_claims[{i}][product_id]', 0))
                description = kwargs.get(f'product_claims[{i}][description]', '')

                # Validate product belongs to sale order
                if not any(line.product_id.id == product_id for line in sale_order.order_line):
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

            return request.render('after_sales_service.warranty_claim_success_template', {})

        except Exception as e:
            return request.render('after_sales_service.warranty_claim_form_template', {
                'error': f'Error processing claims: {str(e)}'
            })