from odoo import models,fields,api,_
from odoo.exceptions import UserError
from datetime import datetime


class InheritSO(models.Model):
    _inherit = 'sale.order'

    is_dropship = fields.Boolean(string='Is Dropship', default=False, readonly=True, states={'draft': [('readonly', False)]})
    purchase_request_ids = fields.One2many(comodel_name='purchase.request', inverse_name='so_id', string='Purchase Requests')
    purchase_request_count = fields.Integer(string='Purchase Request Count', compute="_compute_purchase_request_count")
    
    @api.depends('purchase_request_ids')
    def _compute_purchase_request_count(self):
        for i in self:
            i.purchase_request_count = i.purchase_request_ids and len(i.purchase_request_ids) or 0

    def sh_create_po_from_so(self):
        """
            this method fire the action and open create purchase order wizard
        """
        view = self.env.ref('equip3_sale_purchase.purchase_order_wizard_view_form')
        context = dict(self.env.context or {})
        context.update({
            'default_so_id':self.id,
            'so_id':self.id,
            'default_is_dropship':self.is_dropship,
        })
        return {
            'name': 'Create Purchase Order',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    def action_confirm(self):
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
            
        if self.is_dropship:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            self.write(self._prepare_confirmation_values())
            self.write({'date_confirm': datetime.today()})
            self.write({'sale_state': 'in_progress'})
            keep_name_so = IrConfigParam.get_param('keep_name_so', False)
            if not keep_name_so:
                if self.origin:
                    self.origin += "," + self.name
                else:
                    self.origin = self.name
                self.name = self.env['ir.sequence'].next_by_code('sale.quotation.order')
            return True
        else:
            return super(InheritSO,self).action_confirm()

    def sh_action_view_purchase_request(self):
        return {
            'name': _("Purchase Request's"),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.purchase_request_ids.ids)],
            'target': 'current',
        }


    def action_view_delivery(self):
        if self.is_dropship:
            action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
            pickings = self.env['stock.picking'].sudo().search([('sale_id','=',self.id)])
            if len(pickings) > 1:
                action['domain'] = [('id', 'in', pickings.ids)]
            elif pickings:
                form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
                if 'views' in action:
                    action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
                else:
                    action['views'] = form_view
                action['res_id'] = pickings.id
            # Prepare the context.
            picking_id = pickings.filtered(lambda l: l.location_dest_id.usage == 'customer')
            if picking_id:
                picking_id = picking_id[0]
            else:
                picking_id = pickings[0]
            action['context'] = dict(self._context, default_partner_id=self.partner_id.id, default_picking_type_id=picking_id.picking_type_id.id, default_origin=self.name, default_group_id=picking_id.group_id.id)
            return action
        else:
            return super(InheritSO,self).action_view_delivery()