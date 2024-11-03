# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime,timedelta
import pytz
import xlwt
import base64
from io import BytesIO
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import tools
from odoo.tools.float_utils import float_compare, float_round

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    title = fields.Char("Title Sale Margin")
    distance_btn_2_loc = fields.Float("Distance in KM", copy=False)

    def get_date(self):
        return datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    @api.model
    def set_dashboard_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('sale.sale_menu_root').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-sales-sales-dahboard'})

    @api.model
    def set_quotation_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'quotation'),
            ('parent_id', '=', self.env.ref('sale.sale_menu_root').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-sales-quotation-monitoring'})

class SaleMargin(models.Model):
    _name = 'sale.data.margin'
    _description = "Sale Data Margin"

    partner_id = fields.Many2one('res.partner')
    company_id = fields.Many2one('res.company')
    branch_id = fields.Many2one('res.branch')
    title = fields.Char("Title Report Sales Margin")
    order_line = fields.One2many('sale.data.margin.line', 'margin_id')
    date_order = fields.Datetime(string='Date Order')
    margin = fields.Float('margin')

    def get_date(self):
        return datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

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


class SaleMarginLine(models.Model):
    _name = 'sale.data.margin.line'
    _description = "Sale Data Margin Line"

    margin_id = fields.Many2one('sale.data.margin')
    product_id = fields.Many2one('product.product')
    product_qty = fields.Float('qty')
    price_subtotal = fields.Float('subtotal')
    margin = fields.Float('margin')
    cost_price = fields.Float('cost price')
    cost_per_warehouse = fields.Float('cost price')


class SaleDetailExcel(models.Model):
    _name = "sales.margin.xls"
    _description = "Sales Margin XLS"

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sales.margin.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }

