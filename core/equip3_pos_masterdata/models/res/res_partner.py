# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
from lxml import etree

class ResPartner(models.Model):
    _inherit = "res.partner"

    discount_id = fields.Many2one(
        'pos.global.discount',
        'Pos discount',
        help='Discount (%) automatic apply for this customer')
    birthday_date = fields.Date('Birthday Date')
    group_ids = fields.Many2many(
        'res.partner.group',
        'res_partner_group_rel',
        'partner_id',
        'group_id',
        string='Groups Name')
    pos_order_ids = fields.One2many(
        'pos.order',
        'partner_id',
        'POS Order')
    pos_total_amount = fields.Float(
        'POS Amount Total',
        help='Total amount customer bought from your shop',
        compute='_getTotalPosOrder')
    pos_partner_type_id = fields.Many2one(
        'res.partner.type',
        string='POS Partner Type',
        compute='_getTotalPosOrder',
        readonly=1)
    pos_branch_id = fields.Many2one(
        'res.branch',
        string = "Branch",
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
        domain=lambda self: [('id', 'in', self.env.branches.ids)])
    special_name = fields.Char('Special Name')

    is_pos_partner = fields.Boolean('Is POS Partner')


    def check_member_is_duplicate(self,name,mobile,phone=False):      
        self.env.cr.execute("""
            SELECT id FROM res_partner
            WHERE replace(name,' ','') ILIKE '%s' and replace(mobile,' ','')  ILIKE '%s'
        """ % (name,mobile))
        res = self.env.cr.fetchall()
        if not res:
            self.env.cr.execute("""
                SELECT id FROM res_partner
                WHERE replace(name,' ','') ILIKE '%s' and replace(phone,' ','')  ILIKE '%s'
            """ % (name,mobile))
            res = self.env.cr.fetchall()
        if not res and phone:
            self.env.cr.execute("""
                SELECT id FROM res_partner
                WHERE replace(name,' ','') ILIKE '%s' and replace(phone,' ','')  ILIKE '%s'
            """ % (name,phone))
            res = self.env.cr.fetchall()
        if not res and phone:
            self.env.cr.execute("""
                SELECT id FROM res_partner
                WHERE replace(name,' ','') ILIKE '%s' and replace(mobile,' ','')  ILIKE '%s'
            """ % (name,phone))
            res = self.env.cr.fetchall()
        return res or False



    @api.depends('pos_order_ids', 'pos_order_ids.amount_total', 'pos_order_ids.state')
    def _compute_customer_credit_limit(self):
        # Depends: 'equip3_sale_other_operation'
        super(ResPartner, self)._compute_customer_credit_limit()

        for record in self:
            credit_usage = 0

            #sale.order
            sale_ids = self.env['sale.order'].search([
                ('partner_id', '=', record.id),
                ('state', '=', 'sale'),
                # ('over_limit_approved','=',False)
            ])
            invoice_ids = sale_ids.invoice_ids
            invoice_amount =  sum(invoice_ids.mapped('amount_total')) - sum(invoice_ids.mapped('amount_residual'))
            credit_usage += sum(sale_ids.mapped('amount_total')) + invoice_amount

            #pos.order
            pos_order_ids = record.pos_order_ids.filtered(lambda l: l.state in ['invoiced', 'partially paid'] and l.is_payment_method_with_receivable)
            credit_usage += sum(pos_order_ids.mapped('amount_total'))

            record.customer_credit_limit = record.cust_credit_limit - credit_usage
       

    def _getTotalPosOrder(self):
        for partner in self:
            partner.pos_total_amount = 0
            for o in partner.pos_order_ids:
                partner.pos_total_amount += o.amount_total
            type_will_add = self.env['res.partner.type'].sudo().get_type_from_total_amount(partner.pos_total_amount)
            if not type_will_add:
                type_will_add = None
            partner.pos_partner_type_id = type_will_add

    def update_branch_to_partner(self, vals):
        for partner in self:
            if not partner.pos_branch_id:
                partner.write(vals)
        return True

    def get_barcode_string(self):
        partner_obj = self.env['res.partner'].sudo()
        barcode_rules = self.env['barcode.rule'].sudo().search([
            ('type', '=', 'client'),
            ('pattern', '!=', '.*'),
        ])
        barcode = None
        if barcode_rules:
            last_id = 1
            partner = partner_obj.search([],limit=1,order='id desc')
            if partner:
                last_id = partner.id + 1 
            format_code = "%s%s%s" % (barcode_rules[0].pattern, last_id, datetime.now().strftime("%d%m%y%H%M"))
            barcode = self.env['barcode.nomenclature'].sanitize_ean(format_code)

        return barcode

    def add_barcode(self):
        barcode_rules = self.env['barcode.rule'].sudo().search([
            ('type', '=', 'client'),
            ('pattern', '!=', '.*'),
        ])
        barcode = None
        if barcode_rules:
            for partner in self:
                format_code = "%s%s%s" % (barcode_rules[0].pattern, partner.id, datetime.now().strftime("%d%m%y%H%M"))
                barcode = self.env['barcode.nomenclature'].sanitize_ean(format_code)
                partner.write({'barcode': barcode})
        return barcode

    @api.model
    def create_from_ui(self, partner):
        if partner.get('birthday_date', None):
            birthday_date = datetime.strptime(partner.get('birthday_date'), "%Y-%m-%d")
            partner.update({'birthday_date': birthday_date})
        if partner.get('property_product_pricelist', False):
            partner['property_product_pricelist'] = int(partner['property_product_pricelist'])
        for key, value in partner.items():
            if value == "false":
                partner[key] = False
            if value == "true":
                partner[key] = True
        
        partner['pos_branch_id'] = False # If create from POS Screen set branch to False
        partner['company_id'] = self.env.company and self.env.company.id or False

        return super(ResPartner, self).create_from_ui(partner)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(ResPartner, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit:
            root = etree.fromstring(res['arch'])
            root.set('edit', 'false')
            res['arch'] = etree.tostring(root)

        if self.env.user.has_group('equip3_pos_masterdata.group_pos_user') and not self.env.user.has_group('equip3_pos_masterdata.group_pos_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)

            
        return res

    @api.model
    def create(self, vals):
        partner = super(ResPartner, self).create(vals)
        if partner.birthday_date and (partner.birthday_date >= fields.Date.context_today(self)):
            raise UserError('Birth date could not bigger than today')

        if not vals.get('barcode') and vals.get('is_pos_member'):
            partner.add_barcode()

        return partner

    def write(self, vals):
        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit and 'active' in vals:
            raise Warning(_("Your user not have permission to archive/active partner.")) 

        res = super(ResPartner, self).write(vals)
        partner_ids = []
        for partner in self:
            partner_ids.append(partner.id)
            if partner.birthday_date and (partner.birthday_date >= fields.Date.context_today(self)):
                raise UserError('Birth date could not bigger than today')

        return res

    def action_view_pos_partner_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['domain'] = [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('partner_id', 'child_of', self.id),
        ]
        action['context'] = {'default_move_type':'out_invoice', 'move_type':'out_invoice', 'journal_type': 'sale', 'search_default_unpaid': 1}
        return action


class ResPartnerGroup(models.Model):
    _name = "res.partner.group"
    _description = "Customers Group/Membership Management"

    name = fields.Char('Name', required=1)
    pricelist_applied = fields.Boolean('Replace Customer PriceList')
    pricelist_id = fields.Many2one(
        'product.pricelist',
        'Pricelist Applied',
        help='When POS cashiers scan membership card on pos screen \n'
             'If customer exist inside this Group, this pricelist will apply to order customer'
    )
    image = fields.Binary('Card Image', required=1)
    height = fields.Integer('Card Image Height', default=120)
    width = fields.Integer('Card Image Width', default=300)

class ResPartnerType(models.Model):
    _name = "res.partner.type"
    _description = "Type of partner, filter by amount total bought from your shops"

    name = fields.Char('Name', required=1)
    from_amount_total_orders = fields.Float('From amount total', help='Min of total amount bought from your shop')
    to_amount_total_orders = fields.Float('To amount total', help='Max of total amount bought from your shop')

    def get_type_from_total_amount(self, amount):
        types = self.search([])
        type_will_add = None
        for type in types:
            if amount >= type.from_amount_total_orders and amount <= type.to_amount_total_orders:
                type_will_add = type.id
        return type_will_add