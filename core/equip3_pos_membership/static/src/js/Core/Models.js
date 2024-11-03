odoo.define('equip3_pos_membership.model', function (require) {
    const models = require('point_of_sale.models');
    const pos_general_models = require('equip3_pos_general.models');
    const utils = require('web.utils');
    const core = require('web.core');
    const _t = core._t;
    const session = require('web.session');
    
    models.load_fields('product.template', ['is_gift_product']);
    models.load_fields('product.product', ['is_gift_product']);
    models.load_fields('pos.receipt.template', ['is_receipt_member_info']);


    models.load_fields('pos.payment.method', ['is_deposit_payment']);
    models.load_fields('res.company', [
        'membership_pluspoint_rounding',
        'membership_pluspoint_rounding_type',
        'membership_pluspoint_rounding_multiplier', 
        'is_pos_use_deposit',
    ]);
    
    const _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            let self = this;
            let loyalty_rule_model = this.get_model('loyalty.rule');
            if (loyalty_rule_model) {
                loyalty_rule_model.condition = function (self) {
                    if (self.config.pos_loyalty_ids) {
                        return false
                    } else {
                        if (self.config.module_pos_loyalty && self.config.loyalty_id) {
                            return true
                        } else {
                            return false
                        }
                    }
                }
            }
            
            let loyalty_reward_model = this.get_model('loyalty.reward');
            if (loyalty_reward_model) {
                loyalty_reward_model.condition = function (self) { 
                    if (self.config.pos_loyalty_ids) {
                        return false
                    } else {
                        if (self.config.module_pos_loyalty && self.config.loyalty_id) {
                            return true
                        } else {
                            return false
                        }
                    }
                }
            }

            let partnerModel = this.get_model('res.partner');
            if(partnerModel){
                partnerModel.fields.push(
                    'pos_loyalty_point',
                    'pos_loyalty_type',
                    'is_pos_member',
                    'pos_branch_id',
                );
            }

            let posPromotion = this.get_model('pos.promotion');
            if(posPromotion){
                posPromotion.fields.push(
                    'pos_loyalty_category',
                    'pos_loyalty_category_ids',
                );
            }

            _super_PosModel.initialize.call(this, session, attributes);
        },

        async getCustomerDepositFromBackend() {
            let self = this;
            let domain = [['partner_id','!=',false], ['partner_id.is_pos_member','=',true]];
            let write_date = this.db.customer_deposit_last_write_date;
            if(write_date){
                domain.push(['write_date','>', write_date]);
            }

            let model = self.get_model('customer.deposit');
            let params = {
                model: 'customer.deposit',
                fields: model.fields,
                domain: domain,
            }

            let datas = await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context']);
            this.db.save_customer_deposits(datas)

            this.alert_message({
                title: _t('Syncing'),
                body: _t('Customer Deposit')
            })
        },
    });
});