from odoo import models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def button_immediate_upgrade(self):
        res = super(IrModuleModule, self).button_immediate_upgrade()

        if self.name in ["equip3_pos_membership"]:
            self.env['res.partner'].search([('is_pos_member','=',True),('pos_loyalty_point','<',0)])._get_point()
            self.env.cr.execute("""
                SELECT rp.id,  ip.value_text FROM res_partner AS rp
                LEFT JOIN ir_property AS ip
                    ON ip.res_id = CONCAT('res.partner,', rp.id) AND ip.name = 'barcode'
                WHERE rp.is_pos_member = 't' AND ip.value_text IS NULL;
            """)
            partner_ids = [x[0] for x in self.env.cr.fetchall()]
            if partner_ids:
                partners = self.env['res.partner'].sudo().search([('id','in',partner_ids),('barcode','=',False)])
                for partner in partners:
                    create_date = partner.create_date and partner.create_date.strftime('%Y%m%d') or False
                    partner.write({
                        'barcode': partner.get_partner_barcode(create_date)
                    })
        return res
