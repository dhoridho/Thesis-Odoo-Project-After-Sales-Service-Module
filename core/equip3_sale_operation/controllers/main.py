# -*- coding: utf-8 -*-

import base64
import io
import pytz
from odoo import http
from odoo.http import request
from werkzeug.utils import redirect
from datetime import datetime, time, timedelta
from pytz import timezone, UTC
from odoo import fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.sale_product_configurator.controllers.main import ProductConfiguratorController
from odoo.addons.sale.controllers.variant import VariantController
from odoo.addons.website_sale.controllers.main import WebsiteSale

class AttachmentController(http.Controller):

    @http.route(['/attachment/download/<int:attachment_id>'], type='http', auth="public", website=True)
    def download_attcahment(self, attachment_id=None, **post):
        attachment = request.env['ir.attachment'].sudo().search_read(
            [('id', '=', int(attachment_id))],
            ["name", "datas", "type", "res_model", "res_id", "type", "url", "expiry_date"]
        )
        if attachment:
            attachment = attachment[0]
            IrConfigParam = request.env['ir.config_parameter'].sudo()
            expired_date = IrConfigParam.get_param('expired_date', 1)
            expiry_date = attachment.get('expiry_date') + timedelta(hours=int(expired_date))
            timezone = pytz.timezone(request._context.get('tz') or 'UTC')
            local_date = pytz.UTC.localize(fields.Datetime.from_string(datetime.now()))
            local_convert_date = datetime.strptime(local_date.astimezone(timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT), DEFAULT_SERVER_DATETIME_FORMAT)
            expiry_local_date = pytz.UTC.localize(fields.Datetime.from_string(expiry_date))
            expiry_local_convert_date = datetime.strptime(expiry_local_date.astimezone(timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT), DEFAULT_SERVER_DATETIME_FORMAT)
            if local_convert_date > expiry_local_convert_date:
                return request.not_found()
        else:
            return redirect('/attachment/download/%s' % attachment_id)

        if attachment["type"] == "url":
            if attachment["url"]:
                return redirect(attachment["url"])
            else:
                return request.not_found()
        elif attachment["datas"]:
            data = io.BytesIO(base64.standard_b64decode(attachment["datas"]))
            return http.send_file(data, filename=attachment['name'], as_attachment=True)
        else:
            return request.not_found()

class ProductConfiguratorControllerInheirt(ProductConfiguratorController):
    # OVERRIDE
    @http.route(['/sale_product_configurator/configure'], type='json', auth="user", methods=['POST'])
    def configure(self, product_template_id, pricelist_id, warehouse_id=1, **kw):
        add_qty = int(kw.get('add_qty', 1))
        product_template = request.env['product.template'].browse(int(product_template_id))
        pricelist = self._get_pricelist(pricelist_id)

        product_combination = False
        attribute_value_ids = set(kw.get('product_template_attribute_value_ids', []))
        attribute_value_ids |= set(kw.get('product_no_variant_attribute_value_ids', []))
        if attribute_value_ids:
            product_combination = request.env['product.template.attribute.value'].browse(attribute_value_ids)

        if pricelist:
            product_template = product_template.with_context(pricelist=pricelist.id, partner=request.env.user.partner_id,warehouse_id=warehouse_id)

        return request.env['ir.ui.view']._render_template("sale_product_configurator.configure", {
            'product': product_template,
            'pricelist': pricelist,
            'add_qty': add_qty,
            'product_combination': product_combination,
            'warehouse_id':warehouse_id,
        })


class VariantControllerInheirt(VariantController):
    # OVERRIDE
    @http.route(['/sale/get_combination_info'], type='json', auth="user", methods=['POST'])
    def get_combination_info(self, product_template_id, product_id, combination, add_qty, pricelist_id, warehouse_id=1, **kw):
        combination = request.env['product.template.attribute.value'].browse(combination)
        pricelist = self._get_pricelist(pricelist_id)
        ProductTemplate = request.env['product.template']
        if 'context' in kw:
            ProductTemplate = ProductTemplate.with_context(**kw.get('context'))
        product_template = ProductTemplate.browse(int(product_template_id))
        res = product_template._get_combination_info(combination, int(product_id or 0), int(add_qty or 1), pricelist, warehouse_id)
        if 'parent_combination' in kw:
            parent_combination = request.env['product.template.attribute.value'].browse(kw.get('parent_combination'))
            if not combination.exists() and product_id:
                product = request.env['product.product'].browse(int(product_id))
                if product.exists():
                    combination = product.product_template_attribute_value_ids
            res.update({
                'is_combination_possible': product_template._is_combination_possible(combination=combination, parent_combination=parent_combination),
            })
        return res    

class WebsiteSaleStock(WebsiteSale):
    
    @http.route()
    def payment_transaction(self, *args, **kwargs):
        # Retrieve the sale order
        so_id = kwargs.get('so_id')
        access_token = kwargs.get('access_token')
        if so_id:
            env = request.env['sale.order']
            domain = [('id', '=', so_id)]
            if access_token:
                env = env.sudo()
                domain.append(('access_token', '=', access_token))
            order = env.search(domain, limit=1)
        else:
            order = request.website.sale_get_order()

        commitment_date = order.commitment_date
        order.order_line.filtered(lambda o: not o.multiple_do_date or not o.multiple_do_date_new).write({
            'multiple_do_date': commitment_date,
            'multiple_do_date_new': commitment_date,
        })
        
        res = super(WebsiteSaleStock, self).payment_transaction(*args, **kwargs)
        return res