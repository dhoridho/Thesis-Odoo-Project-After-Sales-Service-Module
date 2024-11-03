odoo.define('equip3_pos_membership.load_models', function (require) {
"use strict";

    const models = require('point_of_sale.models');
    const exports = {};
    const core = require('web.core');
    const _t = core._t;

    models.load_models([
        {
            model: 'pos.loyalty',
            fields: [
                'name', 
                'product_loyalty_id', 
                'rounding', 
                'rounding_down', 
                'start_date', 
                'end_date','type'
            ],
            condition: function (self) {
                return self.config.pos_loyalty_ids;
            },
            domain: function (self) {
                let current_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                console.log('LOADED pos.loyalty is after or equal to: ', current_date)
                return ['|', ['end_date','>=', current_date], ['end_date','=', false], ['id', 'in', self.config.pos_loyalty_ids], ['state', '=', 'running']];
            },
            loaded: function (self, data) {
                let loyalties = [];
                self.loyalty_type_plus_point = data.find((d)=>d.type == 'plus point');
                self.loyalty_type_redeem = data.find((d)=>d.type == 'redeem');

                if(self.loyalty_type_plus_point){
                    loyalties.push(self.loyalty_type_plus_point);
                }
                if(self.loyalty_type_redeem){
                    loyalties.push(self.loyalty_type_redeem);
                }
                if (loyalties.length > 0) {
                    self.retail_loyalty = loyalties[0];
                    self.retail_loyalty['rewards'] = [] // todo: supported EE version if install pos_loyalty
                } else {
                    self.retail_loyalty = false;
                }
            }
        }, 
        {
            model: 'pos.loyalty.category',
            fields: [
                'name', 
                'code', 
                'coefficient', 
            ],
            condition: function (self) {
                return self.config.pos_loyalty_ids;
            },
            domain: function (self) {
                return [];
            },
            loaded: function (self, data) {
                self.loyalty_category = {};
                for (var i = data.length - 1; i >= 0; i--) {
                    self.loyalty_category[data[i].id] = data[i];
                }
            }
        }, 
        {
            model: 'pos.loyalty.rule',
            fields: [
                'name',
                'loyalty_id',
                'coefficient',
                'type',
                'product_ids',
                'category_ids',
                'categories',
                'min_amount',
                'is_multi',
                'pos_loyalty_category_ids',
                'calc_point_without_point_as_payment'
            ],
            condition: function (self) {
                return self.loyalty_type_plus_point != undefined;
            },
            domain: function (self) {
                let domain = [['id','=',-1]];
                if(self.loyalty_type_plus_point){
                    domain = [['state','=','running'],['loyalty_id', '=', self.loyalty_type_plus_point.id]];
                }
                return domain;
            },
            loaded: function (self, rules) {
                self.rules = rules;
                self.rule_ids = [];
                self.rule_by_id = {};
                self.rules_by_loyalty_id = {};
                for (let i = 0; i < rules.length; i++) {
                    self.rule_by_id[rules[i].id] = rules[i];
                    self.rule_ids.push(rules[i].id)
                    if (!self.rules_by_loyalty_id[rules[i].loyalty_id[0]]) {
                        self.rules_by_loyalty_id[rules[i].loyalty_id[0]] = [rules[i]];
                    } else {
                        self.rules_by_loyalty_id[rules[i].loyalty_id[0]].push(rules[i]);
                    }
                }
            }
        }, 
        {
            model: 'pos.loyalty.reward.product',
            fields: [
                'gift_reward_id',
                'product_id',
                'redeem_point',
            ],
            domain: function (self) {
                return [['gift_reward_id','!=',false]];
            },
            loaded: function (self, data) {
                self.redeem_product_gift_rule = data;
            }
        }, 
        {
            model: 'pos.loyalty.reward',
            fields: [
                'name',
                'loyalty_id',
                'product_redeem_loyalty_id',
                'reward_redeem_loyalty_id',
                'redeem_point',
                'type',
                'redeem_coefficient',
                'coefficient',
                'discount',
                'discount_product_ids',
                'discount_category_ids',
                'min_amount',
                'gift_product_rule_ids',
                'resale_product_ids',
                'gift_quantity',
                'price_resale',
                'pos_loyalty_category_ids',
                'discount_child_category_ids',
            ],
            condition: function (self) {
                return self.loyalty_type_redeem;
            },
            domain: function (self) {
                let domain = [['id','=',-1]];
                if(self.loyalty_type_redeem){
                    domain = [
                        '|', 
                        ['reward_redeem_loyalty_id', '=', self.loyalty_type_redeem.id], 
                        ['product_redeem_loyalty_id', '=', self.loyalty_type_redeem.id], 
                        ['state', '=', 'running'], 
                        ['coefficient', '>', 0]
                    ];
                }
                return domain;
            },
            loaded: function (self, data) {
                self.rewards = data.filter((r)=>r.type != 'gift');
                self.reward_by_id = {};
                self.rewards_by_loyalty_id = {};
                self.redeem_product = data.filter((r)=>r.type == 'gift');
                self.redeem_product_id = {};

                for (let i = 0; i < self.redeem_product.length; i++) {
                    self.redeem_product[i].gift_product_rule = self.redeem_product_gift_rule.filter((r)=>r.gift_reward_id[0] == self.redeem_product[i].id);
                    self.redeem_product_id[self.redeem_product[i].id] = self.redeem_product[i];
                }

                for (let i = 0; i < self.rewards.length; i++) {
                    self.reward_by_id[self.rewards[i].id] = self.rewards[i];
                    if (!self.rewards_by_loyalty_id[self.rewards[i].loyalty_id[0]]) {
                        self.rewards_by_loyalty_id[self.rewards[i].loyalty_id[0]] = [self.rewards[i]];
                    } else {
                        self.rewards_by_loyalty_id[self.rewards[i].loyalty_id[0]].push([self.rewards[i]]);
                    }
                }
            }
        }, 
        {
            model: 'customer.deposit',
            fields: [
                'write_date',
                'name',
                'partner_id',
                'amount',
                'remaining_amount',
                'communication',
                'state',
                'payment_date',
                'journal_id',
                'deposit_account_id',
                'deposit_reconcile_journal_id',
                'is_from_pos',
            ],
            domain: function (self) {
                return [['partner_id','!=',false], ['partner_id.is_pos_member','=',true]];
            },
            condition: function (self) {
                return self.company.is_pos_use_deposit;
            },
            loaded: function (self, data) {
                self.customer_deposits = data;
                self.customer_deposit_by_id = {};
                for (let i = 0; i < data.length; i++) {
                    self.customer_deposit_by_id[data[i].id] = data[i];
                }
                self.db.save_customer_deposits(data);
            }
        }, 
    ], 
    {
        after: 'pos.config'
    });

    return exports;
});
