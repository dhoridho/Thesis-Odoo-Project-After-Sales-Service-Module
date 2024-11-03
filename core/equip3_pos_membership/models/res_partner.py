from odoo import api, models, fields, _
from datetime import datetime


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _default_pos_loyalty_type(self):
        default = False
        try:
            default = self.env.ref('equip3_pos_membership.pos_loyalty_category_default')
        except Exception as e:
            default = False
            
        if default:
            return default.id
        return False

    is_pos_member = fields.Boolean('POS Member')
    pos_loyalty_point_import = fields.Float(
        'Loyalty Points Import',
        default=0,
        help='Admin system can import point for this customer')
    pos_loyalty_point = fields.Float(
        digits=(16, 0),
        compute="_get_point",
        string='Member Points',
        help='Total point of customer can use reward program of pos system', store=True)
    pos_loyalty_type = fields.Many2one(
        'pos.loyalty.category', 
        default=_default_pos_loyalty_type,
        string='Member type',
        help='Customer type of loyalty program')
    pos_loyalty_point_ids = fields.One2many(
        'pos.loyalty.point',
        'partner_id',
        'Point Histories')
    order_count = fields.Integer(compute='_compute_order_count')
    pos_loyalty_point_available = fields.Float(
        digits=(16, 2),
        compute='_get_point_available',
        string='Member Points (Available)',
        help='''Total point of customer can use reward program of pos system, 
        related to Member Type Coefficient Ratio''')

    @api.model
    def default_get(self, fields):
        context = self._context
        rec = super(ResPartner, self).default_get(fields)
        if context.get('ctx_membership'):
            rec['company_id'] = self.env.user.company_id.id
            rec['is_vendor'] = False
            rec['is_customer'] = True
        return rec

    def _compute_order_count(self):
        orders_data = self.env['pos.order'].read_group([('partner_id', '=', self.id)], ['partner_id'], ['partner_id'])
        data = {order_data['partner_id'][0]: order_data['partner_id_count'] for order_data in orders_data}
        for rec in self:
            rec.order_count = data.get(rec.id, 0)
            
    @api.depends('pos_loyalty_point_import')
    def _get_point(self):
        for partner in self:
            partner.pos_loyalty_point = partner.pos_loyalty_point_import
            for loyalty in partner.pos_loyalty_point_ids:
                if loyalty.state == 'ready':
                    if loyalty.type in ['plus','import']:
                        partner.pos_loyalty_point += loyalty.point - loyalty.redeemed_point
                    if loyalty.type in ['void', 'return']:
                        partner.pos_loyalty_point -= loyalty.point

            partner.upgrade_member_type()

    def _get_point_available(self):
        for partner in self:
            coefficient = 1
            if partner.pos_loyalty_type:
                coefficient = partner.pos_loyalty_type.coefficient
            point = partner.pos_loyalty_point * coefficient
            partner.pos_loyalty_point_available = point

    def upgrade_member_type(self):
        member_types = self.env['pos.loyalty.category'].search([])
        for partner in self:
            current_type = partner.pos_loyalty_type
            new_type = current_type
            for index, member_type in enumerate(member_types):
                if (index + 1) == len(member_types):
                    if partner.pos_loyalty_point >= member_type.to_point:
                        new_type = member_type

                if member_type.from_point <= partner.pos_loyalty_point <= member_type.to_point:
                    new_type = member_type

            if current_type and new_type and current_type.id != new_type.id:
                partner.pos_loyalty_type = new_type
        return True

    def action_view_order(self):
        return {
            'name': _('Orders'),
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('point_of_sale.view_pos_order_tree_no_session_id').id, 'tree'),
                (self.env.ref('point_of_sale.view_pos_pos_form').id, 'form'),
                ],
            'type': 'ir.actions.act_window',
            'domain': [('partner_id', '=', self.id)],
        }

    def recharge_point(self, vals):
        self.write({ 'pos_loyalty_point_import': int(vals.get('pos_loyalty_point_import', 0) or  0) })
        return {
            'pos_loyalty_point': self.pos_loyalty_point
        }

    def get_partner_barcode(self, create_date=None):
        barcode = create_date or datetime.now().strftime('%Y%m%d')
        barcode += self.env['ir.sequence'].sudo().get('pos.member.barcode') or ''
        return barcode

    def get_selected_group_member_to_print(self):
        partners = []
        for partner in self:
            if partner.pos_loyalty_type:
                barcode_bg = ''
                qr_bg = ''
                no_bg_qr = False
                no_bg_bar = False

                if not partner.pos_loyalty_type.card_template_barcode:
                    barcode_bg = f'/equip3_pos_membership/static/src/img/White-Background.png'
                    no_bg_bar = True
                elif partner.pos_loyalty_type.card_template_barcode:
                    barcode_bg = f'/web/image?model=pos.loyalty.category&field=card_template_barcode&id={partner.pos_loyalty_type.id}'


                if not partner.pos_loyalty_type.card_template_qrcode:
                    qr_bg = f'equip3_pos_membership/static/src/img/White-Background.png'
                    no_bg_qr = True
                elif partner.pos_loyalty_type.card_template_qrcode:
                    qr_bg = f'/web/image?model=pos.loyalty.category&field=card_template_qrcode&id={partner.pos_loyalty_type.id}'


                partners += [{
                    'name': partner.name,
                    'barcode': partner.barcode,
                    'barcode_background_url': f'{barcode_bg}',
                    'barcode_url': f'/report/barcode?type=Code128&value={partner.barcode}&width=600&height=120&humanreadable=1',
                    'qrcode_background_url': f'{qr_bg}',
                    'qrcode_url': f'/report/barcode?type=QR&value={partner.barcode}&width=400&height=400',
                    'no_bg_bar': no_bg_bar,
                    'no_bg_qr': no_bg_qr,
                }]
                
        chunk = 2
        partners = [partners[x:x+chunk] for x in range(0, len(partners), chunk)]
        return partners
