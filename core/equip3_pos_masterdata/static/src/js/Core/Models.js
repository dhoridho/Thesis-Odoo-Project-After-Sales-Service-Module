odoo.define('equip3_pos_masterdata.model', function (require) {
    const models = require('point_of_sale.models');
    const utils = require('web.utils');
    const core = require('web.core');
    const round_pr = utils.round_precision;
    const _t = core._t;
    const rpc = require('pos.rpc');
    const session = require('web.session');
    const time = require('web.time');
    const Session = require('web.Session');
    const load_model = require('equip3_pos_masterdata.load_models');
    const {Printer} = require('point_of_sale.Printer');
    const {posbus} = require('point_of_sale.utils');
    const {Gui} = require('point_of_sale.Gui');
    var Orderline_super = models.Orderline.prototype;
    models.load_fields('product.product','default_time','is_can_be_po');
    models.load_fields('pos.payment.method', ['is_bank','is_receivables','is_mdr_discount','is_mdr','mdr_paid_by','mdr_intermediary_account_id','able_use_card']);
    models.load_fields('res.company', ['tax_discount_policy']);
    models.load_fields('account.tax', ['company_id']);
    models.load_fields('pos.category', ['id', 'name', 'parent_id', 'child_id', 'write_date']);

    models.load_models({
    model: 'pos.payment.method.mdr',
    fields: ['name','payment_method_id','mdr_type','card_group_ids','card_payment_ids','percentage','surcharge'],
        loaded: function(self,pos_payment_method_mdr){
            self.db.set_pos_payment_method_mdr(pos_payment_method_mdr);
        },
    });
    const _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        async automaticSetCoupon(couponsSelected) {
            this.runningCouponProgram = true
            let couponPromotionNoNeededCode = null
            if (!couponsSelected) {
                couponPromotionNoNeededCode = this.couponProgramsAutomatic.filter(p => p['promo_code_usage'] == "no_code_needed")
            } else {
                couponPromotionNoNeededCode = couponsSelected
            }
            if (couponPromotionNoNeededCode) {
                for (let i = 0; i < couponPromotionNoNeededCode.length; i++) {
                    let couponProgram = couponPromotionNoNeededCode[i];
                    this._removeLineByCouponID(couponProgram['id'])
                    let rule = this.couponRule_by_id[couponProgram.rule_id[0]]
                    let reward = this.couponReward_by_id[couponProgram.reward_id[0]]
                    let canBeApplyCoupon = await this._checkCouponRule(couponProgram, null, rule, reward, true)
                    if (canBeApplyCoupon) {
                        let hasApplied = this._applyCouponReward(couponProgram, null, rule, reward);
                        if (hasApplied) {
                            this.chrome.showNotification(_t('Coupon Program: ') + couponProgram['name'], _t('Added to Order'), 4000)
                        }
                    }
                }
            }
            this.runningCouponProgram = false
        },

        _removeLineByCouponID(couponID) {
            const selectedOrder = this.get_order();
            selectedOrder.orderlines.models.forEach(l => {
                if (l.coupon_program_id && l.coupon_program_id == couponID) {
                    selectedOrder.remove_orderline(l)
                }
            })
            selectedOrder.orderlines.models.forEach(l => {
                if (l.coupon_program_id && l.coupon_program_id == couponID) {
                    selectedOrder.remove_orderline(l)
                }
            })
            selectedOrder.orderlines.models.forEach(l => {
                if (l.coupon_program_id && l.coupon_program_id == couponID) {
                    selectedOrder.remove_orderline(l)
                }
            })
        },

        async _applyCouponReward(program, coupon, rule, reward) {
            const selectedOrder = this.get_order();
            const product = this.db.get_product_by_id(reward.discount_line_product_id[0])
            if (!product) {
                console.warn(reward.discount_line_product_id[1] + ' not available in POS, please set it available in POS back')
                let resultUpdate = await this.rpc({
                    model: 'product.product',
                    method: 'force_write',
                    args: [[reward.discount_line_product_id[0]], {
                        'available_in_pos': true,
                        'sale_ok': true,
                        'active': true,
                    }],
                    context: {}
                })
                if (resultUpdate) {
                    await this.pos.syncProductsPartners();
                } else {
                    return this.pos.alert_message({
                        title: _t('Error'),
                        body: _t('Please check your internet or your Hashmicro Server Offline Mode')
                    })
                }
            }
            let balanceAmountCoupon;
            if (coupon) {
                let couponPrograms = await this.rpc({
                    model: 'coupon.coupon',
                    method: 'search_read',
                    domain: [['id', '=', coupon.id]],
                    fields: [],
                })
                coupon = couponPrograms[0]
                if (!['new', 'sent'].includes(coupon.state) || (coupon['is_gift_card'] && coupon['balance_amount'] <= 0)) {
                    this.chrome.showNotification(coupon.code, _t(', This coupon has already been used or expired. Or Balance Amount is 0'))
                }
                if (coupon.is_gift_card) {
                    balanceAmountCoupon = coupon['balance_amount']
                }
            }
            await this.env.pos.syncProductsPartners();
            let appliedRewardSuccessfully = false;
            if (reward.reward_type == 'discount') { // discount
                let price = 0;
                if (reward.discount_apply_on == 'on_order') { // discount apply on order
                    if (reward.discount_type == 'percentage') {
                        price = selectedOrder.get_total_with_tax() / 100 * reward.discount_percentage
                    } else {
                        price = reward.discount_fixed_amount
                    }
                    if (price > 0 && reward.discount_max_amount > 0 && price > reward.discount_max_amount) {
                        price = reward.discount_max_amount
                    }
                }
                if (reward.discount_apply_on == 'cheapest_product') { // discount apply on cheapest
                    let lineCheapest;
                    selectedOrder.orderlines.models.forEach(l => {
                        if (!lineCheapest || (lineCheapest && lineCheapest.get_price_with_tax() >= l.get_price_with_tax())) {
                            lineCheapest = l
                        }
                    })
                    if (reward.discount_type == 'percentage') {
                        price = lineCheapest.get_price_with_tax() / 100 * reward.discount_percentage
                    } else {
                        price = reward.discount_fixed_amount
                    }
                    if (price > 0 && reward.discount_max_amount > 0 && price > reward.discount_max_amount) {
                        price = reward.discount_max_amount
                    }
                }
                if (reward.discount_apply_on == 'specific_products') { // discount apply on specific products
                    selectedOrder.orderlines.models.forEach(l => {
                        if (reward.discount_specific_product_ids.includes(l.product.id)) {
                            price += l.get_price_with_tax()
                        }
                    })
                    if (reward.discount_type == 'percentage') {
                        price = price / 100 * reward.discount_percentage
                    } else {
                        price = reward.discount_fixed_amount
                    }
                    if (price > 0 && reward.discount_max_amount > 0 && price > reward.discount_max_amount) {
                        price = reward.discount_max_amount
                    }
                }
                let line = new models.Orderline({}, {
                    pos: this,
                    order: selectedOrder,
                    product: product
                });
                if (coupon) {
                    line.coupon_id = coupon.id
                }
                line.coupon_program_id = program.id
                line.coupon_program_name = program.name;
                line.price_manually_set = true; //no need pricelist change, price of promotion change the same, i blocked
                line.set_quantity(-1);
                if (selectedOrder.get_total_with_tax() <= price) {
                    price = selectedOrder.get_total_with_tax()
                }
                if (balanceAmountCoupon && price > balanceAmountCoupon) {
                    price = balanceAmountCoupon
                }
                line.set_unit_price(price);
                selectedOrder.orderlines.add(line);
                selectedOrder.trigger('change', selectedOrder)
                appliedRewardSuccessfully = true;
            } else { // free product
                const reward_product = this.db.get_product_by_id(reward.reward_product_id[0])
                let totalProductsMatchedRuleInCart = 0;
                selectedOrder.orderlines.models.forEach(l => {
                    if (rule.applied_product_ids.includes(l.product.id)) {
                        totalProductsMatchedRuleInCart += l.quantity
                    }
                })
                if (totalProductsMatchedRuleInCart >= rule.rule_min_quantity) {
                    let min_qty = rule.rule_min_quantity || 1
                    let quantity_free = parseInt(totalProductsMatchedRuleInCart / min_qty * reward.reward_product_quantity);
                    let line = new models.Orderline({}, {
                        pos: this,
                        order: selectedOrder,
                        product: reward_product
                    });
                    if (coupon) {
                        line.coupon_id = coupon.id
                    }
                    line.coupon_program_id = program.id
                    line._applyCouponRewardcoupon_program_name = program.name
                    line.price_manually_set = true; //no need pricelist change, price of promotion change the same, i blocked
                    line.set_quantity(quantity_free);
                    line.set_unit_price(0);
                    selectedOrder.orderlines.add(line);
                    selectedOrder.trigger('change', selectedOrder)
                    appliedRewardSuccessfully = true
                }
            }
            return appliedRewardSuccessfully
        },

        async _checkCouponRule(program, coupon, rule, reward, automaticApplied) {
            // TODO: if manual is true, it mean cashier input code direct popup input coupon code
            if (program['promo_code_usage'] == "code_needed" && !automaticApplied) {
                console.log('[_checkCouponRule]: ' + program['name'] + ' code is required !')
                return false
            }
            console.log('[_checkCouponRule]: ' + program['name'])
            let passConditionOfProgram = true
            const rewardDroduct = this.db.get_product_by_id(reward.reward_product_id[0])
            const productDiscount = this.db.get_product_by_id(reward.discount_line_product_id[0])
            if (!rewardDroduct && reward.reward_type != 'discount') {
                const resultUpdate = await this.rpc({
                    model: 'product.product',
                    method: 'force_write',
                    args: [[reward.reward_product_id[0]], {
                        'available_in_pos': true,
                        'sale_ok': true,
                        'active': true,
                    }],
                    context: {}
                })
                if (resultUpdate) {
                    await this.pos.syncProductsPartners();
                } else {
                    return this.pos.alert_message({
                        title: _t('Error'),
                        body: _t('Please check your internet or your Hashmicro Server Offline Mode')
                    })
                }
            }
            if (!productDiscount && reward.reward_type == 'discount') {
                const resultUpdate = await this.rpc({
                    model: 'product.product',
                    method: 'force_write',
                    args: [[reward.discount_line_product_id[0]], {
                        'available_in_pos': true,
                        'sale_ok': true,
                        'active': true,
                    }],
                    context: {}
                })
                if (resultUpdate) {
                    await this.pos.syncProductsPartners();
                } else {
                    return this.pos.alert_message({
                        title: _t('Error'),
                        body: _t('Please check your internet or your Hashmicro Server Offline Mode')
                    })
                }
            }
            const selectedOrder = this.get_order()
            var currency = false
            if(selectedOrder) {
                currency = selectedOrder.currency
            }
            let client = selectedOrder.get_client()
            const currentTime = new Date().getTime()
            const productIdsInCart = selectedOrder.orderlines.models.map(l => l.product.id)
            const productIdsOfRuleExistInCart = rule.applied_product_ids.filter(product_id => productIdsInCart.includes(product_id) == true)
            let errorMessage;
            let couponPrograms = await this.rpc({
                model: 'coupon.program',
                method: 'search_read',
                domain: [['id', '=', program.id]],
                fields: ['pos_order_count', 'active'],
            })
            let totalAmountCompare = selectedOrder.get_total_with_tax();
            let totalTax = selectedOrder.get_total_tax();
            if (rule.rule_minimum_amount_tax_inclusion == "tax_excluded") {
                totalAmountCompare -= totalTax
            }
            if (rule.rule_minimum_amount > 0 && rule.rule_minimum_amount >= totalAmountCompare) {
                errorMessage = this.env._t('Promotion/Coupon have Minimum Purchase Amount Total of Order required bigger than ' + this.format_currency(rule.rule_minimum_amount,false,currency))
                if (!automaticApplied) {
                    this.alert_message({
                        title: this.env._t('Error'),
                        body: errorMessage
                    })
                }
                this.chrome.showNotification(_t('Error'), errorMessage)
                passConditionOfProgram = false
                return false
            }
            if (rule.rule_min_quantity > 0) {
                let totalProductsMatchedRuleInCart = 0;
                selectedOrder.orderlines.models.forEach(l => {
                    if (rule.applied_product_ids.includes(l.product.id)) {
                        totalProductsMatchedRuleInCart += l.quantity
                    }
                })
                if (totalProductsMatchedRuleInCart < rule.rule_min_quantity) {
                    errorMessage = this.env._t('Products add to cart not matching with Products condition of Promotion. Minimum quantity is ' + rule.rule_min_quantity)
                    if (!automaticApplied) {
                        this.alert_message({
                            title: this.env._t('Error'),
                            body: errorMessage
                        })
                    }
                    this.chrome.showNotification(_t('Error'), errorMessage)
                    passConditionOfProgram = false
                    return false
                }
            }
            if (coupon) {
                let coupons = await this.rpc({
                    model: 'coupon.coupon',
                    method: 'search_read',
                    domain: [['id', '=', coupon.id]],
                    fields: ['state', 'expiration_date'],
                })
                if (coupons.length == 0 || (coupons.length > 0 && !['new', 'sent'].includes(coupons[0]['state'])) || (coupons.length > 0 && new Date(coupons[0].expiration_date).getTime() < currentTime)) {
                    errorMessage = this.env._t('Coupon is expired or used before')
                    if (!automaticApplied) {
                        this.alert_message({
                            title: this.env._t('Error'),
                            body: errorMessage
                        })
                    }
                    this.chrome.showNotification(_t('Error'), errorMessage)
                    passConditionOfProgram = false
                    return false
                }
            }
            if (rule.rule_date_from && new Date(rule.rule_date_from).getTime() > currentTime) {
                errorMessage = this.env._t('Start Date of Promotion/Coupon is: ') + rule.rule_date_from + this.env._t(' . Bigger than current Date Time')
                if (!automaticApplied) {
                    this.alert_message({
                        title: this.env._t('Error'),
                        body: errorMessage
                    })
                }
                this.chrome.showNotification(_t('Error'), errorMessage)
                passConditionOfProgram = false
                return false
            }
            if (rule.rule_date_to && new Date(rule.rule_date_to).getTime() < currentTime) {
                errorMessage = this.env._t('Promotion/Coupon Program is Expired at: ' + rule.rule_date_to)
                if (!automaticApplied) {
                    this.alert_message({
                        title: this.env._t('Error'),
                        body: errorMessage
                    })
                }
                this.chrome.showNotification(_t('Error'), errorMessage)
                passConditionOfProgram = false
                return false
            }
            if (program.program_type == 'promotion_program') {  // if promotion program, we required set client
                if (!client && rule.applied_partner_ids.length > 0) {
                    const {confirmed, payload: newClient} = await Gui.showTempScreen(
                        'ClientListScreen',
                        {client: null}
                    );
                    if (confirmed) {
                        selectedOrder.set_client(newClient);
                        client = newClient
                    } else {
                        errorMessage = this.env._t('Customer is Required')
                        if (!automaticApplied) {
                            this.alert_message({
                                title: this.env._t('Error'),
                                body: errorMessage
                            })
                        }
                        this.chrome.showNotification(_t('Error'), errorMessage)
                        return false
                    }
                }
                if (rule.applied_partner_ids.length > 0 && client && !rule.applied_partner_ids.includes(client.id)) {
                    errorMessage = client.display_name + this.env._t(' not inside Based on Customers of Promotion/Coupon')
                    if (!automaticApplied) {
                        this.alert_message({
                            title: this.env._t('Error'),
                            body: errorMessage
                        })
                    }
                    this.chrome.showNotification(_t('Error'), errorMessage)
                    return false
                }
            }
            if (!productIdsInCart) {
                errorMessage = this.env._t('Your cart is blank')
                if (!automaticApplied) {
                    this.alert_message({
                        title: this.env._t('Error'),
                        body: errorMessage
                    })
                }
                this.chrome.showNotification(_t('Error'), errorMessage)
                return false
            }
            if (productIdsOfRuleExistInCart.length == 0 && rule.applied_product_ids.length != 0) {
                errorMessage = this.env._t('Products in cart not matching with Based on Products of Promotion/Coupon')
                if (!automaticApplied) {
                    this.alert_message({
                        title: this.env._t('Error'),
                        body: errorMessage
                    })
                }
                this.chrome.showNotification(_t('Error'), errorMessage)
                return false
            }
            if (program.maximum_use_number > 0) {
                if ((couponPrograms && couponPrograms['0']['pos_order_count'] >= program.maximum_use_number) || (couponPrograms && couponPrograms[0] && !couponPrograms[0]['active'])) {
                    errorMessage = this.env._t('Promotion/Coupon applied full ') + program.maximum_use_number + this.env._t(' POS Orders.')
                    if (!automaticApplied) {
                        this.alert_message({
                            title: this.env._t('Error'),
                            body: errorMessage
                        })
                    }
                    this.chrome.showNotification(_t('Error'), errorMessage)
                    return false
                }
            }
            return true
        },

        async getInformationCouponPromotionOfCode(code) {
            if (!this.couponProgram_by_code) {
                return false
            }
            let program = this.couponProgram_by_code[code];
            let coupon;
            let rule;
            let reward;
            if (program) {
                this._removeLineByCouponID(program['id'])
                rule = this.couponRule_by_id[program.rule_id[0]]
                reward = this.couponReward_by_id[program.reward_id[0]]
            } else {
                coupon = this.coupon_by_code[code]
                if (coupon) {
                    program = this.couponProgram_by_id[coupon.program_id[0]]
                    rule = this.couponRule_by_id[program.rule_id[0]]
                    reward = this.couponReward_by_id[program.reward_id[0]]
                }

            }
            if (!program && !coupon) {
                this.chrome.showNotification(_t('Error'), _t('Please checking some Reasons: Code of your Input not found Coupon/Program OR Coupon/Program of Code has Expired !!!'))
            }
            if (program && rule && reward) {
                let canBeApplyCoupon = await this._checkCouponRule(program, coupon, rule, reward, true)
                if (canBeApplyCoupon) {
                    let hasAppliedCoupon = this._applyCouponReward(program, coupon, rule, reward);
                    if (hasAppliedCoupon) {
                        this.chrome.showNotification(_t('Coupon Program: ') + program['name'], _t('Added to Order'), 4000)
                        return true
                    }
                }
            }
            return false
        },
        wrongInput(el, element) {
            $(el).find(element).css({
                'box-shadow': '0px 0px 0px 1px rgb(236, 5, 5) inset',
                'border': 'none !important',
                'border-bottom': '1px solid red !important'
            });
        },
        passedInput(el, element) {
            $(el).find(element).css({
                'box-shadow': '#3F51B5 0px 0px 0px 1px inset'
            })
        },
        reload_pos: function () {
            location.reload();
        },

        async close_pos() {
            this.chrome._closePosScreen()
        },

        /** OVERRIDE **/
        // wrapper around the _save_to_server that updates the synch status widget
        // Resolves to the backend ids of the synced orders.
        _flush_orders: function(orders, options) {
            var self = this;
            
            // this.set_synch('connecting', orders.length); // Hide loading Icon

            return this._save_to_server(orders, options).then(function (server_ids) {
                self.set_synch('connected');

                for (let i = 0; i < server_ids.length; i++) {
                    self.validated_orders_name_server_id_map[server_ids[i].pos_reference] = server_ids[i].id;
                }
                return _.pluck(server_ids, 'id');
            }).catch(function(error){
                self.set_synch(self.get('failed') ? 'error' : 'disconnected');
                return Promise.reject(error);
            });
        },


        get_source_stock_location: function () {
            let stock_location_id = this.config.stock_location_id;
            let selected_order = this.get_order();
            if (selected_order && selected_order.location) {
                return selected_order.location;
            } else {
                return this.stock_location_by_id[stock_location_id[0]];
            }
        },
        get_all_source_locations: function () {
            if (this.stock_location_ids.length != 0) {
                return this.stock_location_ids.concat(this.config.stock_location_id[0])
            } else {
                return [this.config.stock_location_id[0]]
            }
        },
        generate_wrapped_name: function (name) {
            let MAX_LENGTH = 24; // 40 * line ratio of .6
            let wrapped = [];
            let current_line = "";

            while (name.length > 0) {
                let space_index = name.indexOf(" ");

                if (space_index === -1) {
                    space_index = name.length;
                }

                if (current_line.length + space_index > MAX_LENGTH) {
                    if (current_line.length) {
                        wrapped.push(current_line);
                    }
                    current_line = "";
                }

                current_line += name.slice(0, space_index + 1);
                name = name.slice(space_index + 1);
            }

            if (current_line.length) {
                wrapped.push(current_line);
            }

            return wrapped;
        },
        highlight_control_button: function (button_class) {
            $('.' + button_class).addClass('highlight')
        },
        remove_highlight_control_button: function (button_class) {
            $('.' + button_class).removeClass('highlight')
        },
        async show_purchased_histories(client) {
            let self = this;
            if (!client) {
                client = this.get_client();
            }
            if (!client) {
                this.alert_message({
                    title: 'Warning',
                    body: 'We could not find purchased orders histories, please set client first'
                });
                this.gui.show_screen('clientlist')
            } else {
                let orders = this.db.get_pos_orders().filter(function (order) {
                    return order.partner_id && order.partner_id[0] == client['id']
                });
                if (orders.length) {
                    const {confirmed, payload: result} = await this.showTempScreen(
                        'PosOrderScreen',
                        {
                            order: null,
                            selectedClient: client
                        }
                    );
                } else {
                    this.alert_message({
                        title: 'Warning',
                        body: 'Your POS not active POS Order Management or Current Client have not any Purchased Orders'
                    })
                }
            }
        },
        async _getVoucherNumber() {
            return await rpc.query({
                model: 'pos.config',
                method: 'get_voucher_number',
                args: [[], this.config.id],
                context: {}
            });
        },
        show_products_with_field: function (field) {
            let products = this.db.getAllProducts();
            let products_by_field = _.filter(products, function (product) {
                return product[field] == true;
            });
            if (products_by_field.length != 0) {
                this.gui.screen_instances.products.product_list_widget.set_product_list(products_by_field);
            }
        },
        show_products_type_only_product: function () {
            let products = this.db.getAllProducts();
            let products_type_product = _.filter(products, function (product) {
                return product.type == 'product';
            });
            this.gui.screen_instances.products.product_list_widget.set_product_list(products_type_product);
        },
        async _validate_action(title) {
            let validate = await this._validate_by_manager(title);
            if (!validate) {
                Gui.playSound('error')
                this.alert_message({
                    title: this.env._t('Validation Failed !!!'),
                    body: this.env._t(
                        'Your Action required Approve by Your Manager'
                    ),
                });
                return false;
            }
            return true
        },
        async _validate_by_manager(title) {
            let self = this;
            let manager_validate = [];
            _.each(this.config.manager_ids, function (user_id) {
                let user = self.user_by_id[user_id];
                if (user) {
                    manager_validate.push({
                        id: user.id,
                        label: user.name,
                        item: user,
                        imageUrl: 'data:image/png;base64, ' + user['image_1920'],
                    })
                }
            });
            if (manager_validate.length == 0) {
                this.alert_message({
                    title: this.env._t('Error'),
                    body: this.env._t('Your POS Setting / Tab Security not set Managers Approve'),
                })
                return false
            }
            let popup_title = this.env._t('Select one Manager bellow will Validate your Action')
            if (title) {
                popup_title += ' : ' + title;
            }
            if (manager_validate.length > 1) {
                let {confirmed, payload: selected_user} = await Gui.showPopup('SelectionPopup', {
                    title: popup_title,
                    list: manager_validate,
                })
                if (confirmed) {
                    let manager_user = selected_user;
                    let {confirmed, payload: password} = await Gui.showPopup('NumberPopup', {
                        title: _t('Manager Approval'),
                        isPassword: true,
                        allowScanBarcode: true,
                    });
                    if (confirmed) {
                        if (manager_user['pos_security_pin'] != password) {
                            this.alert_message({
                                title: _t('Warning'),
                                body: _t('Pos Security Pin of ') + manager_user.name + _t(' Incorrect.')
                            })
                            return self._validate_by_manager(title)
                        } else {
                            return true
                        }
                    } else {
                        return false
                    }
                } else {
                    return false
                }
            } else {
                let manager_user = manager_validate[0]['item'];
                let {confirmed, payload: password} = await Gui.showPopup('NumberPopup', {
                    title: _t('Manager Approval'),
                    isPassword: true,
                    allowScanBarcode: true,
                });
                if (confirmed) {
                    if (manager_user['pos_security_pin'] != password) {
                        this.alert_message({
                            title: _t('Warning'),
                            body: _t('Pos Security Pin of ') + manager_user.name + _t(' Incorrect.')
                        })
                        return self._validate_by_manager(title)
                    } else {
                        return true
                    }
                } else {
                    return false
                }
            }
        },
        _search_read_by_model_and_id: function (model, ids) {
            let object = this.get_model(model);
            return new Promise(function (resolve, reject) {
                rpc.query({
                    model: model,
                    method: 'search_read',
                    domain: [['id', 'in', ids]],
                    fields: object.fields
                }, {
                    timeout: 30000,
                    shadow: true,
                }).then(function (datas) {
                    resolve(datas)
                }, function (error) {
                    reject(error)
                })
            })
        },
        _update_cart_qty_by_order: function (product_ids) {
            let selected_order = this.get_order();
            $('.cart_qty').addClass('oe_hidden');
            let product_quantity_by_product_id = selected_order.product_quantity_by_product_id();
            for (let i = 0; i < selected_order.orderlines.models.length; i++) {
                let line = selected_order.orderlines.models[i];
                let product_id = line.product.id;
                let $qty = $('article[data-product-id="' + product_id + '"] .cart_qty');
                let qty = product_quantity_by_product_id[product_id];
                if (qty) {
                    $qty.removeClass('oe_hidden');
                    $('article[data-product-id="' + product_id + '"] .add_shopping_cart').html(qty);
                } else {
                    $qty.addClass('oe_hidden');
                }
            }
            let total_items = selected_order.get_total_items();
            $('.items-incart').text(total_items);
        },
        _get_active_pricelist: function () {
            let current_order = this.get_order();
            let default_pricelist = this.default_pricelist;
            if (current_order && current_order.pricelist) {
                let pricelist = _.find(this.pricelists, function (pricelist_check) {
                    return pricelist_check['id'] == current_order.pricelist['id']
                });
                return pricelist;
            } else {
                if (default_pricelist) {
                    let pricelist = _.find(this.pricelists, function (pricelist_check) {
                        return pricelist_check['id'] == default_pricelist['id']
                    });
                    return pricelist
                } else {
                    return null
                }
            }
        },
        get_receipt_template() {
            //TO DO: Get masterdata receipt template
            var receipt_templates = this.db.receipt_templates
            var pos_receipt_template_id = this.config.pos_receipt_template_id
            var pos_receipt_template = false
            if(pos_receipt_template_id){
                pos_receipt_template = receipt_templates.filter((rt)=> rt.id == pos_receipt_template_id[0]);
                if(pos_receipt_template){
                    pos_receipt_template = pos_receipt_template[0]
                    if(pos_receipt_template.size=='custom'){
                        pos_receipt_template['width'] = pos_receipt_template.custom_size+'mm'
                    }
                    else{
                        pos_receipt_template['width'] = pos_receipt_template.size
                    }
                    var width = parseInt(pos_receipt_template['width'].replace('mm',''))
                    if(width>=80){
                        pos_receipt_template['element_id'] = 'receipt_template_c_big_size'
                    }
                    else{
                        pos_receipt_template['element_id'] = 'receipt_template_c_small_size'
                    }
                }

                pos_receipt_template['icon_coupon_base64'] = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4MSIgaGVpZ2h0PSIyNiI+CgogPGc+CiAgPHRpdGxlPkNvdXBvbjwvdGl0bGU+CiAgPHJlY3Qgcng9IjQiIHN0cm9rZT0iIzU0NTQxNSIgaWQ9InN2Z18yIiBoZWlnaHQ9IjI2IiB3aWR0aD0iODEiIHk9IjAiIHg9IjAiIHN0cm9rZS13aWR0aD0iMCIgZmlsbD0iIzE0OGY4YiIvPgogIDx0ZXh0IHN0cm9rZT0iIzU0NTQxNSIgeG1sOnNwYWNlPSJwcmVzZXJ2ZSIgdGV4dC1hbmNob3I9InN0YXJ0IiBmb250LWZhbWlseT0iTm90byBTYW5zIEpQIiBmb250LXNpemU9IjI0IiBpZD0ic3ZnXzEiIHk9IjE3IiB4PSI0IiBzdHJva2Utd2lkdGg9IjAiIGZpbGw9IiNmZmZmZmYiPmNvdXBvbjwvdGV4dD4KIDwvZz4KPC9zdmc+';
            }
            return pos_receipt_template;
        },

        sumbit_session_order: async function(order){
            let self = this;
            let vals = {
                uid: order['uid'],
                database: self.env.pos.session.db,
                pos_config_id: self.config.id,
                pos_session_id: self.env.session.config.pos_session_id,
                order: order.export_as_JSON(),
            }
            console.warn('[sumbit_session_order] ~ Sending Data: ', vals)
            let result = await self.rpc({
                model: 'pos.sync.session.order',
                method: 'new_order', 
                args: [[], vals]
            }, {
                shadow: true,
                timeout: 5000
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[sumbit_session_order] ~ Server Offline')
                } else {
                    console.error('[sumbit_session_order] ~ Error 403')
                }
                self.env.pos.alert_message({
                    title: self.env._t('Warning'),
                    body: self.env._t('Failed, please try again.'),
                })
                return Promise.reject(error);
            });
            console.warn('[sumbit_session_order] ~ Result: ', result);
            if(result){
                order.sync_write_date = moment().format('YYYY-MM-DD HH-mm-ss');

                let orderlines = order.get_orderlines();
                for (var i = orderlines.length - 1; i >= 0; i--) {
                    let sync_line_id = result.sync_line_ids[orderlines[i].uid];
                    if(sync_line_id){
                        orderlines[i].sync_line_id = sync_line_id;
                    }
                }
                order.trigger('change', order);
            }
            return result;
        },

        sync_session_orders: async function(){
            const self = this;
            let vals = {
                database: self.session.db,
                pos_config_id: self.config.id,
                pos_session_id: self.env.session.config.pos_session_id,
            }
            if(self.removed_order_uids){
                vals['removed_order_uids'] = self.removed_order_uids;
            }
            console.log('[sync_session_orders] ~ Sync Orders: ', vals)

            let results = await this.rpc({
                model: 'pos.sync.session.order',
                method: 'sync_orders', 
                args: [[], vals]
            }, { shadow: true, timeout: 75000}).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[sync_session_orders] ~ Server Offline')
                } else {
                    console.error('[sync_session_orders] ~ Error 403')
                }
                return Promise.reject(error);
            });
            console.log('[sync_session_orders] ~ Results:', results)

            let draft_orders = results['draft_orders'];
            let removed_order_uids = results['removed_order_uids'];
            if (removed_order_uids.length){
                self.removed_order_uids = removed_order_uids;
            }
            removed_order_uids.forEach(function(uid){
                let done_order = self.get_order_by_uid(uid);
                if(done_order){
                    self.db.remove_order(done_order.uid);
                    done_order.destroy({'reason': 'abandon'});
                }
            });

            let orders = self.get('orders');
            for (let i = draft_orders.length - 1; i >= 0; i--) {
                let draft_order = draft_orders[i];
                let vals = draft_order.data;
                let order = null;
                order = self.get_order_by_uid(vals.uid);
                if (!order) {
                    order = self.get_order_by_name(vals.name);
                }
                
                if (order) {
                    let is_changed = false
                    if( typeof order.sync_write_date == 'undefined' || order.sync_write_date != draft_order.write_date ){
                        is_changed = true;
                    }
                    if(is_changed){
                        let lines = vals.lines;
                        console.log('[sync_session_orders] ~ Sync Order: ', order.name, ' Lines:', lines.length, ' items')
                        order.sync_write_date = draft_order.write_date;
                        order.sync_sequence_number = vals.sync_sequence_number;
                        
                        while (order.orderlines.models.length > 0) {
                            order.orderlines.models.forEach(l => order.orderlines.remove(l));
                        }

                        for (var j = lines.length - 1; j >= 0; j--) {
                            let _json = lines[j][2];
                            order.add_orderline(new models.Orderline({}, {pos: self.env.pos, order: order, json: _json}));
                        }

                        if(vals.partner_id){
                            let client = self.db.get_partner_by_id(vals.partner_id);
                            order.set_client(client);
                            order.trigger('change', order);
                        }
                    }
                }

                if (!order) {
                    let new_order = new models.Order({}, {pos: self.env.pos, json: vals});
                    if (draft_order.write_date) {
                        new_order.sync_write_date = draft_order.write_date;
                    }
                    if (vals.sync_sequence_number) {
                        new_order.sync_sequence_number = vals.sync_sequence_number;
                    }
                    orders.add(new_order);
                    new_order.trigger('change', new_order);
                }

            }
            return Promise.resolve(true);
        },
        get_session_order_datas: async function(order){
            const self = this;
            let vals = {
                uid: order['uid'],
                database: self.env.pos.session.db,
                pos_config_id: self.env.pos.config.id,
                pos_session_id: self.env.session.config.pos_session_id,
                order: order.export_as_JSON(),
            }
            console.warn('[get_session_order_data] ~ vals: ', vals)
            let result = await this.rpc({
                model: 'pos.sync.session.order', 
                method: 'sync_order', 
                args: [[], vals]
            }, {
                shadow: true,
                timeout: 75000
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[get_session_order_data] ~ Server Offline')
                } else {
                    console.error('[get_session_order_data] ~ Error 403')
                }
                return { 'status': 'failed', 'data': [],  'message': error  }
            });
            console.warn('[get_session_order_data] ~ Result:', result)
            return { 'status': 'success', 'data': result }
        },
        sync_session_order: async function(order){
            const self = this;
            let session_order_datas = await self.get_session_order_datas(order);
            if(session_order_datas.status == 'failed'){
                self.env.pos.alert_message({
                    title: self.env._t('Warning'),
                    body: self.env._t('Failed, please try again.'),
                });
            }
            if(session_order_datas.status == 'success'){
                if(session_order_datas.data.length == 0){
                    return;
                }
                let data_order = session_order_datas.data[0];

                if(data_order.state != 'draft'){
                    self.env.pos.db.remove_order(order.uid);
                    order.destroy({'reason': 'abandon'});
                    self.env.pos.alert_message({
                        title: self.env._t('Warning'),
                        body: self.env._t(order.uid + ' already done'),
                    })
                }

                while (order.orderlines.models.length > 0) {
                    order.orderlines.models.forEach(l => order.remove_orderline(l))
                }
                let vals = data_order.data;
                let lines = vals.lines.reverse();
                for (var j = lines.length - 1; j >= 0; j--) {
                    let _json = lines[j][2];
                    order.add_orderline(new models.Orderline({}, {pos: self.env.pos, order: order, json: _json}));
                }
            }
            return Promise.resolve(true);
        },

        set_cashier: function (employee) {
            _super_PosModel.set_cashier.apply(this, arguments);
            if (employee.is_employee && this.chrome) {
                this.config.allow_discount = employee['allow_discount']
                this.config.allow_qty = employee['allow_qty']
                this.config.allow_price = employee['allow_price']
                this.config.allow_remove_line = employee['allow_remove_line']
                this.config.allow_minus = employee['allow_minus']
                this.config.allow_payment = employee['allow_payment']
                this.config.allow_customer = employee['allow_customer']
                this.config.allow_add_order = employee['allow_add_order']
                this.config.allow_remove_order = employee['allow_remove_order']
                this.config.allow_add_product = employee['allow_add_product']
                this.config.allow_payment_zero = employee['allow_payment_zero']
                this.chrome.env.qweb.forceUpdate();

            }
        },
        _get_default_pricelist: function () {
            let current_pricelist = this.default_pricelist;
            return current_pricelist
        },
        get_model: function (_name) {
            let _index = this.models.map(function (e) {
                return e.model;
            }).indexOf(_name);
            if (_index > -1) {
                return this.models[_index];
            }
            return false;
        },
        initialize: function (session, attributes) {
            this.is_mobile = odoo.is_mobile;
            
            let account_tax_model = this.get_model('account.tax');
            account_tax_model.fields.push('type_tax_use');
            let wait_currency = this.get_model('res.currency');
            wait_currency.fields.push(
                'rate'
            );
            let accountFiscalPositionTaxModel = this.get_model('account.fiscal.position.tax');
            let accountFiscalPositionTaxModelLoaded = accountFiscalPositionTaxModel.loaded;
            accountFiscalPositionTaxModel.loaded = function (self, fiscal_position_taxes) {
                fiscal_position_taxes = _.filter(fiscal_position_taxes, function (tax) {
                    return tax.tax_dest_id != false;
                });
                if (fiscal_position_taxes.length > 0) {
                    accountFiscalPositionTaxModelLoaded(self, fiscal_position_taxes);
                }
            };
            const posCategoryModel = this.get_model('pos.category');
            posCategoryModel.condition = function (self) {
                if (self.config.product_category_ids.length != 0) {
                    console.warn('Your POS Only loading product from sale category')
                }
                return self.config.product_category_ids.length == 0
            }
            let posCategoryModelLoaded = posCategoryModel.loaded;
            posCategoryModel.loaded = function (self, categories) {
                if (!self.pos_categories) {
                    self.pos_categories = categories;
                    self.pos_category_by_id = {};
                } else {
                    self.pos_categories = self.pos_categories.concat(categories);
                }
                for (let i = 0; i < categories.length; i++) {
                    let category = categories[i];
                    self.pos_category_by_id[category.id] = category;
                }
                _.each(categories, function (category) {
                    category.parent = self.pos_category_by_id[category.parent_id[0]];
                });
                posCategoryModelLoaded(self, categories);
            };
            posCategoryModel.fields = posCategoryModel.fields.concat([
                'is_category_combo',
                'sale_limit_time',
                'from_time',
                'to_time',
                'submit_all_pos',
                'pos_branch_ids',
                'pos_config_ids',
                'category_type',
                'image_128',
            ]);

            let productCategoryModel = this.get_model('product.category');
            productCategoryModel.fields = productCategoryModel.fields.concat([
                'complete_name',
                'parent_id',
                'child_id',
                'write_date'
            ])
            productCategoryModel.domain = function (self) {
                if (self.config.product_category_ids && self.config.product_category_ids.length != 0) {
                    return [['id', 'in', self.config.product_category_ids]]
                } else {
                    return []
                }
            }
            let productCategoryLoaded = productCategoryModel.loaded;
            productCategoryModel.loaded = function (self, categories) {
                self.pos_categories_appetizer = []
                if (self.product_category_by_id == undefined) {
                    self.product_category_by_id = {};
                }
                self.product_category_by_id[0] = {
                    id: 0,
                    name: 'Sale Categories'
                }
                for (let i = 0; i < categories.length; i++) {
                    let category = categories[i];
                    self.product_category_by_id[category.id] = category;
                }
                _.each(categories, function (category) {
                    category.parent = self.product_category_by_id[category.parent_id[0]];
                });
                productCategoryLoaded(self, categories);
                if (self.config.product_category_ids.length != 0) {
                    self.db.add_categories(categories);
                }
            };
            let productModel = this.get_model('product.product');

//            'sale_with_package',
            productModel.fields.push(
                'name', 
                'to_weight',
                'is_employee_meal',
                'multi_category',
                'multi_uom',
                'type',
                // 'multi_variant',
                'supplier_barcode',
                'is_combo',
                'sale_ok',
                'combo_limit',
                'uom_po_id',
                'barcode_line_ids',
                'pos_categ_ids',
                'supplier_taxes_id',
                'volume',
                'weight',
                'description_sale',
                'description_picking',
                'type',
                'cross_selling',
                'standard_price',
                'pos_sequence',
                'is_voucher',
                'pizza_modifier',
                'qty_warning_out_stock',
                'write_date',
                'is_voucher',
                'combo_price',
                'is_combo_item',
                'name_second',
                'note_ids',
                'tag_ids',
                'commission_rate',
                'company_id',
                'uom_ids',
                'attribute_line_ids',
                'product_template_attribute_value_ids',
                // 'model_id',
                'discountable',
                'refundable',
                'open_price',
                'is_can_be_po',
                'plu_number',
                'default_time',
            );
            this.bus_location = null;
            let partnerModel = this.get_model('res.partner');
            partnerModel.fields.push(
                'display_name',
                'special_name',
                'ref',
                'vat',
                'comment',
                'discount_id',
                'property_product_pricelist',
                'property_payment_term_id',
                'is_company',
                'write_date',
                'birthday_date',
                'group_ids',
                'title',
                'company_id',
                'pos_order_count',
                'pos_total_amount',
                'type',
                'parent_id',
                'company_type',
                'active',
                
                'customer_credit_limit',
                'customer_credit',
            );
            const productAttributeModel = this.get_model('product.attribute');
            if (productAttributeModel) {
                productAttributeModel.domain = []
            }
            const priceListObject = this.get_model('product.pricelist');
            priceListObject.fields.push('id', 'currency_id', 'barcode');
            priceListObject['pricelist'] = true;
            const priceListLoaded = priceListObject.loaded;
            priceListObject.loaded = function (self, pricelists) {
                self.pricelist_currency_ids = [];
                self.pricelist_by_id = {};
                for (let i = 0; i < pricelists.length; i++) {
                    let pricelist = pricelists[i];
                    if (pricelist.currency_id) {
                        pricelist.name = pricelist.name + '(' + pricelist.currency_id[1] + ')'
                    }
                    self.pricelist_by_id[pricelist.id] = pricelist;
                    if (pricelist.currency_id) {
                        self.pricelist_currency_ids.push(pricelist.currency_id[0])
                    }
                }
                priceListLoaded(self, pricelists);
            };

            let pricelistItemModel = this.get_model('product.pricelist.item');
            pricelistItemModel['pricelist'] = true;
            const paymentMethodObject = this.get_model('pos.payment.method');
            const paymentMethodLoaded = paymentMethodObject.loaded;
            paymentMethodObject.fields = paymentMethodObject.fields.concat([
                'cash_journal_id',
                'fullfill_amount',
                'shortcut_keyboard',
                'cheque_bank_information',
                'apply_charges',
                'fees_amount',
                'fees_type',
                'fees_product_id',
                'discount',
                'discount_type',
                'discount_amount',
                'discount_product_id',
            ]);
            paymentMethodObject.loaded = function (self, payment_methods) {
                self.payment_methods = payment_methods;
                paymentMethodLoaded(self, payment_methods);
            };
            paymentMethodObject.domain = function (self) {
                return ['|', ['active', '=', false], ['active', '=', true], ['id', 'in', self.config.payment_method_ids]];
            }
            let res_users_object = this.get_model('res.users');
            if (res_users_object) {
                res_users_object.fields = res_users_object.fields.concat([
                    'pos_security_pin',
                    'barcode',
                    'pos_config_id',
                    'partner_id',
                    'company_ids',
                ]);
                // todo: move load res.users after pos.config, we dont want load res.users after partners or products because we need checking company_ids of user
                let res_users = _.filter(this.models, function (model) {
                    return model.model == 'res.users';
                });
                this.models = _.filter(this.models, function (model) {
                    return model.model != 'res.users';
                })
                if (res_users) {
                    let index_number_pos_config = null;
                    for (let i = 0; i < this.models.length; i++) {
                        let model = this.models[i];
                        if (model.model == 'pos.config') {
                            index_number_pos_config = i;
                            break
                        }
                    }
                    for (let i = 0; i < res_users.length; i++) {
                        let user_model = res_users[i];
                        this.models.splice(index_number_pos_config + 1, 0, user_model)
                    }
                }
            }
            let pos_session_model = this.get_model('pos.session');
            pos_session_model.fields.push('lock_state');
            pos_session_model.fields.push('opened_at')
            pos_session_model.fields.push('order_count');
            pos_session_model.fields.push('total_payments_amount');
            pos_session_model['core'] = true
            let pos_config_model = this.get_model('pos.config');
            let _pos_config_loaded = pos_config_model.loaded;
            pos_config_model.loaded = function (self, configs) {
                _pos_config_loaded(self, configs);
                if(self.config.sync_to_pos_config_ids){
                    self.config.sync_to_pos_config_ids = _.filter(self.config.sync_to_pos_config_ids, function (id) {
                        return id != self.config.id
                    })
                }
            };
            _super_PosModel.initialize.apply(this, arguments);
            let employee_model = this.get_model('hr.employee');
            if (employee_model) {
                let _super_employee_model_loaded = employee_model.loaded;
                employee_model.fields = employee_model.fields.concat([
                    'allow_discount',
                    'allow_qty',
                    'allow_price',
                    'allow_remove_line',
                    'allow_minus',
                    'allow_payment',
                    'allow_customer',
                    'allow_add_order',
                    'allow_remove_order',
                    'allow_add_product',
                    'allow_payment_zero',
                    'pos_use_otp',
                    'pos_otp_phone',
                    'work_phone',
                    'image_1920',
                ])
                employee_model.loaded = function (self, employees) {
                    _super_employee_model_loaded(self, employees);
                    self.employee_by_id = {};
                    for (let i = 0; i < employees.length; i++) {
                        let emp = employees[i];
                        self.employee_by_id[emp.id] = emp;
                    }
                };
            }
        },
        async _required_set_client() {
            let order = this.get_order();
            let client = order.get_client();
            if (!client && this.config.add_customer_before_products_already_in_shopping_cart) {
                try {
                    const {confirmed, payload: newClient} = await Gui.showTempScreen(
                        'ClientListScreen',
                        {client: null}
                    );
                    if (confirmed) {
                        order.set_client(newClient);
                    } else {
                        this.alert_message({
                            title: this.env._t('Warning !!! Your POS Active set Customer before add items to Cart'),
                            body: this.env._t('Please select one Customer before add items to cart')
                        })
                        return this._required_set_client()
                    }
                } catch (e) {
                    return false
                }

            }
            return true
        },
        async add_new_order() {
            _super_PosModel.add_new_order.apply(this, arguments);
            const order = this.get_order();
            if(order){
                const client = order.get_client();
                if (!client && this.config.customer_default_id) {
                    let client_default = this.db.get_partner_by_id(this.config.customer_default_id[0]);
                    if (!client_default) {
                        this.alert_message({
                            title: this.env._t('Warning !!!'),
                            body: this.config.customer_default_id[1] + this.env._t(' set to Default Customer of new Order, but it Arichived it. Please Unarchive')
                        })
                    } else {
                        order.set_client(client_default);
                    }
                }
                this._required_set_client()
                this.alert_message({
                    title: this.env._t('New Order !!!'),
                    body: order.uid + this.env._t(' just create successfully'),
                })
            }
        },
        formatDateTime: function (value, field, options) {
            if (value === false) {
                return "";
            }
            if (!options || !('timezone' in options) || options.timezone) {
                value = value.clone().add(session.getTZOffset(value), 'minutes');
            }
            return value.format(time.getLangDatetimeFormat());
        },
        format_date: function (date) { // covert datetime backend to pos
            if (date) {
                return this.formatDateTime(
                    moment(date), {}, {timezone: true});
            } else {
                return ''
            }
        },
        get_config: function () {
            return this.config;
        },
        get_packaging_by_product: function (product) {
            if (!this.packaging_by_product_id || !this.packaging_by_product_id[product.id]) {
                return false;
            } else {
                return true
            }
        },
        get_default_sale_journal: function () {
            let invoice_journal_id = this.config.invoice_journal_id;
            if (!invoice_journal_id) {
                return null
            } else {
                return invoice_journal_id[0];
            }
        },
        get_bus_location: function () {
            return this.bus_location
        },
        alert_message: function (options) {
            const self = this;
            let title = options['title'] || 'Message'
            let timer = options['timer'] || 2000;
            let body = options.body || ''
            if (this.chrome) {
                this.chrome.showNotification(title, body, timer)
            }
        },

        query_backend_fail: function (error) {
            if (error && error.message && error.message.code && error.message.code == 200) {
                return this.alert_message({
                    title: _t('Error code: ') + error.message.code + _t(' . Bug of python model method of Backend'),
                    body: error.message.data.message,
                    timer: 4000,
                })
            }
            if (error && error.message && error.message.code && error.message.code == -32098) {
                return this.alert_message({
                    title: _t('Error code: ') + error.message.code,
                    body: _t('Your Internet has problem or Your Hashmicro Server Offline'),
                    timer: 4000,
                })
            } else {
                return this.alert_message({
                    title: _t('Error code: ') + error.message.code,
                    body: _t('Your offline mode or backend codes have issues. Please contact your admin system'),
                    timer: 4000,
                })
            }
        },


        async scan_product(parsed_code) {
            /*
                This function only return true or false
                Because if barcode passed mapping data of products, customers ... will return true
                else all return false and popup warning message
             */
            let self = this;
            const barcodeScanned = parsed_code.code
            console.log('-> [scan barcode]' + parsed_code.code);
            const product = this.db.get_product_by_barcode(parsed_code.code);
            const selectedOrder = this.get_order();
            let products_by_supplier_barcode = this.db.product_by_supplier_barcode[parsed_code.code];
            let barcodes = null;
            if(this.barcodes_by_barcode){
                barcodes = this.barcodes_by_barcode[parsed_code.code];
            }
            let productQuantityPacks = [];
            if(this.packagings){
                productQuantityPacks = this.packagings.filter(pack => pack.barcode == barcodeScanned);
            }
            if (productQuantityPacks.length) {
                let list = productQuantityPacks.map(pack => ({
                    label: pack.name + this.env._t(' with barcode ' + pack.barcode),
                    item: pack,
                    id: pack.id
                }));
                let {confirmed, payload: packSelected} = await Gui.showPopup('SelectionPopup', {
                    title: _t('Select one Product Packaging'),
                    list: list,
                });
                if (confirmed) {
                    let productOfPack = this.db.product_by_id[packSelected.product_id[0]];
                    if (productOfPack) {
                        selectedOrder.add_product(productOfPack, {quantity: packSelected.qty, merge: false});
                        let order_line = selectedOrder.get_selected_orderline();
                        order_line.price_manually_set = true;
                        if (packSelected.list_price > 0) {
                            order_line.set_unit_price(packSelected['list_price']);
                        }
                        return true
                    }
                }
            }

            // scan supplier barcode
            if (products_by_supplier_barcode) {
                let list = products_by_supplier_barcode.map(p => ({
                    id: p.id,
                    label: p.display_name,
                    item: p

                }))
                if (product) {
                    list.push({
                        id: product.id,
                        label: product.display_name,
                        item: product
                    })
                }
                let {confirmed, payload: productSelected} = await Gui.showPopup('SelectionPopup', {
                    title: _t('Select one product'),
                    list: list,
                });
                if (confirmed) {
                    if (parsed_code.type === 'price') {
                        selectedOrder.add_product(productSelected, {
                            quantity: 1,
                            price: product['lst_price'],
                            merge: true
                        });
                    } else if (parsed_code.type === 'weight') {
                        selectedOrder.add_product(productSelected, {
                            quantity: 1,
                            price: product['lst_price'],
                            merge: false
                        });
                    } else if (parsed_code.type === 'discount') {
                        selectedOrder.add_product(productSelected, {discount: parsed_code.value, merge: false});
                    } else {
                        selectedOrder.add_product(productSelected);
                    }
                    return true
                }
            }
            // scan via multi barcode
            if (!product && barcodes) { // not have product but have barcodes
                let productOfBarcode
                let barcodeSelected
                if (barcodes.length > 1) {
                    let list = barcodes.map(b => ({
                        id: b.id,
                        item: b,
                        label: b.product_id[1] + this.env._t(' with Units: ') + b.uom_id[1]
                    }));
                    let {confirmed, payload: barcodeSelected} = await Gui.showPopup('SelectionPopup', {
                        title: _t('Select Product add to Cart'),
                        list: list,
                    })
                    if (confirmed) {
                        productOfBarcode = self.db.product_by_id[barcodeSelected['product_id'][0]];
                    }
                } else {
                    barcodeSelected = barcodes[0]
                    productOfBarcode = self.db.product_by_id[barcodes[0]['product_id'][0]];
                }
                if (productOfBarcode) {
                    let pricelist_id = barcodeSelected.pricelist_id[0];
                    let pricelist = this.pricelist_by_id[pricelist_id];
                    if (pricelist) {
                        selectedOrder.set_pricelist(pricelist)
                    }
                    selectedOrder.add_product(productOfBarcode, {
                        quantity: 1,
                        extras: {
                            uom_id: barcodeSelected['uom_id'][0],
                            scanned_barcode: parsed_code.code,
                            productOfBarcode: productOfBarcode,
                            selected_uom_id: barcodeSelected['uom_id']
                        }
                    });
                    let uom_id = barcodeSelected.uom_id[0];
                    let uom = this.uom_by_id[uom_id];
                    if (uom && selectedOrder.pricelist) {
                        let price = productOfBarcode.get_price(product, selectedOrder.pricelist, 1, uom_id);
                        selectedOrder.selected_orderline.set_unit(uom_id, price)
                    }
                    return true
                }
            }
            // voucher
            if (!product && barcodeScanned) {
                let voucher = await this.rpc({
                    model: 'pos.voucher',
                    method: 'get_voucher_by_code',
                    args: [barcodeScanned, []],
                })
                if (voucher != -1) {
                    selectedOrder.client_use_voucher(voucher)
                    return true
                }
            }
            const orderReturn = this.env.pos.db.get_pos_orders().find(o => o.ean13 == barcodeScanned)
            if (orderReturn) {
                const {confirmed, payload: result} = await Gui.showTempScreen(
                    'PosOrderScreen',
                    {
                        order: orderReturn,
                        selectedClient: null
                    }
                );
                return true
            }
            const scanCoupon = this.getInformationCouponPromotionOfCode(barcodeScanned)
            if (!scanCoupon) {
                return true
            }
        // Final check for product scan
            if (product) {
                if (parsed_code.type === 'price') {
                    selectedOrder.add_product(product, {
                        quantity: 1,
                        price: product['lst_price'],
                        merge: true
                    });
                } else if (parsed_code.type === 'weight') {
                    selectedOrder.add_product(product, {
                        quantity: 1,
                        price: product['lst_price'],
                        merge: false
                    });
                } else if (parsed_code.type === 'discount') {
                    selectedOrder.add_product(product, {discount: parsed_code.value, merge: false});
                } else {
                    selectedOrder.add_product(product, {});
                }
                return true
            }
            return false
        },

        get_image_url_by_model: function (record, model) {
            return window.location.origin + '/web/image?model=' + model + '&field=image_128&id=' + record.id;
        },
        async buildReport(report_html) {
            const printer = new Printer();
            const ticketImage = await printer.htmlToImg(report_html);
            return 'data:image/png;base64,' + ticketImage
        },
        async saveOrderRemoved(selectedOrder) {
            if (this.config.save_orders_removed) {
                selectedOrder['state'] = 'cancel'
                selectedOrder['removed_user_id'] = this.pos_session.user_id[0]
                await this.push_single_order(selectedOrder, {
                    draft: true
                })
            }
        },
        getReceiptEnv() {
            let selectedOrder = this.get_order();
            if (!selectedOrder) {
                return null
            }
            let receiptEnv = selectedOrder.getOrderReceiptEnv();
            receiptEnv['pos'] = this;
            if (this.company.contact_address) {
                receiptEnv.receipt.contact_address = this.company.contact_address
            }
            let orderlines_by_category_name = {};
            let order = this.get_order();
            let orderlines = order.orderlines.models;
            let categories = [];
            receiptEnv['orderlines_by_category_name'] = orderlines_by_category_name;
            receiptEnv['categories'] = categories;
            receiptEnv['total_paid'] = order.get_total_paid(); // save amount due if have (display on receipt of partial order)
            receiptEnv['total_due'] = order.get_due(); // save amount due if have (display on receipt of partial order)
            receiptEnv['invoice_ref'] = order.invoice_ref;
            receiptEnv['picking_ref'] = order.picking_ref;
            receiptEnv['order_fields_extend'] = order.order_fields_extend;
            receiptEnv['delivery_fields_extend'] = order.delivery_fields_extend;
            receiptEnv['invoice_fields_extend'] = order.invoice_fields_extend;
            if (selectedOrder['backendOrder']) {
                this.qrCodeLink = window.origin + "/pos/scanQrCode?order_id=" + selectedOrder['backendOrder']['id']
            } else {
                this.qrCodeLink = null
            }
            receiptEnv['oloutlet_order_id'] = order.oloutlet_order_id;
            receiptEnv['oloutlet_order_from'] = order.oloutlet_order_from;
            receiptEnv['oloutlet_order_type'] = order.oloutlet_order_type;
            receiptEnv['oloutlet_order_info'] = order.oloutlet_order_info;
            return receiptEnv
        },
        _get_voucher_env: function (voucher) {
            let cashier = this.get_cashier();
            let company = this.company;
            return {
                widget: this,
                pos: this,
                cashier: cashier,
                company: company,
                voucher: voucher
            };
        },
        _render_vouchers: function (vouchers_created) {
            let el_pos_receipt = $('.pos-receipt-container');
            let url_location = window.location.origin + '/report/barcode/EAN13/';
            for (let i = 0; i < vouchers_created.length; i++) {
                let voucher = vouchers_created[i];
                voucher['url_barcode'] = url_location + voucher['code'];
                el_pos_receipt.append(
                    qweb.render('VoucherCard', this._get_voucher_env(voucher))
                );
            }
        },
        format_currency: function (amount, precision,currency=false) {
            if (currency) {
                amount = this.format_currency_no_symbol(amount, precision);
                if (currency.position === 'after') {
                    return amount + ' ' + (currency.symbol || '');
                } else {
                    return (currency.symbol || '') + ' ' + amount;
                }
            } else {
                return _super_PosModel.format_currency.call(this, amount, precision);
            }
        },
        _save_to_server: function (orders, options) {
            let self = this;
            this.partner_need_update_ids = [];
            this.wait_print_voucher = false;
            if (orders.length) {
                if (orders.length == 1 && orders[0] == undefined) {
                    return Promise.resolve([]);
                }
                for (let n = 0; n < orders.length; n++) {
                    if (!orders[n]['data']) {
                        continue
                    }
                    let order = orders[n]['data'];
                    if (order.partner_id) {
                        this.partner_need_update_ids.push(order.partner_id)
                    }
                    for (let i = 0; i < order.lines.length; i++) {
                        let line = order.lines[i][2];
                        if (line.voucher) {
                            this.wait_print_voucher = true;
                            break;
                        }
                    }
                    posbus.trigger('reload.session.information.widget', {
                        'amount_total': order['amount_total']
                    })
                }
            }
            return _super_PosModel._save_to_server.call(this, orders, options).then(function (backendOrderValue) {
                if (backendOrderValue.length == 1) {
                    console.log('[_save_to_server] new orders: ' + _.pluck(backendOrderValue, 'id')[0])
                    if (backendOrderValue) {
                        let frontend_order = self.get_order();
                        for (let i = 0; i < backendOrderValue.length; i++) {
                            let backend_order = backendOrderValue[i];
                            if (frontend_order) {
                                frontend_order['backendOrder'] = backend_order
                                frontend_order.invoice_ref = backend_order.invoice_ref;
                                frontend_order.picking_ref = backend_order.picking_ref;
                                if (backend_order.included_order_fields_extend) {
                                    frontend_order.order_fields_extend = backend_order.order_fields_extend;
                                }
                                if (backend_order.included_delivery_fields_extend) {
                                    frontend_order.delivery_fields_extend = backend_order.delivery_fields_extend;
                                }
                                if (backend_order.included_invoice_fields_extend) {
                                    frontend_order.invoice_fields_extend = backend_order.invoice_fields_extend;
                                }

                            }
                        }
                    }
                    if (self.partner_need_update_ids.length) {
                        for (let i = 0; i < self.partner_need_update_ids.length; i++) {
                            self.load_new_partners(self.partner_need_update_ids[i]);
                        }
                    }
                    if (self.wait_print_voucher) {
                        self.rpc.query({
                            model: 'pos.voucher',
                            method: 'get_vouchers_by_order_ids',
                            args: [[], _.pluck(backendOrderValue, 'id')]
                        }).then(function (vouchers_created) {
                            if (vouchers_created.length) {
                                self.wait_print_voucher = false;
                                self.vouchers_created = vouchers_created;
                                self._render_vouchers(self.vouchers_created);
                            }
                        })
                    }
                }
                self.partner_need_update_ids = [];
                return backendOrderValue
            }).catch(function (reason) {
                if (reason['code'] == -32098) {
                    self.alert_message({
                        title: _t('Error'),
                        body: _t('Your Offline Mode, could not save Order to backend')
                    })
                }
                var error = reason.message;
                console.warn('Failed to send orders:', orders);
                if (error.code === 200) {    // Business Logic Error, not a connection problem
                    // Hide error if already shown before ...
                    if ((!self.get('failed') || options.show_error) && !options.to_invoice) {
                        self.set('failed', error);
                        throw error;
                    }
                }
                throw error;
            });
        },

        push_order_one: function (order_id, opts) {
            opts = opts || {};
            var self = this;
            return new Promise(function (resolve, reject) {
                self.flush_mutex.exec(function () {
                    var order = self.db.get_order(order_id);
                    if (order){
                        var flushed = self._flush_orders([order], opts);
                    } else {
                        var flushed = Promise.resolve([]);
                    }
                    flushed.then(resolve, reject);
                    return flushed;
                });
            });
            
        },
        
        // Overide:
        // Todo: limit push orders to only one by one
        push_orders: function (order, opts) {
            opts = opts || {};
            var self = this;

            if (order) {
                this.db.add_order(order.export_as_JSON());
            }
            return new Promise(function (resolve, reject) {

                let limit_push = 1;
                let flush_order = [];
                let orders = self.db.get_orders();
                if(orders.length){
                    flush_order = orders.slice(0, limit_push);
                }
                self.flush_mutex.exec(function () {
                    var flushed = self._flush_orders(flush_order, opts);

                    flushed.then(resolve, reject);

                    return flushed;
                });
            });
            
        },

        push_single_order: function (order, opts) {
            if (order && order['data']) {
                this.alert_message({
                    title: this.env._t('Saving Order'),
                    body: order['data']['uid']
                })
            }
            const pushed = _super_PosModel.push_single_order.call(this, order, opts);
            if (!order) {
                return pushed;
            }
            let client = order && order.get_client();
            if (client) {
                for (let i = 0; i < order.paymentlines.models.length; i++) {
                    let line = order.paymentlines.models[i];
                    let amount = line.get_amount();
                    let pos_method_type = line.payment_method.pos_method_type;
                }
            }
            return pushed;
        },
        push_and_invoice_order: function (order) {
            this.alert_message({
                title: _t('Waiting'),
                body: _t('Downloading Invoice for Order')
            });
            return _super_PosModel.push_and_invoice_order.call(this, order);
        },

        add_return_order: function (order_return, lines) {
            let self = this;
            let order_return_id = order_return['id'];
            let order_selected_state = order_return['state'];
            let partner_id = order_return['partner_id'];
            let return_order_id = order_return['id'];
            let order = new models.Order({}, {pos: this});
            order['is_return'] = true;
            order['return_order_id'] = return_order_id;
            order['pos_reference'] = 'Return/' + order['name'];
            order['name'] = 'Return/' + order['name'];
            if (order_return['fiscal_position_id'] && this.fiscal_positions) {
                const fiscal_position = this.fiscal_positions.find(fp => fp.id == order_return['fiscal_position_id'][0])
                if (fiscal_position) {
                    order['fiscal_position'] = fiscal_position
                }
            }
            if (order_return['pricelist_id']) {
                var pricelist = this.pricelist_by_id[order_return['pricelist_id'][0]]
                if (pricelist) {
                    order.pricelist = pricelist // TODO: set direct, because order return not allow set pricelist
                }
            }
            this.get('orders').add(order);
            if (partner_id && partner_id[0]) {
                let client = this.db.get_partner_by_id(partner_id[0]);
                if (client) {
                    order.set_client(client);
                } else {
                    order.set_to_invoice(false)
                }
            } else {
                order.set_to_invoice(false)
            }
            this.set('selectedOrder', order);
            for (let i = 0; i < lines.length; i++) {
                let line_return = lines[i];
                if (line_return['is_return']) {
                    this.db.remove_order(order.id);
                    order.destroy({'reason': 'abandon'});
                    return Gui.showPopup('ConfirmPopup', {
                        title: _t('Warning'),
                        body: _t('This order is order return before, it not possible return again')
                    })
                }
                let price = line_return['price_unit'];
                if (price < 0) {
                    price = -price;
                }
                let quantity = 0;
                let product = this.db.get_product_by_id(line_return.product_id[0]);
                if (!product) {
                    this.db.remove_order(order.id);
                    order.destroy({'reason': 'abandon'});
                    return Gui.showPopup('ConfirmPopup', {
                        title: _t('Warning'),
                        body: _t(line_return.product_id[0] + ' not available in POS, it not possible made return')
                    })
                }
                let line = new models.Orderline({}, {
                    pos: this,
                    order: order,
                    product: product,
                });
                order.orderlines.add(line);
                // TODO: set lot back
                let pack_operation_lots = this.pack_operation_lots_by_pos_order_line_id[line_return.id];
                if (pack_operation_lots) {
                    let multi_lot_ids = [];
                    let lot_name_manual = null;
                    for (let i = 0; i < pack_operation_lots.length; i++) {
                        let pack_operation_lot = pack_operation_lots[i];
                        if (pack_operation_lot.lot_id) {
                            multi_lot_ids.push({
                                'id': pack_operation_lot.lot_id[0],
                                'quantity': pack_operation_lot.quantity
                            })
                        } else {
                            lot_name_manual = pack_operation_lot.lot_name
                        }
                    }
                    if (multi_lot_ids.length) { // TODO: only for multi lot
                        line.set_multi_lot(multi_lot_ids)
                    }
                    if (lot_name_manual) { // TODO: only for one lot
                        let pack_lot_lines = line.compute_lot_lines();
                        for (let i = 0; i < pack_lot_lines.models.length; i++) {
                            let pack_line = pack_lot_lines.models[i];
                            pack_line.set_lot_name(lot_name_manual)
                        }
                        pack_lot_lines.remove_empty_model();
                        pack_lot_lines.set_quantity_by_lot();
                        line.order.save_to_db();
                    }
                }
                if (line_return['tag_ids']) {
                    line.set_tags(line_return['tag_ids'])
                }
                line['returned_order_line_id'] = line_return['id'];
                line['is_return'] = true;
                line.set_unit_price(price);
                line.price_manually_set = true;
                if (line_return.discount)
                    line.set_discount(line_return.discount);
                if (line_return.discount_reason)
                    line.discount_reason = line_return.discount_reason;
                if (line_return['new_quantity']) {
                    quantity = -line_return['new_quantity']
                } else {
                    quantity = -line_return['qty']
                }
                if (line_return.promotion) {
                    quantity = -quantity;
                }
                // if (line_return.redeem_point) {
                //     quantity = -quantity;
                //     line.credit_point = line_return.redeem_point;
                // }
                if (quantity > 0) {
                    quantity = -quantity;
                }
                line.set_quantity(quantity, 'keep price when return');
            }
            if (this.combo_picking_by_order_id) {
                let combo_picking_id = this.combo_picking_by_order_id[return_order_id];
                if (combo_picking_id) {
                    moves = this.stock_moves_by_picking_id[combo_picking_id];
                    for (let n = 0; n < moves.length; n++) {
                        let price = 0;
                        let move = moves[n];
                        let product = this.db.get_product_by_id(move.product_id[0]);
                        if (!product) {
                            this.pos.alert_message({
                                title: 'Warning',
                                body: 'Product ID ' + move.product_id[1] + ' have removed out of POS. Take care'
                            });
                            continue
                        }
                        if (move.product_uom_qty == 0) {
                            continue
                        }
                        let line = new models.Orderline({}, {
                            pos: this,
                            order: order,
                            product: product,
                        });
                        order.orderlines.add(line);
                        line['is_return'] = true;
                        line.set_unit_price(price);
                        line.price_manually_set = true;
                        line.set_quantity(-move.product_uom_qty, 'keep price when return');
                    }
                }
            }

            if (order_selected_state.is_paid_full == false) {
                return new Promise(function (resolve, reject) {
                    rpc.query({
                        model: 'account.bank.statement.line',
                        method: 'search_read',
                        domain: [['pos_statement_id', '=', order_return_id]],
                        fields: [],
                    }).then(function (statements) {
                        let last_paid = 0;
                        for (let i = 0; i < statements.length; i++) {
                            let statement = statements[i];
                            last_paid += statement['amount'];
                        }
                        last_paid = self.format_currency(last_paid,false,order.currency);
                        self.alert_message({
                            'title': _t('Warning'),
                            'body': 'Selected Order need return is partial payment, and customer only paid: ' + last_paid + ' . Please return back money to customer correctly',
                        });
                        resolve()
                    }, function (error) {
                        reject()
                    })
                })
            } else {
                let payment_method = _.find(this.payment_methods, function (method) {
                    return method['journal'] && method['journal']['pos_method_type'] == 'default' && method['journal'].type == 'cash';
                });
                if (payment_method) {
                    order.add_paymentline(payment_method);
                    let amount_withtax = order.get_total_with_tax();
                    order.selected_paymentline.set_amount(amount_withtax);
                    order.trigger('change', order);
                    this.trigger('auto_update:paymentlines', this);
                }
            }
        },
        add_refill_order: function (order, lines) {
            let partner_id = order['partner_id'];
            let newOrder = new models.Order({}, {pos: this});
            this.get('orders').add(newOrder);
            if (partner_id && partner_id[0]) {
                let client = this.db.get_partner_by_id(partner_id[0]);
                if (client) {
                    newOrder.set_client(client);
                }
            }
            this.set('selectedOrder', newOrder);
            for (let i = 0; i < lines.length; i++) {
                let line_refill = lines[i];
                let price = line_refill['price_unit'];
                if (price < 0) {
                    price = -price;
                }
                let quantity = 0;
                let product = this.db.get_product_by_id(line_refill.product_id[0]);
                if (!product) {
                    console.error('Could not find product: ' + line_refill.product_id[0]);
                    continue
                }
                let line = new models.Orderline({}, {
                    pos: this,
                    order: newOrder,
                    product: product,
                });
                newOrder.orderlines.add(line);
                // if (line_refill['variant_ids']) {
                //     line.set_variants(line_refill['variant_ids'])
                // }
                if (line_refill['tag_ids']) {
                    line.set_tags(line_refill['tag_ids'])
                }
                line.set_unit_price(price);
                line.price_manually_set = true;
                if (line_refill.discount)
                    line.set_discount(line_refill.discount);
                if (line_refill.discount_reason)
                    line.discount_reason = line_refill.discount_reason;
                if (line_refill['new_quantity']) {
                    quantity = line_refill['new_quantity']
                } else {
                    quantity = line_refill['qty']
                }
                line.set_quantity(quantity, 'keep price when return');
            }
            return newOrder
        }
        ,
        lock_order: function () {
            $('.rightpane').addClass('oe_hidden');
            $('.timeline').addClass('oe_hidden');
            $('.find_customer').addClass('oe_hidden');
            $('.leftpane').css({'left': '0px'});
            $('.numpad').addClass('oe_hidden');
            $('.actionpad').addClass('oe_hidden');
            $('.deleteorder-button').addClass('oe_hidden');
        }
        ,
        unlock_order: function () {
            $('.rightpane').removeClass('oe_hidden');
            $('.timeline').removeClass('oe_hidden');
            $('.find_customer').removeClass('oe_hidden');
            $('.numpad').removeClass('oe_hidden');
            $('.actionpad').removeClass('oe_hidden');
            if (this.config.staff_level == 'manager') {
                $('.deleteorder-button').removeClass('oe_hidden');
            }
        },

        load_server_data_by_model: function (model) {
            let self = this;
            let tmp = {};
            let fields = typeof model.fields === 'function' ? model.fields(self, tmp) : model.fields;
            let domain = typeof model.domain === 'function' ? model.domain(self, tmp) : model.domain;
            let context = typeof model.context === 'function' ? model.context(self, tmp) : model.context || {};
            let ids = typeof model.ids === 'function' ? model.ids(self, tmp) : model.ids;
            let order = typeof model.order === 'function' ? model.order(self, tmp) : model.order;
            const loaded = new Promise(function (resolve, reject) {
                let params = {
                    model: model.model,
                    context: _.extend(context, session.user_context || {}),
                };
                if (model.ids) {
                    params.method = 'read';
                    params.args = [ids, fields];
                } else {
                    params.method = 'search_read';
                    params.domain = domain;
                    params.fields = fields;
                    params.orderBy = order;
                }
                rpc.query(params, {
                    timeout: 30000,
                    shadow: true,
                }).then(function (result) {
                    try {    // catching exceptions in model.loaded(...)
                        Promise.resolve(model.loaded(self, result, tmp)).then(function () {
                            resolve()
                            posbus.trigger('reload-orders', {})
                        }, function (err) {
                            if (err.message && err.message.code == -32098) {
                                self.alert_message({
                                    title: _t('Error'),
                                    body: _t('Your Server or Internet is Offline')
                                })
                            }
                            resolve(err)
                        });
                    } catch (err) {
                        if (err.message && err.message.code == -32098) {
                            self.alert_message({
                                title: _t('Error'),
                                body: _t('Your Server or Internet is Offline')
                            })
                        }
                        resolve(err)
                    }
                }, function (err) {
                    if (err.message && err.message.code == -32098) {
                        self.alert_message({
                            title: _t('Error'),
                            body: _t('Your Server or Internet is Offline')
                        })
                    }
                    resolve(err)
                });
            });
            return loaded;
        },

        on_removed_order: function(removed_order,index,reason){
            var order_list = this.get_order_list();
            if (this.env.pos.config.screen_type === 'cashier' && order_list.length > 0){
                // Set existing order as current order
                this.set_order(order_list[index] || order_list[order_list.length - 1], { silent: true });
            } else if( (reason === 'abandon' || removed_order.temporary) && order_list.length > 0){
                // when we intentionally remove an unfinished order, and there is another existing one
                this.set_order(order_list[index] || order_list[order_list.length - 1], { silent: true });
            } else{
                // when the order was automatically removed after completion,
                // or when we intentionally delete the only concurrent order
                this.add_new_order({ silent: true });
            }
        },

        covertCurrency(pricelist, price) {
            let baseCurrency = this.currency_by_id[this.config.currency_id[0]];
            if (pricelist.currency_id && baseCurrency && baseCurrency.id != pricelist.currency_id[0]) {
                let currencySelected = this.currency_by_id[pricelist.currency_id[0]];
                if (currencySelected && currencySelected['converted_currency'] != 0) {
                    price = (currencySelected['converted_currency'] * price);
                }
            }
            return price
        },
        async _check_connection(){
            const iot_url = this.env.pos.session.origin;
            const connection = new Session(void 0, iot_url, {
                use_cors: true
            });
            const pingServer = await connection.rpc('/pos/passing/login?_check_connection=1',{},{
                shadow: true, 
                timeout: 2000 // 2 seconds
            }).then(function (result) {
                return result
            }, function (error) {
                return false;
            })
            if(!pingServer){
                core.bus.trigger('connection_lost');
            }else{
                core.bus.trigger('connection_restored');
            }
            return pingServer
        },
        async _turn_on_save_order_to_server(){
            // TODO: set variable to False, so that the order can push to server
            if(this.env.pos.pushOrderInBackground){
                this.env.pos.pushOrderInBackground = false;
            }
        },
        getBrowserName() {
            if( navigator.userAgent.indexOf("Chrome") != -1 ) {
                return "Chrome";
            } else if( navigator.userAgent.indexOf("Opera") != -1 ) {
                return "Opera";
            } else if( navigator.userAgent.indexOf("MSIE") != -1 ) {
                return "IE";
            } else if( navigator.userAgent.indexOf("Firefox") != -1 ) {
                return "Firefox";
            } else {
                return "unknown";
            }
        },
        getCashierDeviceID() {
            // Generate Device ID with: Browser name + random + datetime
            function randomString(length) {
                let value = '';
                let s = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
                for (var i = length - 1; i >= 0; i--) {
                    value += s.charAt(Math.floor(Math.random() * s.length));
                }
                return value;
            }
            
            let device_id = this.env.pos.db.get_pos_device_id();
            if (!device_id){
                let browser_name = this.getBrowserName();
                device_id = browser_name + '.' + randomString(10) + '-' + moment().utc().format('YYYYMMDDHHmmss');
                this.env.pos.db.set_pos_device_id(device_id);
            }
            return device_id;
        },
        async log_cashier_pos(action) {
            let cashier = this.env.pos.get_cashier();
            let vals = {
                'cashier_id': cashier.id, // res.users
                'pos_config_id': this.env.pos.config.id, // res.users
                'device_id': this.getCashierDeviceID(),
            }
            rpc.query({
                model: 'pos.session',
                method: 'log_cashier_pos',
                args: [this.env.pos.pos_session.id, action, vals]
            }, {
                shadow: true,
                timeout: (1000  * 60 ) * 2 // 2 minutes
            }).then(function (result) {
               console.warn('[log_cashier_pos] result:', result)
            }, function (error) {
                console.error('[log_cashier_pos] ERROR :\n', error.message.message);
            });
        },

        async search_model_datas(method, vals){
            vals['pos_config_id'] = this.env.pos.config.id;
            let args = [[], vals];
            let result = await rpc.query({
                model: 'pos.cache.database',
                method: method, 
                args: args
            }, {
                shadow: true,
                timeout: 3000 // timeout 3 seconds
            }).then(function (response) {
                return response;
            }, function (error) {
                error.event.preventDefault(); // Stop default popup error
                if (error && error.message && error.message.code == -32098) {
                    console.error('[search_model_datas] ~ Server Offline -> ['+ method +']')
                } else {
                    console.error('[search_model_datas] ~ Error 403 -> ['+ method +']')
                }
                return Promise.resolve(null);
            });
            return Promise.resolve(result);
        },


        async action_download_paid_orders() {
            console.warn('[action_download_paid_orders] backup data');
            let paid_orders_json_data = localStorage.getItem(this.env.pos.db.name + '_orders');
            if(paid_orders_json_data === null){
                paid_orders_json_data = '[]';
            }
            let filename = `backup_paid_orders_${moment().format('YYYY-MM-DD-HH-mm-ss')}.json`;
            await this.download_data(filename, paid_orders_json_data);
        },
        async download_data(filename, text) {
            this.env.pos.alert_message({
                title: this.env._t('Warning'),
                body: this.env._t('Preparing download file, please wait for moment.')
            });

            const blob = new Blob([text]);
            const URL = window.URL || window.webkitURL;
            const url =  URL.createObjectURL(blob);
            const element = document.createElement('a');
            element.setAttribute('href', url);
            element.setAttribute('download', filename);
            element.style.display = 'none';
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
        },

    });


