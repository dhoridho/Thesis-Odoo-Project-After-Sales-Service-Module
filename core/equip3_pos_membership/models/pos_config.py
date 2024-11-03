# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PosConfig(models.Model):
    _inherit = "pos.config"

    display_point_receipt = fields.Boolean(
        'Display Point / Receipt', help='Active this field for display loyalty\n'
                                        ' point plus on bill receipt')
    pos_loyalty_id = fields.Many2one( 'pos.loyalty', string='Loyalty', domain=[('id', '=', 'running')])
    pos_loyalty_ids = fields.Many2many('pos.loyalty',
        'pos_config_pos_loyalty_rel', 'pos_config_id', 'loyalty_id', 
        string='Loyalties', 
        domain=[('state', '=', 'running')])
    loyalty_combine_promotion = fields.Boolean(
        'Loyalty Combine Promotion',
        help='If checked: allow each order line, loyalty plus point and promotion apply together \n'
             'If not checked: When promotion add to order lines, points will not plus'
    )
    loyalty_redeem_in_pos_screen = fields.Boolean('Redeem in POS Screen')
    is_allow_redeem_in_pos_screen = fields.Boolean(compute='_compute_is_allow_redeem_in_pos_screen')

    is_allow_create_member_in_pos_screen = fields.Boolean(compute='_compute_is_allow_create_member_in_pos_screen')

    customer_deposit_account_id = fields.Many2one('account.account', 
        string='Deposit Account')
    customer_deposit_reconcile_journal_id = fields.Many2one('account.journal', 
        string='Deposit Reconcile Journal')



    def _compute_is_allow_redeem_in_pos_screen(self):
        for rec in self:
            rec.is_allow_redeem_in_pos_screen = False
            if rec.pos_loyalty_ids and rec.loyalty_redeem_in_pos_screen:
                rec.is_allow_redeem_in_pos_screen = True

    def _compute_is_allow_create_member_in_pos_screen(self):
        ConfigParameter = self.env['ir.config_parameter']
        is_allow = ConfigParameter.get_param('base_setup.allow_create_member_in_pos_screen')
        for rec in self:
            rec.is_allow_create_member_in_pos_screen = is_allow and is_allow or False
    
    def write(self, vals):
        res = super(PosConfig, self).write(vals)

        if vals.get('pos_loyalty_ids'):
            point_plus_count = len([x.id for x in self.pos_loyalty_ids if x.type == 'plus point'])
            if point_plus_count > 1:
                raise UserError('You can not set up more than one loyalty program with the type Point Plus!\n\nPOS: ' + str(self.name))

            redeem_count = len([x.id for x in self.pos_loyalty_ids if x.type == 'redeem'])
            if redeem_count > 1:
                raise UserError('You can not set up more than one loyalty program with the type Redeem!\n\nPOS: ' + str(self.name))

        if not self._context.get('action_applied_to_selected_pos') and vals.get('pos_loyalty_ids'):
            for loyalty in self.env['pos.loyalty'].sudo().search([('pos_config_ids','in',self.id)]):
                if loyalty.id not in self.pos_loyalty_ids.ids:
                    loyalty.write({ 'pos_config_ids': [(3, self.id)] })
            for data in self:
                data.action_applied_to_selected_loyalty_pos()

        return res


    @api.model
    def create(self, vals):
        res = super(PosConfig, self).create(vals)
        if not self._context.get('action_applied_to_selected_pos') and vals.get('pos_loyalty_ids'):
            res.action_applied_to_selected_loyalty_pos()
        return res




    def action_applied_to_selected_loyalty_pos(self):
        self.ensure_one()
        for loyalty in self.pos_loyalty_ids:
            if self.id not in loyalty.pos_config_ids.ids:
                loyalty.with_context(action_applied_to_selected_loyalty_pos=True).write({ 'pos_config_ids': [(4, self.id)] })
        return True