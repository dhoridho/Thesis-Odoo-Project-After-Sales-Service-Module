from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from datetime import date
from odoo.exceptions import ValidationError
from lxml import etree

class productProductExpenseExtend(models.Model):
    _inherit = 'product.product'
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(productProductExpenseExtend, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.context.get('default_can_be_expensed'):
            if  self.env.user.has_group('hr_expense.group_hr_expense_user'):
                root = etree.fromstring(res['arch'])
                root.set('create', 'true')
                root.set('edit', 'true')
                root.set('delete', 'true')
                res['arch'] = etree.tostring(root)
            else:
                root = etree.fromstring(res['arch'])
                root.set('create', 'false')
                root.set('edit', 'false')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)
            
        return res