from odoo import models, fields, api, tools, _
from odoo.http import request
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import datetime


class KitchenCookingListReport(models.AbstractModel):
    _name = 'report.equip3_kitchen_operations.report_cooking_list'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['kitchen.cooking.list'].browse(docids)

        lines = {}
        total = {}
        is_show_byproduct = {}
        for doc in docs:

            lines[doc.id] = []
            is_show_byproduct[doc.id] = False

            total_to_produce = 0.0
            total_to_consume = 0.0
            total_quantity = 0.0
            for line_id in doc.product_ids:
                product_id = line_id.product_id

                bom_line_ids = []
                byproduct_ids = []
                if product_id.bom_ids:
                    bom_line_ids = product_id.bom_ids[0].bom_line_ids
                    byproduct_ids = product_id.bom_ids[0].byproduct_ids

                product = product_id.name
                finished_uom = product_id.uom_id.name
                to_produce = line_id.to_produce_qty
                if byproduct_ids:
                    is_show_byproduct[doc.id] = True

                n_lines = max(len(bom_line_ids), len(byproduct_ids)) or 1

                for i in range(n_lines):

                    line = {
                        'product': i == 0 and product or '',
                        'to_produce': i == 0 and to_produce or '',
                        'finished_uom': i == 0 and finished_uom or '',
                        'material': '',
                        'material_uom': '',
                        'to_consume': '',
                        'byproduct': '',
                        'quantity': '',
                        'product_obj': i == 0 and product_id or self.env['product.product']
                    }

                    total_to_produce += i == 0 and to_produce or 0.0

                    if not bom_line_ids and not byproduct_ids:
                        lines[doc.id].append(line)
                        break

                    if i < len(bom_line_ids):
                        bom_line_id = bom_line_ids[i]
                        line['material'] = bom_line_id.product_id.name
                        line['material_uom'] = bom_line_id.product_uom_id.name
                        line['to_consume'] = bom_line_id.product_qty * to_produce
                        total_to_consume += line['to_consume']

                    if i < len(byproduct_ids):
                        byproduct_id = byproduct_ids[i]
                        line['byproduct'] = byproduct_id.product_id.name
                        line['quantity'] = byproduct_id.product_qty
                        total_quantity += line['quantity']

                    lines[doc.id].append(line)

            total[doc.id] = {
                'to_produce': total_to_produce,
                'to_consume': total_to_consume,
                'quantity': total_quantity
            }

        values = {
            'doc_ids': docids,
            'doc_model': 'kitchen.cooking.list',
            'docs': docs,
            'data': data,
            'lines': lines,
            'total': total,
            'is_show_byproduct': is_show_byproduct
        }
        return values


class KitchenCookingList(models.TransientModel):
    _name = 'kitchen.cooking.list'
    _description = 'Kitchen Cooking List'

    def default_get(self, list_field):
        res = super(KitchenCookingList, self).default_get(list_field)
        kitchen_context = request.session.get('kitchen_context', dict())
        res['warehouse_id'] = kitchen_context.get('warehouse', False)
        res['from_date'] = kitchen_context.get('from_date', fields.Date.today())
        res['to_date'] = kitchen_context.get('to_date', fields.Date.today() + relativedelta(days=7))
        res['company_id'] = self.env.company.id
        return res

    @api.onchange('warehouse_id', 'from_date', 'to_date')
    def _onchange_warehouse_date(self):

        from_date = self.from_date
        to_date = self.to_date

        if not from_date or not to_date:
            raise UserError(_('Please specify period!'))

        if to_date < from_date:
            raise UserError(_("You can't select to date < from date!"))

        warehouse_id = self.warehouse_id

        products = self.env['internal.transfer.line'].search([
            ('product_line.is_outlet_order', '=', True),
            ('product_line.source_warehouse_id', '=', warehouse_id.id)
        ]).mapped('product_id')

        product_ids = [(5,)]
        if products and warehouse_id:
            products = products.with_context(warehouse=warehouse_id.id)
            res = products._compute_kitchen_quantities_dict(from_date, to_date)

            for product_id in res:
                values = {
                    'list_id': self.id,
                    'product_id': product_id,
                    'inventory_quantity': res[product_id]['kitchen_inventory_quantity'],
                    'outgoing_qty': res[product_id]['kitchen_outgoing_qty'],
                    'to_produce_qty': res[product_id]['kitchen_to_produce_qty']
                }
                product_ids.append((0, 0, values))
        self.product_ids = product_ids

    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    company_id = fields.Many2one('res.company', string='Company')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    product_ids = fields.One2many('kitchen.cooking.list.line', 'list_id', string='Product Lines')

    def action_print(self):
        return self.env.ref('equip3_kitchen_operations.action_report_kitchen_cooking_list').report_action(self.ids, data=None)

    def action_print_html(self):
        ir_config_param = self.env['ir.config_parameter'].sudo()
        web_base_url = ir_config_param.get_param('web.base.url')

        if web_base_url:
            url = '%s/report/html/equip3_kitchen_operations.report_cooking_list/%s' % (web_base_url, self.id)
            return {
                'name': 'Check HTML',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': url
            }

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_formatted_date(self, date):
        self.ensure_one()
        lang = self.env['res.lang'].search([("code", "=", self.env.user.lang or 'en_US')])
        timestamp = datetime.datetime.strptime(
            str(date), tools.DEFAULT_SERVER_DATE_FORMAT)
        ts = fields.Datetime.context_timestamp(self, timestamp)
        formatted_date = ts.strftime(lang.date_format)
        return formatted_date


class KitchenCookingListLine(models.TransientModel):
    _name = 'kitchen.cooking.list.line'
    _description = 'Kitchen Cooking lIst Line'

    list_id = fields.Many2one('kitchen.cooking.list', string='Cooking List', required=True, copy=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string="UoM")
    inventory_quantity = fields.Float(string='Quantity on Hand', digits='Product Unit of Measure')
    outgoing_qty = fields.Float(string='Forecasted Outgoing', digits='Product Unit of Measure')
    to_produce_qty = fields.Float(string='To Produce', digits='Product Unit of Measure')