// TODO: PROBLEM IS ( if we have 100k, 500k or few millions products record ) and when change pricelist, take a lot times render qweb
// TODO SOLUTION: we force method get_price of product recordset to posmodel, see to method get_price of LoadModel.js
    const _super_Product = models.Product.prototype;
    models.Product = models.Product.extend({
        initialize: function (attr, options) {
            _super_Product.initialize.apply(this, arguments);
        },
        /*
            We not use exports.Product because if you have 1 ~ 10 millions data products
            Original function odoo will crashed browse memory
         */


        covertCurrency(pricelist, price) {
            let baseCurrency = this.pos.currency_by_id[this.pos.config.currency_id[0]];
            if (pricelist.currency_id && baseCurrency && baseCurrency.id != pricelist.currency_id[0]) {
                let currencySelected = this.pos.currency_by_id[pricelist.currency_id[0]];
                if (currencySelected && currencySelected['converted_currency'] != 0) {
                    price = (currencySelected['converted_currency'] * price);
                }
            }
            return price
        },

        get_product_bundles() {
            if(this.pos.product_bundle_by_product_tmpl_id && this.product_tmpl_id){
                let bundles = this.pos.product_bundle_by_product_tmpl_id[this.product_tmpl_id];
                if(bundles && bundles.length){
                    return bundles;
                }
            }
            return [];
        },

        get_qty_available() {
            let qty = 0;

            if(this.pos.stock_quant_by_product_id){
                let stock_locations = this.pos.db.get_pos_stock_locations();
                if(!stock_locations){
                    return 0;
                }

                let product_bundles = this.get_product_bundles();
                if(product_bundles.length){
                    // TODO: Get qty available to buy, base on the lowes qty available in the bundles
                    let qty_available_in_the_bundles = [];
                    for(let bundle of product_bundles){
                        let quantity = 0;
                        if(this.pos.stock_quant_by_product_id){
                            let stock_quants = this.pos.stock_quant_by_product_id[bundle.product_id[0]];
                            if(stock_quants){
                                for (let quant of stock_quants){
                                    if(stock_locations.includes(quant.location_id[0])){
                                        quantity += quant.quantity;
                                    }
                                } 
                            }
                        }
                        qty_available_in_the_bundles.push((quantity - (quantity%bundle.qty_uom) ) / bundle.qty_uom);
                    }
                    let qty_available = Math.min.apply(Math, qty_available_in_the_bundles);
                    qty_available = qty_available<0?0:qty_available;
                    qty += qty_available;
                }else{
                    let stock_quants = this.pos.stock_quant_by_product_id[this.id];
                    if(stock_quants){
                        for (let quant of stock_quants){
                            if(stock_locations.includes(quant.location_id[0])){
                                qty += quant.quantity;
                            }
                        } 
                    }
                }
            }
            return qty;
        },
        get_lot_qty_available(lot_names){
            let qty = 0;
            if(this.pos.stock_quant_by_product_id){
                let stock_quants = this.pos.stock_quant_by_product_id[this.id];
                if(!stock_quants){
                    return 0;
                }
                let stock_locations = this.pos.db.get_pos_stock_locations();
                if(!stock_locations){
                    return 0;
                }
                for (let quant of stock_quants){
                    if(stock_locations.includes(quant.location_id[0])){
                        if(quant.lot_id){
                            let lot_name = quant.lot_id[1];
                            if(lot_names.includes(lot_name)){
                                qty += quant.quantity;
                            }
                        }
                    }
                }
            }
            return qty;
        },
        get_stock_quant_by_lot_id(){
            let values = {};
            if(this.pos.stock_quant_by_product_id){
                let stock_quants = this.pos.stock_quant_by_product_id[this.id];
                if(!stock_quants){
                    return {};
                }
                let stock_locations = this.pos.db.get_pos_stock_locations();
                if(!stock_locations){
                    return {};
                }
                for (let quant of stock_quants){
                    if(stock_locations.includes(quant.location_id[0]) && quant.lot_id){
                        values[quant.lot_id[0]] = quant;
                    }
                }
            }
            return values;
        },
        get_lots_available(){
            // Todo: get list of lots/serial number available
            let self = this;
            let lots = [];
            let product_id = this.id;
            if(self.pos.lot_by_product_id){
                if(self.pos.lot_by_product_id[product_id]){
                    lots = self.pos.lot_by_product_id[product_id];
                }
            }

            const sortByCreateDate = str => {
                const [_, dd, mm, yyyy, hh, min, ss] = str.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
                return new Date(yyyy, mm - 1, dd, hh, min, ss)
            };
            lots.sort((a, b) => sortByCreateDate(b.create_date) - sortByCreateDate(a.create_date));

            console.warn('[get_lots_available]')
            let stock_quant_by_lot_id = self.get_stock_quant_by_lot_id();
            lots = lots.filter((lot) => {
                if(stock_quant_by_lot_id[lot.id] && stock_quant_by_lot_id[lot.id].quantity > 0){
                    lot.lot_qty_available = stock_quant_by_lot_id[lot.id].quantity;
                    return true;
                }
                if(lot.expiration_date){
                    let current_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                    let is_expired = moment(lot.expiration_date).isSameOrAfter(current_date);
                    return is_expired;
                }
                if (this.pos.config.allow_order_out_of_stock) {
                    return true;
                }
                return false;
            });

            return lots
        },

        get_price_with_tax: function (pricelist) {
            let self = this;
            let price;
            let price_pricelist;
            let tax_discount_policy = self.pos.company.tax_discount_policy;

            if (pricelist) {
                price = this.get_price_with_pricelist(pricelist, 1)[0];
                price_pricelist = price;

            } else {
                price = self['lst_price']
                price_pricelist = price;
            }

            // if (tax_discount_policy=='untax'){
            //     price = price_pricelist
            // }

            let taxes_id = self['taxes_id'];
            if (!taxes_id) {
                return price_pricelist;
            }
            let tax_amount = 0;
            var taxes =  this.pos.taxes;
            var taxes_ids = _.filter(self.taxes_id, t => t in self.pos.taxes_by_id);
            if(taxes_ids){
                var product_taxes = [];
                var taxtotal = 0;

                _(taxes_ids).each(function(el){
                    var tax = _.detect(taxes, function(t){
                        return t.id === el;
                    });
                    product_taxes.push.apply(product_taxes, [tax]);
                });
                product_taxes = _.uniq(product_taxes, function(tax) { return tax.id; });
                var orderline = Orderline_super;
                Orderline_super.pos = this.pos
                var tax_included = 0
                var all_taxes = orderline.compute_all(product_taxes, price, 1,0.0000001);
                _(all_taxes.taxes).each(function(tax) {
                    taxtotal += tax.amount;
                    var taxdetail =  taxes.filter(p => p.id == tax.id)  
                    if(taxdetail){
                        if(taxdetail[0].price_include){
                            tax_included+=tax.amount
                            if(tax_discount_policy=='untax'){
                                taxtotal -= tax.amount;
                            }
                        }
                    }
                });
                price = all_taxes['total_excluded'] + tax_included;
                if(this.pos.currency.rounding){
                    price = round_pr(all_taxes['total_excluded']+tax_included, this.pos.currency.rounding);
                }

            }

            if (taxtotal) {
                return price + taxtotal - tax_included
            } else {
                return price
            }
        },


        get_price_with_pricelist: function (pricelist, quantity, price_extra, uom_id) {
            let self = this;
            let pricelist_rule = false
            if (!quantity) {
                quantity = 1
            }
            if (!pricelist) {
                self.pos.db.set_cache_product_price('product.product', self.id, { price: self['lst_price'], rule: pricelist_rule });
                return [self['lst_price'],pricelist_rule];
            }
            if (pricelist['items'] == undefined) {
                self.pos.db.set_cache_product_price('product.product', self.id, { price: self['lst_price'], rule: pricelist_rule });
                return [self['lst_price'],pricelist_rule];
            }

            if(pricelist){
                let cache_price = self.pos.db.get_cache_product_price('product.product', self.id);
                if(cache_price){
                    return [cache_price.price, cache_price.rule];
                }
            }
            
            let date = moment(moment().utc().format('YYYY-MM-DD HH:mm:ss'), 'YYYY-MM-DD HH:mm:ss');
            let category_ids = [];
            let category = self.categ_id;
            while (category) {
                category_ids.push(category[0]);
                var categ_detail = self.pos.product_categories.filter(p => p.id == category[0])      
                if(categ_detail) {
                    var categ_parent = categ_detail[0].parent_id
                    category = categ_parent;
                }
                else{
                    category = false
                }
                    
            }
            let pos_category_ids = []
            let pos_category = self.pos_categ_id;
            while (pos_category) {
                pos_category_ids.push(pos_category[0]);
                var categ_detail = self.pos.pos_category_by_id[pos_category[0]]      
                if(categ_detail) {
                    var categ_parent = categ_detail.parent_id
                    pos_category = categ_parent;
                }
                else{
                    pos_category = false
                }
                    
            }
            if(self.multi_category){
                for (var i = 0; i < self.pos_categ_ids.length; i++) {
                    var itempci = self.pos_categ_ids[i];
                    pos_category = [itempci]
                    while (pos_category) {
                        pos_category_ids.push(pos_category[0]);
                        var categ_detail = self.pos.pos_category_by_id[pos_category[0]]      
                        if(categ_detail) {
                            var categ_parent = categ_detail.parent_id
                            pos_category = categ_parent;
                        }
                        else{
                            pos_category = false
                        }
                            
                    }
                }
            }

            var pricelist_items = [];
            let price = self['lst_price'];
            if(!uom_id){
                uom_id = this.uom_id[0]
            }

            for (let i = 0; i < pricelist.items.length; i++) {
                
                let item = pricelist.items[i];
                if(item.pricelist_uom_id && item.pricelist_uom_id[0]!=uom_id){
                    continue
                }
                if ((!item.date_start || moment(item.date_start).isSameOrBefore(date)) && (!item.date_end || moment(item.date_end).isSameOrAfter(date))){
                    if (quantity<item.min_quantity){
                        continue
                    }
                    if(item.applied_on=='0_product_variant' && item.product_id){
                        if(item.product_id[0] === self.id){
                            pricelist_items.push(item)
                        }
                    }
                    else if(item.applied_on=='1_product' && item.product_tmpl_id) {
                        if(item.product_tmpl_id[0] === self.product_tmpl_id){
                            pricelist_items.push(item)
                        }
                    }
                    else if(item.applied_on=='4_pos_category' && item.pos_category_id){
                        if(_.contains(pos_category_ids, item.pos_category_id[0])){
                            pricelist_items.push(item)
                        }
                    }
                    else if(item.applied_on=='2_product_category' && item.categ_id && self.categ_id) {
                        if(_.contains(category_ids, item.categ_id[0])){
                            pricelist_items.push(item)
                        }
                    }
                    else if(item.applied_on=='3_global'){
                        pricelist_items.push(item)
                    }
                }
                    
            }

            // pricelist_items = pricelist_items.filter(r => ((uom_id && r['uom_id'] && r['uom_id'][0] == uom_id) || (!uom_id && r['uom_id'] && this.uom_id && r['uom_id'][0] == this.uom_id[0]) || !r['uom_id']))
            // Re-ordering the pricelist_items based on min qty settings
            const pricelist_items_sort_by_min_qty = [];
            for (const object of pricelist_items) {
                pricelist_items_sort_by_min_qty.push(object);
            }
            pricelist_items_sort_by_min_qty.sort((a, b) => b['min_quantity'] - a['min_quantity']);
            pricelist_items = pricelist_items_sort_by_min_qty

            var new_pricelist_items = pricelist_items.filter(r => (r.applied_on=='0_product_variant'))
            if (new_pricelist_items.length==0){
                new_pricelist_items = pricelist_items.filter(r => (r.applied_on=='1_product'))
            }
            if (new_pricelist_items.length==0){
                new_pricelist_items = pricelist_items.filter(r => (r.applied_on=='4_pos_category'))
            }
            if (new_pricelist_items.length==0){
                new_pricelist_items = pricelist_items.filter(r => (r.applied_on=='2_product_category'))
            }
            if (new_pricelist_items.length==0){
                new_pricelist_items = pricelist_items.filter(r => (r.applied_on=='3_global'))
            }
            if(new_pricelist_items.length > 0){
                pricelist_items=new_pricelist_items
            }


            _.find(pricelist_items, function (rule) {
                if (rule.base === 'pricelist') {
                    price = self.get_price(rule.base_pricelist, quantity, uom_id);
                } else if (rule.base === 'standard_price') {
                    price = self.standard_price;
                }
                if (rule.compute_price === 'fixed') {
                    price = rule.fixed_price;
                    pricelist_rule = 'fixed'

                    if (price<rule.minimum_price && rule.minimum_price){
                        price = rule.minimum_price
                    }
                    if (price>rule.maximum_price && rule.maximum_price){
                        price = rule.maximum_price
                    }

                    return true;
                } else if (rule.compute_price === 'percentage') {
                    price = price - (price * (rule.percent_price / 100));

                    if (price<rule.minimum_price && rule.minimum_price){
                        price = rule.minimum_price
                    }
                    if (price>rule.maximum_price && rule.maximum_price){
                        price = rule.maximum_price
                    }

                    return true;
                } else {
                    let price_limit = price;
                    price = price - (price * (rule.price_discount / 100));
                    if (rule.price_round) {
                        price = round_pr(price, rule.price_round);
                    }

                    if (rule.price_surcharge && rule.type_surcharge == 'fixed') {
                        price += rule.price_surcharge;
                    }
                    if (rule.price_surcharge && rule.type_surcharge == 'percentage') {
                        var price_surcharge_percent = parseFloat((rule.price_surcharge/100).toFixed(2))
                        price += price * price_surcharge_percent;
                    }


                    if (rule.price_min_margin) {
                        let margin_amount = price_limit * rule.price_min_margin/100.0;
                        price = Math.max(price, price_limit + margin_amount);
                    }
                    if (rule.price_max_margin) {
                        let margin_amount = price_limit * rule.price_max_margin/100.0;
                        price = Math.min(price, price_limit + margin_amount);
                    }

                    if (price<rule.minimum_price && rule.minimum_price){
                        price = rule.minimum_price
                    }
                    if (price>rule.maximum_price && rule.maximum_price){
                        price = rule.maximum_price
                    }
                    
                    return true;
                }
                return false;
            });
            price = this.covertCurrency(pricelist, price);
            
            self.pos.db.set_cache_product_price('product.product', self.id, { price: price, rule: pricelist_rule });
            return [price,pricelist_rule];
        },

        get_price: function (pricelist, quantity, price_extra, uom_id) {
            var price = this.get_price_with_pricelist(pricelist, quantity, price_extra, uom_id)[0];
            return price;
        },

        get_name_variant: function () {
            var name_variant = this.display_name.replace(this.name+' ','')
            name_variant = name_variant.replace('(','')
            name_variant = name_variant.replace(')','')
            if (this.default_code){
                name_variant = name_variant.replace(this.default_code,'')
                name_variant = name_variant.replace('[','')
                name_variant = name_variant.replace(']','')
            }
            if (!this.attribute_line_ids.length || this.attribute_line_ids.length==0) {
                name_variant = ''
            }
            return name_variant
        },

        get_pricelist_item_applied: function (pricelist, quantity, uom_id) {
            if (!pricelist || pricelist['items'] == undefined) {
                return null;
            }
            let date = moment().startOf('day');
            let category_ids = [];
            let category = this.categ;
            while (category) {
                category_ids.push(category.id);
                category = category.parent;
            }
            let pos_category_ids = []
            let pos_category = this.pos_category;
            while (pos_category) {
                pos_category_ids.push(pos_category.id);
                pos_category = pos_category.parent;
            }
            let pricelist_items = [];
            for (let i = 0; i < pricelist.items.length; i++) {
                let item = pricelist.items[i];
                if ((!item.product_tmpl_id || item.product_tmpl_id[0] === this.product_tmpl_id) &&
                    (!item.product_id || item.product_id[0] === this.id) &&
                    (!item.categ_id || _.contains(category_ids, item.categ_id[0])) &&
                    (!item.pos_category_id || _.contains(pos_category_ids, item.pos_category_id[0])) &&
                    (!item.date_start || moment(item.date_start).isSameOrBefore(date)) &&
                    (!item.date_end || moment(item.date_end).isSameOrAfter(date))) {
                    pricelist_items.push(item)
                }
            }
            let ret_pricelist_item = null;
//            pricelist_items = pricelist_items.filter(pi => (((uom_id && pi['uom_id'] && pi['uom_id'][0] == uom_id)) || (!uom_id)) && pi['min_price'] != undefined && pi['max_price'] != undefined && pi['max_price'] >= pi['min_price'])
            pricelist_items = pricelist_items.filter(pi => ((uom_id && pi['pricelist_uom_id'] && pi['pricelist_uom_id'][0] == uom_id) || !pi['pricelist_uom_id']) && pi['min_price'] != undefined && pi['max_price'] != undefined && pi['max_price'] >= pi['min_price'])
            if (pricelist_items.length >= 1) {
                ret_pricelist_item = pricelist_items[0]
            }
            return ret_pricelist_item;
        },
        /*
            This function return product amount with default tax set on product > sale > taxes
         */
        // get_price_with_tax: function (pricelist) {
        //     let self = this;
        //     let price;
        //     if (pricelist) {
        //         price = this.get_price(pricelist, 1);
        //     } else {
        //         price = self['lst_price'];
        //     }
        //     let taxes_id = self['taxes_id'];
        //     if (!taxes_id) {
        //         return price;
        //     }
        //     let tax_amount = 0;
        //     let base_amount = price;
        //     if (taxes_id.length > 0) {
        //         for (let index_number in taxes_id) {
        //             let tax = self.pos.taxes_by_id[taxes_id[index_number]];
        //             if ((tax && tax.price_include) || !tax) {
        //                 continue;
        //             } else {
        //                 if (tax.amount_type === 'fixed') {
        //                     let sign_base_amount = base_amount >= 0 ? 1 : -1;
        //                     tax_amount += Math.abs(tax.amount) * sign_base_amount;
        //                 }
        //                 if ((tax.amount_type === 'percent' && !tax.price_include) || (tax.amount_type === 'division' && tax.price_include)) {
        //                     tax_amount += base_amount * tax.amount / 100;
        //                 }
        //                 if (tax.amount_type === 'percent' && tax.price_include) {
        //                     tax_amount += base_amount - (base_amount / (1 + tax.amount / 100));
        //                 }
        //                 if (tax.amount_type === 'division' && !tax.price_include) {
        //                     tax_amount += base_amount / (1 - tax.amount / 100) - base_amount;
        //                 }
        //             }
        //         }
        //     }
        //     if (tax_amount) {
        //         return price + tax_amount
        //     } else {
        //         return price
        //     }
        // },
    });
    let _super_Paymentline = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
        init_from_JSON: function (json) {
            let res = _super_Paymentline.init_from_JSON.apply(this, arguments);
            if (json.ref) {
                this.ref = json.ref
            }
            if (json.cheque_owner) {
                this.cheque_owner = json.cheque_owner
            }
            if (json.cheque_bank_id) {
                this.cheque_bank_id = json.cheque_bank_id
            }
            if (json.cheque_bank_account) {
                this.cheque_bank_account = json.cheque_bank_account
            }
            if (json.cheque_check_number) {
                this.cheque_check_number = json.cheque_check_number
            }
            if (json.cheque_card_name) {
                this.cheque_card_name = json.cheque_card_name
            }
            if (json.cheque_card_number) {
                this.cheque_card_number = json.cheque_card_number
            }
            if (json.cheque_card_type) {
                this.cheque_card_type = json.cheque_card_type
            }
            if (json.add_partial_amount_before) {
                this.add_partial_amount_before = json.add_partial_amount_before
            }
            if (json.voucher_id) {
                this.voucher_id = json.voucher_id
            }
            if (json.voucher_amount) {
                this.voucher_amount = json.voucher_amount
            }
            if (json.voucher_code) {
                this.voucher_code = json.voucher_code
            }
            return res
        },
        export_as_JSON: function () {
            let json = _super_Paymentline.export_as_JSON.apply(this, arguments);
            if (this.ref) {
                json['ref'] = this.ref;
            }
            if (this.cheque_owner) {
                json['cheque_owner'] = this.cheque_owner;
            }
            if (this.cheque_bank_id) {
                json['cheque_bank_id'] = this.cheque_bank_id;
            }
            if (this.cheque_bank_account) {
                json['cheque_bank_account'] = this.cheque_bank_account;
            }
            if (this.cheque_check_number) {
                json['cheque_check_number'] = this.cheque_check_number;
            }
            if (this.cheque_card_name) {
                json['cheque_card_name'] = this.cheque_card_name;
            }
            if (this.cheque_card_number) {
                json['cheque_card_number'] = this.cheque_card_number;
            }
            if (this.cheque_card_type) {
                json['cheque_card_type'] = this.cheque_card_type;
            }
            if (this.voucher_id) {
                json['voucher_id'] = this.voucher_id;
            }
            if (this.voucher_amount) {
                json['voucher_amount'] = this.voucher_amount;
            }
            if (this.voucher_code) {
                json['voucher_code'] = this.voucher_code;
            }
            if (this.add_partial_amount_before) {
                json['add_partial_amount_before'] = this.add_partial_amount_before;
            }
            return json
        },
        export_for_printing: function () {
            let datas = _super_Paymentline.export_for_printing.apply(this, arguments);
            if (this.ref) {
                datas['ref'] = this.ref
            }
            if (this.cheque_check_number) {
                datas['cheque_check_number'] = this.cheque_check_number
            }
            if (this.cheque_card_name) {
                datas['cheque_card_name'] = this.cheque_card_name
            }
            if (this.cheque_card_number) {
                datas['cheque_card_number'] = this.cheque_card_number
            }
            if (this.cheque_card_type) {
                datas['cheque_card_type'] = this.cheque_card_type
            }
            if (this.voucher_id) {
                datas['voucher_id'] = this.voucher_id
            }
            if (this.voucher_amount) {
                datas['voucher_amount'] = this.voucher_amount
            }
            if (this.voucher_code) {
                datas['voucher_code'] = this.voucher_code
            }
            if (this.add_partial_amount_before) {
                datas['add_partial_amount_before'] = this.add_partial_amount_before
            }
            return datas
        },
        set_reference: function (ref) {
            this.ref = ref;
            this.trigger('change', this)
        },
        get_rounding_payment: function () {
            var total_payment = 0
            var rounding = 0
            if(this.pos.company.apply_rounding_type && this.pos.company.rounding_method_id && this.pos.company.is_order_rounding){
                if(this.pos.company.apply_rounding_type == 'All Payment'){
                    total_payment = this.amount
                } 
                if(this.pos.company.apply_rounding_type == 'Cash Payment'){
                    if (this.payment_method.is_cash_count) {
                        total_payment = this.amount
                    }
                } 
                var rounding_calc = 0
                if (total_payment){
                    if(this.pos.cash_rounding[0].rounding < total_payment) {
                        if(this.pos.cash_rounding[0].rounding_method == 'DOWN') {
                            rounding_calc = Math.floor(total_payment / this.pos.cash_rounding[0].rounding) * this.pos.cash_rounding[0].rounding;
                        }
                        if(this.pos.cash_rounding[0].rounding_method == 'UP') {
                            rounding_calc = Math.ceil(total_payment / this.pos.cash_rounding[0].rounding) * this.pos.cash_rounding[0].rounding;
                        }
                        if(this.pos.cash_rounding[0].rounding_method == 'HALF-UP') {
                            rounding_calc = Math.round(total_payment / this.pos.cash_rounding[0].rounding) * this.pos.cash_rounding[0].rounding;  
                            
                        }
                        rounding = rounding_calc - total_payment
                    }
                    else{
                        rounding = this.pos.cash_rounding[0].rounding - total_payment
                    }
                }
            }
            return rounding
        },
        get_amount_with_rounding: function () {
            var rounding = this.get_rounding_payment()
            return this.amount + rounding
        },
        set_amount: function (value) {
            if (this.add_partial_amount_before) {
                return this.pos.alert_message({
                    title: _t('Warning'),
                    body: this.ref + _t(' . Not allow edit amount of this payment line. If you wanted edit, please remove this Line')
                })
            }
            if (this.payment_method && this.payment_method.pos_method_type == 'rounding') {
                return this.pos.alert_message({
                    title: _t('Warning'),
                    body: _t('Rounding Method not allow modifiers. Please set new Payment Method')
                })
            }
            _super_Paymentline.set_amount.apply(this, arguments);
            this.pos.trigger('refresh.customer.facing.screen');
        },
    });
})
;
