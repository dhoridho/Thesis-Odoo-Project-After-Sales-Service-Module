from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _inherit = 'base'


    @api.model
    def web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False,
                       lazy=True, expand=False, expand_limit=None, expand_orderby=False):
        filter_obj = self.env['ir.filters']
        count = 0

        if isinstance(domain, list):
            for dom in domain:
                if dom and isinstance(dom, list) and dom[0] not in ['|', '&'] and len(dom) == 3:
                    field_name = dom[0]
                    value_field = dom[2]

                    # Waiting approval SO
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'sale.order':
                        approver_obj = self.env['approval.matrix.sale.order.lines']
                        state_approval = ['draft','pending']
                        data_approver = approver_obj.sudo().search([('user_name_ids.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approver_state','in',state_approval)])
                        if data_approver:
                            rec_ids = data_approver.mapped('order_id').filtered(lambda x: self.env.user.id in x.approved_matrix_ids.filtered(lambda o: o.approver_state in state_approval)[0].user_name_ids.ids and x.state in ['waiting_for_approval','waiting_for_over_limit_approval']).ids
                            domain[count] = ('id', 'in', rec_ids)

                    # Waiting approval PO
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'purchase.order':
                        approver_obj = self.env['approval.matrix.purchase.order.line']
                        state_approval = ['draft','pending']
                        data_approver = approver_obj.sudo().search([('user_ids.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approver_state','in',state_approval)])
                        if data_approver:
                            rec_ids = data_approver.mapped('order_id').filtered(lambda x: self.env.user.id in x.approved_matrix_ids.filtered(lambda o: o.approver_state in state_approval)[0].user_ids.ids and x.state in ['over_budget_approval','to_approve','waiting_for_approve']).ids
                            domain[count] = ('id', 'in', rec_ids)


                    # Waiting approval PR
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'purchase.request':
                        approver_obj = self.env['approval.matrix.purchase.request.line']
                        state_approval = ['draft','pending']
                        data_approver = approver_obj.sudo().search([('user_ids.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approver_state','in',state_approval)])
                        if data_approver:
                            rec_ids = data_approver.mapped('request_id').filtered(lambda x: self.env.user.id in x.approved_matrix_ids.filtered(lambda o: o.approver_state in state_approval)[0].user_ids.ids and x.state in ['over_budget_approval','to_approve']).ids
                            domain[count] = ('id', 'in', rec_ids)


                    # Waiting approval Account.move
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'account.move':
                        approver_obj = self.env['approval.matrix.accounting.lines']
                        state_approval = [False,'draft','pending']
                        data_approver = approver_obj.sudo().search([('user_ids.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approver_state','in',state_approval)])
                        if data_approver:
                            rec_ids = data_approver.mapped('move_id').filtered(lambda x: self.env.user.id in x.approved_matrix_ids.filtered(lambda o: o.approver_state in state_approval)[0].user_ids.ids and x.state in ['to_approve']).ids
                            domain[count] = ('id', 'in', rec_ids)


                    # Waiting approval product.supplierinfo
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'product.supplierinfo':
                        approver_obj = self.env['product.supplierinfo.approval']
                        data_approver = approver_obj.sudo().search([('user_ids.id','=',self.env.user.id),('user_approved_ids','not in',[self.env.user.id]),('approved','=',False)])
                        if data_approver:
                            rec_ids = data_approver.mapped('supplier_id').filtered(lambda x: self.env.user.id in x.approval_ids.filtered(lambda o: not o.approved)[0].user_ids.ids and  x.state in ['waiting_approval']).ids
                            domain[count] = ('id', 'in', rec_ids)


                    # Waiting approval Stock.picking
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'stock.picking':
                        rec_ids = []
                        
                        rn_approver_obj = self.env['rn.approval_matrix_line']
                        rn_data_approver = rn_approver_obj.sudo().search([('approver.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approved','=',False)])
                        if rn_data_approver:
                            rec_ids += rn_data_approver.mapped('picking_id').filtered(lambda x: self.env.user.id in x.approved_matrix_ids.filtered(lambda o: not o.approved)[0].approver.ids and  x.state in ['waiting_for_approval']).ids

                        do_approver_obj = self.env['do.approval_matrix_line']
                        do_data_approver = do_approver_obj.sudo().search([('approver.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approved','=',False)])
                        if do_data_approver:
                            rec_ids += do_data_approver.mapped('picking_id').filtered(lambda x: self.env.user.id in x.do_approved_matrix_ids.filtered(lambda o: not o.approved)[0].approver.ids and  x.state in ['waiting_for_approval']).ids


                        domain[count] = ('id', 'in', rec_ids)

                count+=1


                
        return super(Base, self).web_read_group(domain, fields, groupby, limit, offset, orderby,
                       lazy, expand, expand_limit, expand_orderby)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        filter_obj = self.env['ir.filters']
        count = 0

        if isinstance(domain, list):
            for dom in domain:
                if dom and isinstance(dom, list) and dom[0] not in ['|', '&'] and len(dom) == 3:
                    field_name = dom[0]
                    value_field = dom[2]

                    # Waiting approval SO
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'sale.order':
                        approver_obj = self.env['approval.matrix.sale.order.lines']
                        state_approval = ['draft','pending']
                        data_approver = approver_obj.sudo().search([('user_name_ids.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approver_state','in',state_approval)])
                        if data_approver:
                            rec_ids = data_approver.mapped('order_id').filtered(lambda x: self.env.user.id in x.approved_matrix_ids.filtered(lambda o: o.approver_state in state_approval)[0].user_name_ids.ids and x.state in ['waiting_for_approval','waiting_for_over_limit_approval']).ids
                            domain[count] = ('id', 'in', rec_ids)

                    # Waiting approval PO
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'purchase.order':
                        approver_obj = self.env['approval.matrix.purchase.order.line']
                        state_approval = ['draft','pending']
                        data_approver = approver_obj.sudo().search([('user_ids.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approver_state','in',state_approval)])
                        if data_approver:
                            rec_ids = data_approver.mapped('order_id').filtered(lambda x: self.env.user.id in x.approved_matrix_ids.filtered(lambda o: o.approver_state in state_approval)[0].user_ids.ids and x.state in ['over_budget_approval','to_approve','waiting_for_approve']).ids
                            domain[count] = ('id', 'in', rec_ids)


                    # Waiting approval PR
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'purchase.request':
                        approver_obj = self.env['approval.matrix.purchase.request.line']
                        state_approval = ['draft','pending']
                        data_approver = approver_obj.sudo().search([('user_ids.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approver_state','in',state_approval)])
                        if data_approver:
                            rec_ids = data_approver.mapped('request_id').filtered(lambda x: self.env.user.id in x.approved_matrix_ids.filtered(lambda o: o.approver_state in state_approval)[0].user_ids.ids and x.state in ['over_budget_approval','to_approve']).ids
                            domain[count] = ('id', 'in', rec_ids)


                    # Waiting approval Account.move
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'account.move':
                        approver_obj = self.env['approval.matrix.accounting.lines']
                        state_approval = [False,'draft','pending']
                        data_approver = approver_obj.sudo().search([('user_ids.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approver_state','in',state_approval)])
                        if data_approver:
                            rec_ids = data_approver.mapped('move_id').filtered(lambda x: self.env.user.id in x.approved_matrix_ids.filtered(lambda o: o.approver_state in state_approval)[0].user_ids.ids and x.state in ['to_approve']).ids
                            domain[count] = ('id', 'in', rec_ids)


                    # Waiting approval product.supplierinfo
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'product.supplierinfo':
                        approver_obj = self.env['product.supplierinfo.approval']
                        data_approver = approver_obj.sudo().search([('user_ids.id','=',self.env.user.id),('user_approved_ids','not in',[self.env.user.id]),('approved','=',False)])
                        if data_approver:
                            rec_ids = data_approver.mapped('supplier_id').filtered(lambda x: self.env.user.id in x.approval_ids.filtered(lambda o: not o.approved)[0].user_ids.ids and  x.state in ['waiting_approval']).ids
                            domain[count] = ('id', 'in', rec_ids)


                    # Waiting approval Stock.picking
                    if field_name == 'x_is_include_filter_pending_my_approval' and self._name == 'stock.picking':
                        rec_ids = []
                        
                        rn_approver_obj = self.env['rn.approval_matrix_line']
                        rn_data_approver = rn_approver_obj.sudo().search([('approver.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approved','=',False)])
                        if rn_data_approver:
                            rec_ids += rn_data_approver.mapped('picking_id').filtered(lambda x: self.env.user.id in x.approved_matrix_ids.filtered(lambda o: not o.approved)[0].approver.ids and  x.state in ['waiting_for_approval']).ids

                        do_approver_obj = self.env['do.approval_matrix_line']
                        do_data_approver = do_approver_obj.sudo().search([('approver.id','=',self.env.user.id),('approved_users','not in',[self.env.user.id]),('approved','=',False)])
                        if do_data_approver:
                            rec_ids += do_data_approver.mapped('picking_id').filtered(lambda x: self.env.user.id in x.do_approved_matrix_ids.filtered(lambda o: not o.approved)[0].approver.ids and  x.state in ['waiting_for_approval']).ids


                        domain[count] = ('id', 'in', rec_ids)

                count+=1


                
        return super(Base, self).search_read(domain, fields, offset, limit, order)