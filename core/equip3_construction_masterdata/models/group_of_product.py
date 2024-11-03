from dataclasses import field

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from lxml import etree


class GroupOfProduct(models.Model):
    _name = 'group.of.product'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Group of Product"
    _rec_name = 'complete_name'
    _order = 'complete_name'

    active = fields.Boolean(string='Active', default=True)
    name = fields.Char('Name', tracking=True)
    complete_name = fields.Char('Complete Name', compute='_compute_name', store=True)
    cons_use_code = fields.Boolean('Use Code', compute='_compute_name', store=False)
    cost_code = fields.Char('Cost Code', tracking=True)

    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company, readonly=True)
    product_ids = fields.Many2many('product.template', 'product_gop_rel', 'gop_id', 'product_template_id', string='Products')
    branch_id = fields.Many2one('res.branch', string='Branch', tracking=True,
                                default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids),
                                                     ('company_id', '=', self.env.company.id)])
    created_by = fields.Many2one("res.users", string="Created By", default=lambda self: self.env.uid, readonly=True)
    created_date = fields.Date("Creation Date", default=fields.Date.today, readonly=True)
            
    @api.depends('name')
    def _compute_name(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        cons_use_code = IrConfigParam.get_param('cons_use_code')
        for record in self:
            record.cons_use_code = cons_use_code
            if cons_use_code and record.name:
                record.complete_name = '%s - %s' % (record.cost_code, record.name)
            else:
                record.complete_name = '%s' % (record.name or '')

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(GroupOfProduct, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        root = etree.fromstring(res['arch'])
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_engineer'):
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        return res

# depracated
# dont use this table, gonna erase in future
class ProductLine(models.Model):
    _name = 'product.line'
    _description = 'GoP Products Related'

    gop_id = fields.Many2one('group.of.product', string='Product Line ID')
    product_id = fields.Many2one('product.product', string='Product Name')
    sales_price = fields.Float(string='Sales Price')
    standard_price = fields.Float(string='Cost')
    last_purchase_price = fields.Float(string='Last Purchase Price')
    qty_available = fields.Float(string='Quantity on Hand')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
