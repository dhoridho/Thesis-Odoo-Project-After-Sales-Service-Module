odoo.define('equip3_pos_membership.order', function (require) {
"use strict";

    const models = require('point_of_sale.models');
    const core = require('web.core');
    const _t = core._t;
    const rpc = require('pos.rpc');
    const utils = require('web.utils');
    const round_pr = utils.round_precision;
    const {Gui} = require('point_of_sale.Gui');

    let _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            this.reward_coefficient = false;
            this.build_plus_point_rules = false;
            this.customer_deposit_id = false;

            _super_Order.initialize.apply(this, arguments);
        },
        init_from_JSON: function (json) {
            _super_Order.init_from_JSON.apply(this, arguments);
            
            if (json.build_plus_point_rules) {
                this.build_plus_point_rules = json.build_plus_point_rules;
            }
            if (json.customer_deposit_id) {
                this.customer_deposit_id = json.customer_deposit_id;
            }
        },
        export_as_JSON: function() {
            var json = _super_Order.export_as_JSON.call(this);

            if (this.build_plus_point_rules) {
                json.build_plus_point_rules = this.build_plus_point_rules;
            }
            if (this.customer_deposit_id) {
                json.customer_deposit_id = this.customer_deposit_id;
            }
            return json;
        },
        get_won_points: function () {
            if (!this.pos.config.loyalty_id) {
                return 0
            } else {
                return _super_Order.get_won_points.call(this);
            }
        },
        get_new_points() {
            if (!this.pos.config.loyalty_id) {
                return 0
            } else {
                return _super_Order.get_new_points.call(this);
            }
        },
        get_order_amount_without_loyalty(){
            let amount = 0;
            let lines = this.orderlines.models;
            if (lines.length != 0 && lines) {
                for (var i = lines.length - 1; i >= 0; i--) {
                    if (!lines[i].is_product_redeemed) {
                        amount += lines[i].get_price_with_tax();
                    }
                }
            }
            return amount;
        },

        get_rounding(type, multiplier, value){
            if(type == 'Down') {
                value = Math.floor(value)
                if (multiplier){
                   value = Math.floor(value / parseFloat(multiplier)) * parseFloat(multiplier);
                }
            }
            if(type == 'Up') {
                value = Math.ceil(value)
                if (multiplier){
                   value = Math.ceil(value / parseFloat(multiplier)) * parseFloat(multiplier);
                }
            }
            if(type == 'Half Up') {
                value = Math.round(value)
                if (multiplier){
                   value = Math.round(value / parseFloat(multiplier)) * parseFloat(multiplier);
                }
            }
            return value;
        },
        
        get_plus_point_rounding(amount){
            let company = this.pos.company;
            if(company.membership_pluspoint_rounding){
                if(company.membership_pluspoint_rounding_type && company.membership_pluspoint_rounding_multiplier){
                    return this.get_rounding(
                            company.membership_pluspoint_rounding_type, 
                            company.membership_pluspoint_rounding_multiplier, 
                            amount);
                }
            }
            return amount;
        },

        calculate_point_for_product_category(rules, lines){
            let order_amount = this.get_order_amount_without_loyalty();
            let total_point = 0;
            for (let j = 0; j < lines.length; j++) {
                let line = lines[j];
                for (let i = 0; i < rules.length; i++) {
                    let rule = rules[i];
                    let plus_point = line.get_price_with_tax() * rule['coefficient'];

                    let is_type_products = (rule['type'] == 'products' && rule['product_ids'].indexOf(line.product['id']) != -1 && (order_amount>=rule.min_amount) );
                    let is_type_categories = (rule['type'] == 'categories' && JSON.parse(rule['categories'].indexOf(line.product.pos_categ_id[0])) != -1 && (order_amount>=rule.min_amount) );

                    if (is_type_products || is_type_categories) {
                        // if(this.pos.config.loyalty_combine_promotion){
                        //     line.plus_point += plus_point;
                        // }else{
                        //     line.plus_point = plus_point;
                        // }
                        plus_point = this.get_plus_point_rounding(plus_point);
                        total_point += plus_point;
                    }
                }
            }
            return total_point;
        },

        calculate_point_for_total_amount(rules, lines){
            let order_amount = this.get_order_amount_without_loyalty();
            let total_point = 0;

            rules = rules.filter((r)=> order_amount >= r.min_amount );

            let rules_A = rules.filter((r)=> r.calc_point_without_point_as_payment == false);
            if(rules_A.length){
                for (var i = rules_A.length - 1; i >= 0; i--) {
                    let rule = rules_A[i];
                    let plus_point = order_amount * rule.coefficient;
                    plus_point = this.get_plus_point_rounding(plus_point);
                    total_point += plus_point;
                }
            }

            let rules_B = rules.filter((r)=> r.calc_point_without_point_as_payment == true);
            if(rules_B.length){
                let redeem_point = lines.reduce((acc, curr) => { if(curr.is_product_redeemed){  return acc + curr.redeem_point } return acc }, 0);
                for (var i = rules_B.length - 1; i >= 0; i--) {
                    let rule = rules_B[i];
                    let plus_point = order_amount * rule.coefficient;
                    if(redeem_point != 0){
                        plus_point = (order_amount - redeem_point) * rule.coefficient;
                    }
                    plus_point = this.get_plus_point_rounding(plus_point);
                    total_point += plus_point;
                }
            }

            return total_point;
        },

        build_plus_point: function () {
            let client = this.get_client();
            let client_loyalty_category = this.pos.loyalty_category[client.pos_loyalty_type[0]];

            let total_point = 0;
            let lines = this.orderlines.models;
            if (lines.length == 0 || !lines) {
                return total_point;
            }
            let loyalty = this.pos.retail_loyalty;
            if (!loyalty || !this.pos.rules_by_loyalty_id) {
                return total_point;
            }

            let start_date = moment(loyalty.start_date, 'YYYY-MM-DD HH:mm:ss');
            let end_date = loyalty.end_date;
            let today = moment(moment().utc().format('YYYY-MM-DD HH:mm:ss'), 'YYYY-MM-DD HH:mm:ss');
            let is_expired = true;
            if(end_date){
                end_date = moment(loyalty.end_date, 'YYYY-MM-DD HH:mm:ss');
                if(start_date < today && today < end_date){
                    is_expired = false;
                }
            }else{
                if(today > start_date){
                    is_expired = false;
                }
            }
            if(is_expired){
                return total_point;
            }

            let rules = [];
            let rules_by_loyalty_id = this.pos.rules_by_loyalty_id[loyalty.id];
            var filterednames = rules_by_loyalty_id.filter(function(obj) {
                return (obj.pos_loyalty_category_ids['name'] === client_loyalty_category['name']);
            });
            if (!rules_by_loyalty_id) {
                return total_point;
            }
            for (let j = 0; j < rules_by_loyalty_id.length; j++) {
                if ( rules_by_loyalty_id[j].pos_loyalty_category_ids.includes(client_loyalty_category['id']) == true ) {
                    rules.push(rules_by_loyalty_id[j]);
                }
            }
            if (!rules) {
                return total_point;
            }
            if (rules.length) {

                for (let j = 0; j < lines.length; j++) { // TODO: reset plus point each line
                    lines[j].plus_point = 0;
                }

                // Type: Selected Product, Selected Category
                let product_and_category_rules = rules.filter((r) => ['products', 'categories'].includes(r['type']) == true);
                if(product_and_category_rules.length){
                    total_point += this.calculate_point_for_product_category(product_and_category_rules, lines);
                }

                // Type: Total Amount
                let total_amount_rules = rules.filter((r) => ['order_amount'].includes(r['type']) == true);
                if(total_amount_rules.length){
                    total_point += this.calculate_point_for_total_amount(total_amount_rules, lines);
                }

            }

            //store rules in pos.order
            this.build_plus_point_rules = rules.map((r)=>r.id);

            return total_point;
        },
        build_redeem_point: function () {
            let client = this.get_client();
            var reco = this.reward_coefficient;
            let coefficient = 1;
            let client_loyalty_category = this.pos.loyalty_category[client.pos_loyalty_type[0]];
            // if(client_loyalty_category){
            //     coefficient = client_loyalty_category.coefficient;
            // }
            if(reco){
                // coefficient = client_loyalty_category.coefficient;
                coefficient = reco['redeem_coefficient'];
            }


            let redeem_point = 0;
            let lines = this.orderlines.models;
            if (lines.length == 0 || !lines) {
                return redeem_point;
            }
            for (let i = 0; i < lines.length; i++) {
                let line = lines[i];

                if (!line.reward_id) {
                    continue
                } else {
                    let rewardSelected = this.pos.reward_by_id[line.reward_id]
                    if (!rewardSelected){
                        rewardSelected = this.pos.redeem_product_id[line.reward_id]
                    }

                    let redeemPoint = 0
                    if (rewardSelected.type == 'use_point_payment') {
                        redeemPoint = line.price * line.quantity / coefficient;
                    } else if (rewardSelected.type == 'gift') {
                        redeemPoint = line.quantity * line.redeem_point;
                    } else if (line.redeem_point) {
                        redeemPoint = line.redeem_point;
                    }
                    if (redeemPoint < 0) {
                        redeemPoint = -redeemPoint
                    }
                    line.redeem_point = redeemPoint
                    redeem_point += line.redeem_point
                }
            }
            let rounding = 1;
            if(redeem_point.toString().indexOf('.') == 1){
                return redeem_point;
            }
            return round_pr(redeem_point || 0, rounding);
        },
        get_client_points: function () {
            let client = this.get_client();
            if (!client) {
                return {
                    redeem_point: 0,
                    plus_point: 0,
                    pos_loyalty_point: 0,
                    remaining_point: 0,
                    next_point: 0,
                    client_point: 0
                }
            }
            let redeem_point = this.build_redeem_point();
            let plus_point = this.build_plus_point();

            let rounding_down = 0;
            if(this.pos.retail_loyalty){
                rounding_down = this.pos.retail_loyalty.rounding_down;
            }
            if (rounding_down) {
                plus_point = parseInt(plus_point);
            }
            
            let pos_loyalty_point = client.pos_loyalty_point || 0;
            let remaining_point = pos_loyalty_point - redeem_point;
            let next_point = pos_loyalty_point - redeem_point + plus_point;
            return {
                redeem_point: redeem_point,
                plus_point: plus_point,
                pos_loyalty_point: pos_loyalty_point,
                remaining_point: remaining_point,
                next_point: next_point,
                client_point: pos_loyalty_point,
            }
        }, 
        async setRewardProgram(reward) { 
            let loyalty = this.pos.loyalty_type_redeem;
            let product = this.pos.db.get_product_by_id(loyalty.product_loyalty_id[0]);
            if (!product) {
                let resultUpdate = await this.pos.rpc({
                    model: 'product.product',
                    method: 'force_write',
                    args: [[loyalty.product_loyalty_id[0]], {
                        'available_in_pos': true,
                        'sale_ok': true,
                        'active': true,
                    }],
                    context: {}
                })
                if (resultUpdate) {
                    await this.pos.syncProductsPartners();
                } else {
                    return Gui.showPopup('ErrorPopup', {
                        title: _t('Error'),
                        body: loyalty.product_loyalty_id[1] + _t(' not set Available In POS, it not possible apply Reward.')
                    })
                }
            }
            if(!product){
                product = this.pos.db.get_product_by_id(loyalty.product_loyalty_id[0]);
            }
            if(!product){
                return Gui.showPopup('ErrorPopup', {
                        title: _t('Error'),
                        body: _t('Product Reward Service ') + loyalty.product_loyalty_id[1] + _t(' not set Available In POS, it not possible apply Reward.')
                });
            }
            this.orderlines.models.forEach(l => {
                if (l.product && l.product.id == product['id']) {
                    this.remove_orderline(l);
                }
            });
            this.orderlines.models.forEach(l => {
                if (l.is_product_redeemed) {
                    this.remove_orderline(l);
                }
            });
            //remove tax
            product['taxes_id'] = [];
            let applied = false;
            let lines = this.orderlines.models;
            if (lines.length == 0 && reward['type'] != 'gift') {
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Warning'),
                    body: _t('Your order is blank cart'),
                })
            }
            let total_with_tax = this.get_total_with_tax();

            this.reward_coefficient = reward;

            let redeem_point_used = this.build_redeem_point();
            let client = this.get_client();

            let coefficient = 1;
            let client_loyalty_category = this.pos.loyalty_category[client.pos_loyalty_type[0]];
            if(reward){
                // coefficient = client_loyalty_category.coefficient;
                coefficient = reward['redeem_coefficient'];
            }

            if (reward['min_amount'] > total_with_tax) {
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Warning'),
                    body: 'Reward ' + reward['name'] + ' required min amount bigger than ' + reward['min_amount'],
                })
            }

            if (client['pos_loyalty_point'] <= redeem_point_used) {
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Warning'),
                    body: _t('Point of customer not enough'),
                })
            }
            if ((reward['type'] == 'discount_products' || reward['type'] == 'discount_categories') && (reward['discount'] <= 0 || reward['discount'] > 100)) {
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Warning'),
                    body: _t('Reward discount required set discount bigger or equal 0 and smaller or equal 100')
                })
            }
            if (reward['type'] == 'discount_products') {
                let point_redeem = 0;
                let amount_total = 0;
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    if (reward['discount_product_ids'].indexOf(line['product']['id']) != -1) {
                        amount_total += line.get_price_with_tax();
                    }
                }
                let point_will_redeem = amount_total * reward['discount'] / 100 / coefficient //reward['coefficient']
                let price_discount = amount_total * reward['discount'] / 100;



                if ((client['pos_loyalty_point'] <= (point_will_redeem + redeem_point_used)) && price_discount) {
                    return Gui.showPopup('ErrorPopup', {
                    title: _t('Warning'),
                    body: _t('Point of customer not enough'),
                    })
                } else if ((client['pos_loyalty_point'] > (point_will_redeem + redeem_point_used)) && price_discount) {
                    applied = true;
                    this.add_product(product, {
                        price: price_discount,
                        quantity: -1,
                        merge: false,
                        extras: {
                            reward_id: reward.id,
                            redeem_point: point_will_redeem,
                            is_product_redeemed: true, 
                        }
                    });
                    this.update_redeem_values();
                    return Gui.showPopup('ConfirmPopup', {
                        title: _t('Successfully'),
                        body: _t('Set Discount: ') + this.pos.format_currency(price_discount),
                        cancelText: ''
                    })
                }
            } else if (reward['type'] == 'discount_categories') {
                let point_redeem = 0;
                let amount_total = 0;
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];

                    if (reward['discount_category_ids'].indexOf(line['product']['pos_categ_id'][0]) != -1) {
                        amount_total += line.get_price_with_tax();
                    }
                    else if (reward['discount_child_category_ids'].indexOf(line['product']['pos_categ_id'][0]) != -1) {
                        amount_total += line.get_price_with_tax();
                    }
                }
                let point_will_redeem = amount_total * reward['discount'] / 100 / coefficient //reward['coefficient']
                let price_discount = amount_total * reward['discount'] / 100;
                if ((client['pos_loyalty_point'] <= (point_will_redeem + redeem_point_used)) && price_discount) {
                    return Gui.showPopup('ErrorPopup', {
                        title: _t('Warning'),
                        body: _t('Point of customer not enough'),
                    })
                } else if ((client['pos_loyalty_point'] > (point_will_redeem + redeem_point_used)) && price_discount) {
                    applied = true;
                    this.add_product(product, {
                        price: price_discount,
                        quantity: -1,
                        merge: false, 
                        extras: {
                            reward_id: reward.id,
                            redeem_point: point_will_redeem,
                            is_product_redeemed: true, 
                        }
                    });
                    this.update_redeem_values();
                    return Gui.showPopup('ConfirmPopup', {
                        title: _t('Successfully'),
                        body: _t('Set Discount: ') + this.pos.format_currency(price_discount),
                        cancelText: '',
                    })
                }
            } else if (reward['type'] == 'resale' && reward['price_resale'] > 0) {
                let point_redeem = 0;
                let amount_total = 0;
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    if (reward['resale_product_ids'].indexOf(line['product']['id']) != -1) {
                        amount_total += (line.get_price_with_tax() / line.quantity - reward['price_resale']) * line.quantity;
                    }
                }
                let point_will_redeem = amount_total * reward['redeem_coefficient'] //reward['coefficient']
                if (client['pos_loyalty_point'] > (point_will_redeem + redeem_point_used)) {
                    applied = true;
                    this.add_product(product, {
                        price: amount_total,
                        quantity: -1,
                        merge: false, 
                        extras: {
                            reward_id: reward.id,
                            redeem_point: point_will_redeem, 
                            is_product_redeemed: true, 
                        }
                    });
                    this.update_redeem_values();
                    return Gui.showPopup('ConfirmPopup', {
                        title: _t('Successfully'),
                        body: _t('Set Discount: ') + this.pos.format_currency(amount_total),
                        cancelText: '',
                    })
                }
            } else if (reward['type'] == 'use_point_payment') {
                let subtitle = 1 / coefficient + _t(' points = 1 ') 
                    + this.pos.currency['name'] 
                    + ',<br/>'
                    + _t('Customer have total Points: ') 
                    + this.pos.format_currency_no_symbol(client['pos_loyalty_point']) 
                    + _t(' and Total Amount of Order is: ') + this.pos.format_currency(this.get_total_with_tax()) 
                    + '. '
                    + _t('Please input points Customer need use bellow');
                let pointCanUse = client['pos_loyalty_point'];
                let allPointCanUse = client['pos_loyalty_point'] * coefficient;
                if (total_with_tax <= allPointCanUse) {
                    pointCanUse = total_with_tax / coefficient;
                }
                let {confirmed, payload: point} = await this.pos.chrome.showPopup('ReChargePointPopup', {
                    title: reward.name,
                    subtitle: subtitle,
                    startingValue: pointCanUse
                })
                if (confirmed) {
                    point = parseFloat(point);
                    let redeem_point_used = this.build_redeem_point();
                    let next_redeem_point = redeem_point_used + point;
                    if (point <= 0) {
                        let {confirmed, payload: confirm} = await Gui.showPopup('ConfirmPopup', {
                            title: _t('Warning'),
                            body: _t('Points redeem required bigger than 0, are you want input points again ?')
                        })
                        if (confirmed) {
                            return await this.setRewardProgram(reward);
                        } else {
                            return false;
                        }
                    }
                    if (client['pos_loyalty_point'] < next_redeem_point) {
                        let {confirmed, payload: confirm} = await Gui.showPopup('ConfirmPopup', {
                            title: _t('Error'),
                            body: _t("It not Possible Redeem Points Bigger than Customer's Points. Are you want re-input points again ?")
                        })
                        if (confirmed) {
                            return await this.setRewardProgram(reward);
                        } else {
                            return false;
                        }
                    } else {
                        let next_amount = total_with_tax - (point * coefficient);
                        var redeem_point = point;
                        if (next_amount >= 0) {
                            applied = true;
                            this.add_product(product, {
                                price: -(point * coefficient),
                                quantity: 1,
                                merge: false, 
                                extras: {
                                    reward_id: reward.id,
                                    redeem_point: redeem_point,
                                    is_product_redeemed: true, 
                                },
                                description: _t('Use ') + point * coefficient + _t(' points payment.')
                            });
                            this.update_redeem_values();
                            return Gui.showPopup('ConfirmPopup', {
                                title: _t('Successfully'),
                                body: _t('Covert ') + point + _t(' Points to : ') + this.pos.format_currency(point * coefficient),
                                cancelText: '',
                            })
                        } else {
                            let {confirmed, payload: confirm} = await Gui.showPopup('ConfirmPopup', {
                                title: _t('Warning'),
                                body: _t('Total points can use require smaller than or equal :') + this.pos.format_currency_no_symbol(total_with_tax / coefficient),
                            })
                            if (confirmed) {
                                return await this.setRewardProgram(reward);
                            } else {
                                return false;
                            }
                        }
                    }
                }
            }
        },
        async setRedeemedProduct(product_gift, reward) {
            let loyalty = this.pos.loyalty_type_redeem;
            let product = this.pos.db.get_product_by_id(loyalty.product_loyalty_id[0]);
            if (!product) {
                let resultUpdate = await this.pos.rpc({
                    model: 'product.product',
                    method: 'force_write',
                    args: [[loyalty.product_loyalty_id[0]], {
                        'available_in_pos': true,
                        'sale_ok': true,
                        'active': true,
                    }],
                    context: {}
                })
                if (resultUpdate) {
                    await this.pos.syncProductsPartners();
                } else {
                    return Gui.showPopup('ErrorPopup', {
                        title: _t('Error'),
                        body: loyalty.product_loyalty_id[1] + _t(' not set Available In POS, it not possible apply Reward.')
                    });
                }
            }
            if(!product){
                product = this.pos.db.get_product_by_id(loyalty.product_loyalty_id[0]);
            }
            if(!product){
                return Gui.showPopup('ErrorPopup', {
                        title: _t('Error'),
                        body: _t('Product Reward Service ') + loyalty.product_loyalty_id[1] + _t(' not set Available In POS, it not possible apply Reward.')
                });
            }
            this.orderlines.models.forEach(l => {
                if (l.product && l.product.id == product['id']) {
                    this.remove_orderline(l);
                }
            });
            this.orderlines.models.forEach(l => {
                if (l.is_product_redeemed) {
                    this.remove_orderline(l);
                }
            });
            //remove tax
            product['taxes_id'] = [];
            let applied = false;
            let lines = this.orderlines.models;
            if (lines.length == 0 && reward['type'] != 'gift') {
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Warning'),
                    body: _t('Your order is blank cart'),
                })
            }
            let total_with_tax = this.get_total_with_tax();
            let redeem_point_used = this.build_redeem_point();
            let client = this.get_client();

            let coefficient = 1;
            let client_loyalty_category = this.pos.loyalty_category[client.pos_loyalty_type[0]];
            // if(client_loyalty_category){
            //     coefficient = client_loyalty_category.coefficient;
            // }
            if(reward['redeem_coefficient']){
                // coefficient = client_loyalty_category.coefficient;
                coefficient = reward['redeem_coefficient'];
            }

            if (reward['min_amount'] > total_with_tax) {
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Warning'),
                    body: 'Redeem Product ' + product_gift.display_name 
                        + ' required min amount bigger than ' 
                        + reward['min_amount'],
                })
            }
            if (client['pos_loyalty_point'] <= redeem_point_used) {
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Warning'),
                    body: _t('Point of customer not enough'),
                })
            }

            let redeem_point = 0;
            if(this.pos.redeem_product){
                let rule = this.pos.redeem_product[0].gift_product_rule.find((r)=>r.product_id[0] == product_gift.id);
                if(rule){
                    redeem_point = rule.redeem_point;
                }
            }
            if (product_gift) { 
                if (client['pos_loyalty_point'] > (redeem_point + redeem_point_used)) {
                    applied = true;
                    this.add_product(product_gift, {
                        price: 0,
                        quantity: reward['quantity'],
                        merge: false, 
                        extras: { 
                            reward_id: reward.id,
                            redeem_point: redeem_point,
                            is_product_redeemed: true, 
                        }
                    });

                    this.update_redeem_values();
                    return Gui.showPopup('ConfirmPopup', {
                        title: _t('Successfully'),
                        body: _t('Set Gift: ') + product_gift.display_name,
                        cancelText: '',
                    });
                }
            }
        },
        update_redeem_values(){
            let points = this.get_client_points();
            this.plus_point = points['plus_point'];
            this.redeem_point = points['redeem_point'];
            this.remaining_point = points['remaining_point'];
        },
        _get_plus_point: function () {
            let rounding_down = 0;
            let rounding = 1;
            if (this.pos.retail_loyalty) {
                rounding_down = this.pos.retail_loyalty.rounding_down;
                rounding = this.pos.retail_loyalty.rounding;
            }
            if (rounding_down) {
                return parseInt(this.plus_point);
            } else {
                return round_pr(this.plus_point, rounding);
            }
        },

        checking_promotion_has_groups: function (promo) {
            let res =  _super_Order.checking_promotion_has_groups.call(this, promo);
            if (promo.pos_loyalty_category) {
                let client = this.get_client();
                if (client && client.pos_loyalty_type && promo.pos_loyalty_category_ids.length) {
                    if (promo.pos_loyalty_category_ids.includes(client.pos_loyalty_type[0])) {
                        return true;
                    }
                }
                return false;
            }
            return res;
        },
    });

});