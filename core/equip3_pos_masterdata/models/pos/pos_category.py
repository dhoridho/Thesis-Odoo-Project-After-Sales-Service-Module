# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.osv import expression



class POSCategory(models.Model):
    _inherit = "pos.category"

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100): 
        domain = []
        if ' / ' in name:
            for i, n in enumerate(name.split(' / ')[::-1]):
                if i == 0:
                    child_domain = [('name', operator, n)]
                else:
                    child_domain = [('.'.join(['parent_id'] * i), operator, n)]
                domain = expression.AND([domain, child_domain])
        else:
            name = name.replace('/', '').strip()
            domain = ['|', ('name', operator, name), ('parent_id', operator, name)]

        domain = expression.AND([args, domain])
        res = self.search(domain, limit=limit).name_get()
        return res

    is_category_combo = fields.Boolean(
        'Is Combo Category',
        help='If it checked, \n'
             'When Pop-Up combo items show on POS Screen\n'
             'Pop-Up Only show POS Categories have Is Combo Category checked'
    )
    sale_limit_time = fields.Boolean('Sale Limit Time')
    from_time = fields.Float('Not allow sale from Time')
    to_time = fields.Float('Not allow sale To Time')
    submit_all_pos = fields.Boolean('Applied all Point Of Sale')
    pos_branch_ids = fields.Many2many(
        'res.branch',
        'pos_category_branch_rel',
        'categ_id',
        'branch_id',
        string='Applied Branches')
    pos_config_ids = fields.Many2many(
        'pos.config',
        'pos_category_config_rel',
        'categ_id',
        'config_id',
        string='Point Of Sale Applied')
    category_type = fields.Selection([
        ('fnb', 'FnB'),
        ('retail', 'Retail')
    ],
        default='fnb',
        string='Category Type',
        help='If selected is [Main Course] when add new products to cart, will skip and not send to Kitchen \n'
             'Else if selected is [FnB] , always send to kitchen when waiters/cashier click to Order button \n'
             'When your waiters ready to send [Main Course] products to kitchen \n'
             '. Them can click to button send Main Course'
    )
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)