class SalesMarginWizard(models.TransientModel):
    _name = "sale.margin.report.wizard"
    _description = "sale margin report wizard model"

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    partner_ids = fields.Many2many('res.partner', string='Customer')
    start_date = fields.Datetime(
        string="Start Date", required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(
        string="End Date", required=True, default=fields.Datetime.now)
    company_ids = fields.Many2many(
        'res.company', string='Companies', default=default_company_ids)
    branch_id = fields.Many2one('res.branch', domain=_domain_branch, string="Branch")

    def print_report(self):
        domain = [
            ('date_order', '>=', fields.Date.to_string(self.start_date)),
            ('date_order', '<=', fields.Date.to_string(self.end_date)),
            ("state", 'in', ('sale','done'))
        ]
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))

        orders = self.env['sale.order'].sudo().search(domain)

        if orders:
            for order in orders:
                order.title = "Period " + self.start_date.strftime("%B %Y - ") + self.end_date.strftime("%B %Y")

            list_id = []
            list_line_id = []
            sale_margin_obj = self.env['sale.data.margin']
            sale_margin_line_obj = self.env['sale.data.margin.line']

            if not self.partner_ids:
                for order in orders:
                    rec1 = sale_margin_obj.search([('company_id', '=', order.company_id.id),('id', 'in', list_id)], limit=1)
                    if not rec1:
                        sale_margin = sale_margin_obj.create({
                            'partner_id': order.partner_id.id,
                            'company_id': order.company_id.id,
                            'date_order': order.date_order,
                            'title': "Period " + self.start_date.strftime("%B %Y - ") + self.end_date.strftime("%B %Y"),
                            'branch_id': order.branch_id.id,
                            'margin': order.margin,
                        })
                        list_id.append(sale_margin.id)
                        for line in order.order_line.filtered(lambda x: x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True ):
                            lines = sale_margin_line_obj.create({
                                'margin_id': sale_margin.id,
                                'product_id': line.product_id.id,
                                'product_qty': line.product_qty,
                                'price_subtotal': line.price_subtotal,
                                'margin': line.margin
                            })
                            list_line_id.append(lines.id)
                    else:
                        for line_order in order.order_line.filtered(lambda x: x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True ):
                            for line in rec1.order_line:
                                rec2 = sale_margin_line_obj.search([('product_id', '=', line_order.product_id.id),('margin_id', '=', rec1.id)], limit=1)
                                if not rec2:
                                    sale_margin_line_obj.create({
                                        'margin_id': rec1.id,
                                        'product_id': line_order.product_id.id,
                                        'product_qty': line_order.product_qty,
                                        'price_subtotal': line_order.price_subtotal,
                                        'margin': line_order.margin
                                    })
                                    rec1.margin += line_order.margin
                                    break
                                else:
                                    rec2.product_qty += line_order.product_qty
                                    rec2.price_subtotal += line_order.price_subtotal
                                    rec2.margin += line_order.margin
                                    rec1.margin += line_order.margin
                                    break
            else:
                for order in orders:
                    rec1 = sale_margin_obj.search([('company_id', '=', order.company_id.id), ('partner_id', '=', order.partner_id.id), ('id', 'in', list_id)], limit=1)
                    if not rec1:
                        sale_margin = sale_margin_obj.create({
                            'partner_id': order.partner_id.id,
                            'company_id': order.company_id.id,
                            'date_order': order.date_order,
                            'title': "Period " + self.start_date.strftime("%B %Y - ") + self.end_date.strftime("%B %Y"),
                            'branch_id': order.branch_id.id,
                            'margin': order.margin,
                        })
                        list_id.append(sale_margin.id)
                        for line in order.order_line.filtered(lambda x: x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True ):
                            lines = sale_margin_line_obj.create({
                                'margin_id': sale_margin.id,
                                'product_id': line.product_id.id,
                                'product_qty': line.product_qty,
                                'price_subtotal': line.price_subtotal,
                                'margin': line.margin,
                                'cost_price': line.purchase_price,
                                'cost_per_warehouse': line.product_qty * line.purchase_price
                                
                            })
                            list_line_id.append(lines.id)
                    else:
                        for line_order in order.order_line.filtered(lambda x: x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True ):
                            for line in rec1.order_line:
                                rec2 = sale_margin_line_obj.search([('product_id', '=', line_order.product_id.id), ('margin_id', '=', rec1.id)], limit=1)
                                if not rec2:
                                    sale_margin_line_obj.create({
                                        'margin_id': rec1.id,
                                        'product_id': line_order.product_id.id,
                                        'product_qty': line_order.product_qty,
                                        'price_subtotal': line_order.price_subtotal,
                                        'margin': line_order.margin
                                    })
                                    rec1.margin += line_order.margin
                                    break
                                else:
                                    rec2.product_qty += line_order.product_qty
                                    rec2.price_subtotal += line_order.price_subtotal
                                    rec2.cost_per_warehouse += line_order.product_qty * line_order.purchase_price
                                    rec2.margin += line_order.margin
                                    rec1.margin += line_order.margin
                                    break


            sale_margin_data = sale_margin_obj.browse(list_id)
            if not self.partner_ids:
                return self.env.ref('equip3_sale_report.sale_margin_report_action2').report_action(sale_margin_data)
            else:
                return self.env.ref('equip3_sale_report.sale_margin_report_action').report_action(sale_margin_data)

        else:
            raise ValidationError(_('There is no order based on your request.'))

    def print_sale_margin_xls_report(self,):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = xlwt.easyxf(
            'font:height 225,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        b1 = xlwt.easyxf('font:bold True;align: horiz left')
        b12 = xlwt.easyxf('font:bold True;align: horiz left;borders: left thin, right thin, top thin, bottom thin')
        bold_right = xlwt.easyxf('align: horiz right')
        center = xlwt.easyxf('font:bold True;align: horiz center;pattern: pattern solid, fore_colour gray25;borders: left thin, right thin, top thin, bottom thin')
        right = xlwt.easyxf('align: horiz right')
        left = xlwt.easyxf('align: horiz left;borders: left thin, right thin, top thin, bottom thin')

        date_start = False
        date_stop = False

        if self.start_date:
            date_start = fields.Datetime.from_string(self.start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.end_date:
            date_stop = fields.Datetime.from_string(self.end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)

        domain = [
            ('date_order', '>=', fields.Date.to_string(date_start)),
            ('date_order', '<=', fields.Date.to_string(date_stop)),
            ("state", 'in', ('sale','done'))
        ]
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))

        if self.partner_ids:
            for partner_id in self.partner_ids:
                if domain:
                    j = 0
                    for i in domain:
                        if i[0] == 'partner_id':
                            domain.pop(j)
                            break
                        j += 1
                domain.append(('partner_id', '=', partner_id.id))
                orders = self.env['sale.order'].sudo().search(domain)
                if orders:
                    user_currency = self.env.company.currency_id
                    worksheet = workbook.add_sheet(u'Sale Margin - %s' % partner_id.name, cell_overwrite_ok=True)
                    worksheet.write_merge(0, 0, 0, 5, "Sale Margin Report", heading_format)
                    text = "Period " + date_start.strftime("%B %Y - ") + date_stop.strftime("%B %Y")
                    worksheet.write_merge(1, 1, 0, 5, text, heading_format)
                    user_tz = self.env.user.tz or pytz.utc
                    local = pytz.timezone(user_tz)

                    total = 0.0
                    products_sold = {}
                    branch = "-"
                    for order in orders:
                        if user_currency != order.pricelist_id.currency_id:
                            total += order.pricelist_id.currency_id.compute(
                                order.amount_total, user_currency)
                        else:
                            total += order.amount_total
                        for line in order.order_line.filtered(lambda x: x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True ):
                            if not line.display_type:
                                margin_per_qty = line.margin / line.product_uom_qty
                                key = (line.product_id, line.price_unit, line.discount, margin_per_qty, line.price_subtotal, line.purchase_price)
                                products_sold.setdefault(key, 0.0)
                                products_sold[key] += line.product_uom_qty
                        branch = order.branch_id.name or "-"

                    worksheet.write(5, 0, "Printed On:", b1)
                    worksheet.write(6, 0, "Customer:", b1)
                    worksheet.write(7, 0, "Company:", b1)
                    worksheet.write(8, 0, "Branch:", b1)

                    worksheet.write(5, 1, fields.Date.to_string(datetime.today()), b1)
                    worksheet.write(6, 1, partner_id.name, b1)
                    worksheet.write(7, 1, order.company_id.name, b1)
                    worksheet.write(8, 1, branch, b1)

                    var = {
                        'products': sorted([{
                            'product_id': product.id,
                            'product_name': product.name,
                            'code': product.default_code,
                            'quantity': qty,
                            'price_unit': price_unit,
                            'discount': discount,
                            'uom': product.uom_id.name,
                            'cost': purchase_price,
                            'subtotal': price_subtotal,
                            'margin': margin * qty
                        } for (product, price_unit, discount, margin, price_subtotal, purchase_price), qty in products_sold.items()], key=lambda l: l['product_name'])
                    }

                    price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')

                    list1 = var.get("products")
                    worksheet.col(0).width = int(25 * 260)
                    worksheet.col(1).width = int(25 * 260)
                    worksheet.col(2).width = int(12 * 260)
                    worksheet.col(3).width = int(14 * 260)
                    worksheet.col(4).width = int(14 * 260)
                    worksheet.col(5).width = int(14 * 260)

                    worksheet.write(12, 0, "Product", center)
                    worksheet.write(12, 1, "Quantity", center)
                    worksheet.write(12, 2, "UoM", center)
                    worksheet.write(12, 3, "Net", center)
                    worksheet.write(12, 4, "Cost", center)
                    worksheet.write(12, 5, "Margin", center)
                    row = 13
                    tot_margin = 0
                    for rec in list1:
                        cost = rec['cost'] * rec['quantity']
                        worksheet.write(row, 0, rec['product_name'], left)
                        worksheet.write(row, 1, "{:0,.2f}".format(rec['quantity']), left)
                        if rec['uom'] != 'Unit(s)':
                            worksheet.write(row, 2, rec['uom'], left)
                        worksheet.write(row, 3, "{:0,.2f}".format(rec['subtotal']), left)
                        worksheet.write(row, 4, "{:0,.2f}".format(cost), left)
                        worksheet.write(row, 5, "{:0,.2f}".format(rec['margin']), left)
                        tot_margin += rec['margin']
                        row += 1
                    worksheet.write(row, 4, "Margin Total", b12)
                    worksheet.write(row, 5, "{:0,.2f}".format(tot_margin), b12)
                else:
                    raise ValidationError(_('There is no order based on your request.'))
        else:
            orders = self.env['sale.order'].sudo().search(domain)
            if orders:
                user_currency = self.env.company.currency_id
                worksheet = workbook.add_sheet(u'Sale Margin', cell_overwrite_ok=True)
                worksheet.write_merge(0, 0, 0, 5, "Sale Margin Report", heading_format)
                text = "Period " + date_start.strftime("%B %Y - ") + date_stop.strftime("%B %Y")
                worksheet.write_merge(1, 1, 0, 5, text, heading_format)
                user_tz = self.env.user.tz or pytz.utc
                local = pytz.timezone(user_tz)

                total = 0.0
                products_sold = {}
                branch = "-"
                for order in orders:
                    if user_currency != order.pricelist_id.currency_id:
                        total += order.pricelist_id.currency_id.compute(
                            order.amount_total, user_currency)
                    else:
                        total += order.amount_total
                    for line in order.order_line.filtered(lambda x: x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True ):
                        if not line.display_type:
                            key = (line.product_id, line.price_unit, line.discount, line.margin, line.price_subtotal, line.purchase_price)
                            products_sold.setdefault(key, 0.0)
                            products_sold[key] += line.product_uom_qty
                    branch = order.branch_id.name or "-"

                worksheet.write(5, 0, "Printed On:", b1)
                worksheet.write(6, 0, "Company:", b1)
                worksheet.write(7, 0, "Branch:", b1)

                worksheet.write(5, 1, fields.Date.to_string(datetime.today()), b1)
                worksheet.write(6, 1, order.company_id.name, b1)
                worksheet.write(7, 1, branch, b1)

                var = {
                    'products': sorted([{
                        'product_id': product.id,
                        'product_name': product.name,
                        'code': product.default_code,
                        'quantity': qty,
                        'price_unit': price_unit,
                        'discount': discount,
                        'uom': product.uom_id.name,
                        'cost': purchase_price,
                        'subtotal': price_subtotal,
                        'margin': margin * qty
                    } for (product, price_unit, discount, margin, price_subtotal, purchase_price), qty in products_sold.items()], key=lambda l: l['product_name'])
                }
                list1 = var.get("products")
                worksheet.col(0).width = int(25 * 260)
                worksheet.col(1).width = int(25 * 260)
                worksheet.col(2).width = int(12 * 260)
                worksheet.col(3).width = int(14 * 260)
                worksheet.col(4).width = int(14 * 260)
                worksheet.col(5).width = int(14 * 260)

                worksheet.write(12, 0, "Product", center)
                worksheet.write(12, 1, "Quantity", center)
                worksheet.write(12, 2, "UoM", center)
                worksheet.write(12, 3, "Net", center)
                worksheet.write(12, 4, "Cost", center)
                worksheet.write(12, 5, "Margin", center)
                row = 13
                tot_margin = 0
                for rec in list1:
                    cost = rec['cost'] * rec['quantity']
                    worksheet.write(row, 0, rec['product_name'], left)
                    worksheet.write(row, 1, "{:0,.2f}".format(rec['quantity']), left)
                    if rec['uom'] != 'Unit(s)':
                        worksheet.write(row, 2, rec['uom'], left)
                    worksheet.write(row, 3, "{:0,.2f}".format(rec['subtotal']), left)
                    worksheet.write(row, 4, "{:0,.2f}".format(cost), left)
                    worksheet.write(row, 5, "{:0,.2f}".format(rec['margin']), left)
                    tot_margin += rec['margin']
                    row += 1
                worksheet.write(row, 4, "Margin Total", b12)
                worksheet.write(row, 5, "{:0,.2f}".format(tot_margin), b12)
            else:
                raise ValidationError(_('There is no order based on your request.'))
        filename = ('Sale Margin Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sales.margin.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        return{
            'type': 'ir.actions.act_window',
            'name': 'Sales Margin Report',
            'res_id': export_id.id,
            'res_model': 'sales.margin.xls',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

class SaleOrderReport(models.Model):
    _inherit = 'sale.order.report'



    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_id = fields.Many2one("res.company", string="Company", required=True, readonly=True, default=lambda self: self.env.company.id, domain=domain_company)
    company_ids = fields.Many2many(
        'res.company', string='Companies', domain=domain_company)

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

    def get_product(self):
        product_detail = []
        date_start = False
        date_stop = False
        if self.start_date:
            date_start = fields.Datetime.from_string(self.start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.end_date:
            date_stop = fields.Datetime.from_string(self.end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        if self.start_date and self.end_date:
            if len(self.company_ids.ids) >= 1:
                self._cr.execute('''select pt.name as product_name,
                                        so.date_order as order_date,
                                        sum(sl.product_uom_qty) as sold_cnt
                                        from sale_order as so 
                                        left join sale_order_line as sl on so.id = sl.order_id
                                        left join product_product as pr on pr.id = sl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date(%s) and date(date_order) <= date(%s) and so.state in ('sale','done') and so.company_id in %s
                                        group by pt.name,so.date_order''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop), tuple(self.company_ids.ids)))
                product_detail = self._cr.dictfetchall()
            else:
                self._cr.execute('''select pt.name as product_name,
                                        so.date_order as order_date,
                                        sum(sl.product_uom_qty) as sold_cnt
                                        from sale_order as so 
                                        left join sale_order_line as sl on so.id = sl.order_id
                                        left join product_product as pr on pr.id = sl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date(%s) and date(date_order) <= date(%s) and so.state in ('sale','done')
                                        group by pt.name,so.date_order''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop)))
                product_detail = self._cr.dictfetchall()
            output_data = {}
            data_list = []
            final_list = []
            if len(product_detail) > 0:
                current_product = product_detail[0]['product_name']
                last_product = product_detail[-1]['product_name']
                count = 1
                for product_dic in product_detail:
                    if product_dic['sold_cnt'] == None:
                        product_dic['sold_cnt'] = 0
                    if product_dic['product_name'] != current_product:
                        data_list.append(output_data)
                        output_data = {}
                        current_product = product_dic['product_name']
                        output_data['product'] = current_product
                        output_data['monday'] = None
                        output_data['tuesday'] = None
                        output_data['wednesday'] = None
                        output_data['thursday'] = None
                        output_data['friday'] = None
                        output_data['saturday'] = None
                        output_data['sunday'] = None

                        order_date = product_dic['order_date']
                        if order_date.weekday() == 0:
                            output_data['monday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 1:
                            output_data['tuesday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 2:
                            output_data['wednesday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 3:
                            output_data['thursday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 4:
                            output_data['friday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 5:
                            output_data['saturday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 6:
                            output_data['sunday'] = int(
                                product_dic['sold_cnt'])
                        if product_dic['product_name'] == last_product:
                            data_list.append(output_data)

                    else:
                        if count == 1:
                            count = 0
                            output_data = {}
                            current_product = product_dic['product_name']
                            output_data['product'] = current_product
                            order_date = product_dic['order_date']
                            output_data['monday'] = None
                            output_data['tuesday'] = None
                            output_data['wednesday'] = None
                            output_data['thursday'] = None
                            output_data['friday'] = None
                            output_data['saturday'] = None
                            output_data['sunday'] = None

                            if order_date.weekday() == 0:
                                output_data['monday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 1:
                                output_data['tuesday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 2:
                                output_data['wednesday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 3:
                                output_data['thursday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 4:
                                output_data['friday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 5:
                                output_data['saturday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 6:
                                output_data['sunday'] = int(
                                    product_dic['sold_cnt'])
                        else:
                            output_data['product'] = current_product
                            order_date = product_dic['order_date']
                            if order_date.weekday() == 0:
                                tmp = output_data['monday'] or 0
                                output_data['monday'] = tmp + \
                                                        int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 1:
                                tmp = output_data['tuesday'] or 0
                                output_data['tuesday'] = tmp + \
                                                         int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 2:
                                tmp = output_data['wednesday'] or 0
                                output_data['wednesday'] = tmp + \
                                                           int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 3:
                                tmp = output_data['thursday'] or 0
                                output_data['thursday'] = tmp + \
                                                          int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 4:
                                tmp = output_data['friday'] or 0
                                output_data['friday'] = tmp + \
                                                        int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 5:
                                tmp = output_data['saturday'] or 0
                                output_data['saturday'] = tmp + \
                                                          int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 6:
                                tmp = output_data['sunday'] or 0
                                output_data['sunday'] = tmp + \
                                                        int(product_dic['sold_cnt'])

                            if product_dic['product_name'] == last_product:
                                data_list.append(output_data)
            for data in data_list:
                if data not in final_list:
                    final_list.append(data)
            return final_list
