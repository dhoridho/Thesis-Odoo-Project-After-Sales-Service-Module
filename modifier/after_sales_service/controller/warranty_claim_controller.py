from odoo import http, fields
from odoo.http import request

import json
import base64
import logging
from werkzeug.utils import redirect

_logger = logging.getLogger(__name__)

class WarrantyClaimController(http.Controller):

    @http.route('/warranty-claim', type='http', auth="public", website=True)
    def warranty_claim_form(self, **kwargs):
        """Display the warranty claim form with pre-filled customer details if logged in."""
        user_partner = request.env.user.partner_id if request.env.user.id != http.request.env.ref('base.public_user').id else None

        # Get relevant sale orders for the customer
        domain = [('partner_id', '=', user_partner.id), ('state', '=', 'sale')] if user_partner else []
        all_sale_orders = request.env['sale.order'].sudo().search(domain)

        sale_orders = all_sale_orders.filtered(lambda so: any(line.warranty_expire_date for line in so.order_line))
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
                if line.warranty_expire_date:
                    display_name = line.product_id.name + ' ' + str((line.warranty_expire_date - fields.Date.today()).days) + ' Days Remaining' if line.warranty_expire_date else line.product_id.name + ' 0 Days Remaining'
                    products.append({
                        'id': line.product_id.id,
                        'name': display_name
                    })
            return json.dumps({'products': products})
        except Exception as e:
            return json.dumps({'error': str(e)})

    @http.route('/warranty-claim-submit', type='http', auth="public", methods=['POST'], website=True, csrf=True)
    def submit_warranty_claim(self, **kwargs):
        """Process the warranty claim form submission with multiple products."""
        try:
            sale_order_id = int(kwargs.get('sale_order_id', 0))
            partner_id = int(kwargs.get('partner_id', 0))

            # Validate sale order
            sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
            if not sale_order.exists() or not sale_order.order_line:
                _logger.error(f"Invalid Sale Order: {sale_order_id}")
                return request.render('after_sales_service.warranty_claim_form_template', {
                    'error': 'Invalid Sale Order or no products available for this order.'
                })

            _logger.info(f"Processing claims for Sale Order ID: {sale_order_id}, Customer ID: {partner_id}")

            # Method 1: Find unique product claim indices
            product_indices = set()
            for key in kwargs.keys():
                if key.startswith('product_claims[') and '][' in key:
                    try:
                        # Extract index from key like 'product_claims[0][product_id]'
                        index_part = key.split('[')[1].split(']')[0]
                        product_indices.add(int(index_part))
                    except (ValueError, IndexError):
                        continue

            _logger.info(f"Found product claim indices: {sorted(product_indices)}")

            if not product_indices:
                return request.render('after_sales_service.warranty_claim_form_template', {
                    'error': 'No valid product claims found in submission.'
                })

            # Process each product claim
            for i in sorted(product_indices):
                try:
                    product_id_key = f'product_claims[{i}][product_id]'
                    description_key = f'product_claims[{i}][description]'

                    product_id = kwargs.get(product_id_key)
                    description = kwargs.get(description_key, '')

                    _logger.info(f"Processing claim {i}: product_id_key={product_id_key}, value={product_id}")

                    if not product_id:
                        _logger.warning(f"No product_id found for claim {i}, skipping...")
                        continue

                    product_id = int(product_id)

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
                        'partner_id': partner_id,
                        'product_id': product_id,
                        'sale_order_id': sale_order_id,
                        'description': description,
                    })
                    _logger.info(f"Warranty Claim Created: {claim.id}")

                    # Process attachments
                    attachment_key = f'product_claims[{i}][attachments]'
                    attachments = request.httprequest.files.getlist(attachment_key)

                    for attachment in attachments:
                        if attachment and attachment.filename:
                            try:
                                file_data = attachment.read()
                                if file_data:  # Only create attachment if file has content
                                    request.env['ir.attachment'].sudo().create({
                                        'name': attachment.filename,
                                        'res_model': 'warranty.claim',
                                        'res_id': claim.id,
                                        'type': 'binary',
                                        'datas': base64.b64encode(file_data),
                                    })
                                    _logger.info(f"Attachment added: {attachment.filename}")
                            except Exception as attach_error:
                                _logger.error(f"Error processing attachment {attachment.filename}: {str(attach_error)}")
                                # Continue processing other attachments/claims

                except Exception as claim_error:
                    _logger.error(f"Error processing claim {i}: {str(claim_error)}")
                    return request.render('after_sales_service.warranty_claim_form_template', {
                        'error': f'Error processing claim #{i + 1}: {str(claim_error)}'
                    })

            return request.render('after_sales_service.warranty_claim_success_template', {})

        except Exception as e:
            _logger.error(f"Error processing warranty claim: {str(e)}")
            return request.render('after_sales_service.warranty_claim_form_template', {
                'error': f'Error processing claims: {str(e)}'
            })

    # Additional debugging method - you can remove this after fixing
    @http.route('/warranty-claim-debug', type='http', auth="public", methods=['POST'], website=True, csrf=True)
    def debug_warranty_claim(self, **kwargs):
        """Debug method to see what's being submitted"""
        _logger.info("=== DEBUGGING WARRANTY CLAIM SUBMISSION ===")
        for key, value in kwargs.items():
            _logger.info(f"Key: {key} = Value: {value}")

        # Also log files
        for key, file_list in request.httprequest.files.lists():
            _logger.info(f"File Key: {key} = Files: {[f.filename for f in file_list]}")

        return json.dumps({"status": "debug_complete", "kwargs_count": len(kwargs)})

