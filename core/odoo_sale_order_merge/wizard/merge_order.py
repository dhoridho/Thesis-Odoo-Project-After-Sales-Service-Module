# -*- coding: utf-8 -*-
# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models ,_
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class MergeOrderWizard(models.TransientModel):
    _name = 'sale.order.merge.wizard'
    _description = 'MergeOrderWizard'


    order_merge_type = fields.Selection(
        selection=[
            ('create_new', 'Merge With New Sale Order'),
            ('update_existing', 'Merge With Selected Sale order'),
        ],
        string="Merge As",
        required=True,
        default="create_new",
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        default=lambda self:self._context.get('active_ids'),
    )
    
    @api.onchange("order_merge_type")
    def _onchange_merge_type(self):
        domain_dict = {'domain': {'sale_order_id': [('id', 'in', self._context.get('active_ids'))]}}
        return domain_dict

    # @api.multi #odoo13
    def merge_sale_order(self):
        sale_order = self.env['sale.order'].browse(self._context.get('active_ids'))

        if any([sale.state not in ['draft', 'sent'] for sale in sale_order]):
            raise UserError("Sale order must be in draft or sent state")
        if len(sale_order.mapped("partner_id"))  > 1:
            raise UserError("All the sale order's Partner should be same")

        sale_order_id = self.env['sale.order']
        clone = self.env['sale.order']
        merge_so_ids = sale_order.ids

        if self.order_merge_type == 'create_new':
            for sale in sale_order:
                for line in sale.order_line:
                    order_lines = sale.order_line.filtered(lambda fline:fline.product_id == line.product_id and fline.price_unit == line.price_unit)
                    if len(order_lines) > 1:
                        raise UserError("It seems you have sale order with same product two/more times on same sales order")
                if sale_order_id:
                    continue
                if sale.state in ('draft', 'sent'):
                    origin_ref = ', '.join(sale_order.mapped("name"))
                    origin_id = {
                            'origin': origin_ref,
                    }
                    clone = sale.copy(origin_id)
                    merge_so_ids.append(clone.id) 
                    sale_order_id = sale
            order_lines = sale_order.mapped("order_line")
            matrix_lines = sale_order.mapped("approved_matrix_ids")

            if clone and sale_order_id:
                for line in order_lines:
                    if line.order_id.id == sale_order_id.id:
                        continue
                    clone_line_ids = clone.order_line.filtered(lambda l: l.product_id == line.product_id and l.price_unit == line.price_unit)
                    if clone_line_ids:
                        clone_line_ids.product_uom_qty += line.product_uom_qty
                    else:
                        default = {
                                'order_id': clone.id,
                                }
                        duplicate = line.copy(default).id

                for mline in matrix_lines:
                    if mline.order_id.id == sale_order_id.id:
                        continue
                    clone_mline_ids = clone.approved_matrix_ids.filtered(lambda l: l.user_name_ids == mline.user_name_ids and l.approval_type == mline.approval_type)
                    if clone_mline_ids:
                        clone_mline_ids.minimum_approver = mline.minimum_approver
                    else:
                        default = {
                                'order_id': clone.id,
                                }
                        duplicate = mline.copy(default).id
                # sale_order.write({'state': 'cancel'})
                for sale_rec in sale_order:
                    sale_rec.write({'state': 'cancel', 'sale_state': 'cancel', 'is_quotation_cancel': True})

        elif self.order_merge_type == 'update_existing':
            clone = self.sale_order_id
            sale_order_id = self.sale_order_id
            order_lines = sale_order.mapped("order_line")
            matrix_lines = sale_order.mapped("approved_matrix_ids")
            so_merge = False
            for line in order_lines:
                    if line.order_id.id == sale_order_id.id:
                        continue
                    clone_line_ids = clone.order_line.filtered(lambda l: l.product_id == line.product_id and l.price_unit == line.price_unit)
                    if clone_line_ids:
                        clone_line_ids.product_uom_qty += line.product_uom_qty
                        so_merge = True
                    else:
                        default = {
                                'order_id': clone.id,
                                }
                        duplicate = line.copy(default).id
                        so_merge = True

            for mline in matrix_lines:
                    if mline.order_id.id == sale_order_id.id:
                        continue
                    clone_mline_ids = clone.approved_matrix_ids.filtered(lambda l: l.user_name_ids == mline.user_name_ids and l.approval_type == mline.approval_type)
                    if clone_mline_ids:
                        clone_mline_ids.minimum_approver = mline.minimum_approver
                        so_merge = True
                    else:
                        default = {
                                'order_id': clone.id,
                                }
                        duplicate = mline.copy(default).id
                        so_merge = True

            if so_merge:
                active_sale_order = self.env['sale.order'].browse(self._context.get('active_ids'))
                merged_sale_order_ids = active_sale_order.filtered(lambda sale:sale.id != sale_order_id.id)
                origin_ref = ', '.join(merged_sale_order_ids.mapped("name"))
                sale_order_id.write({'origin': origin_ref})
                # merged_sale_order_ids.write({'state': 'cancel'})
                for sale_rec in merged_sale_order_ids:
                    sale_rec.write({'state': 'cancel', 'sale_state': 'cancel', 'is_quotation_cancel': True})

        so_action = self.env.ref("sale.action_quotations_with_onboarding").read()[0]
        so_action['domain'] = [('id', 'in', merge_so_ids)]
        return so_action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:   
