
from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request, route
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import base64
from collections import OrderedDict
import json
from datetime import date

class InventoryController(http.Controller):

    @http.route(
        "/equip3_inventory_control/scan_add_product_inventory",
        type="json",
        auth="user",
    )
    def scan_add_product_inventory(self, barcode, vals):
        product_id = request.env['product.product'].search([
                ('barcode', '=ilike', barcode)
            ], limit=1)
        if not product_id:
            return {"warning": _("This Product doesn't exist.")}
        inventory_id = request.env['stock.inventory'].browse(vals.get('active_ids'))
        inventory_line_id = inventory_id.line_ids.filtered(lambda r: r.product_id.id == product_id.id)
        if inventory_line_id:
            inventory_line_id[0].product_qty += 1
        else:
            line_vals = {
                'inventory_id': inventory_id.id,
                'product_qty': 1,
                'theoretical_qty': 1,
                'product_id': product_id.id,
                'location_id': inventory_id.location_ids and inventory_id.location_ids[0].id or request.env.ref('stock.stock_location_stock').id,
                'product_uom_id': product_id.uom_id.id,
                'uom_id': product_id.uom_id.id,
            }
            line_id = request.env['stock.inventory.line'].create(line_vals)
        return {
            "success": _("%(barcode)s product has been scanned successfully.")
            % {"barcode": barcode},
        }

