odoo.define('equip3_pos_masterdata.PosOrderDetail', function (require) {
    'use strict';

    const {getDataURLFromFile} = require('web.utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    const models = require('point_of_sale.models');
    const core = require('web.core');
    const qweb = core.qweb;
    const {Gui} = require('point_of_sale.Gui');
    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const OrderReceiptReprint = require('equip3_pos_masterdata.OrderReceiptReprint');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const ProductScreen = require('point_of_sale.ProductScreen');
    var SuperPosModel = models.PosModel.prototype;
    const _t = core._t;
    var SuperOrder = models.Order.prototype;
    var rpc = require('web.rpc');

    models.Order = models.Order.extend({
        initialize: function(attributes, options) {
            this.pos = options.pos;
            this.pos_config_branch_info = this.pos_config_branch_info || "";
            this.set_branch_data();
            SuperOrder.initialize.call(this, attributes, options);
        },

        set_branch_data: function() {
            var self = this;
            var config_pos_branchId = this.pos.config.pos_branch_id[0]
            var branch_data = []
            rpc.query({
               model: 'res.branch',
               method: 'search_read',
               domain: [['id', '=', config_pos_branchId]],
            })
            .then(function (result) {
                 if (result.length > 0) {
                  branch_data.push({
                        'branch_name' : result[0].name,
                        'telephone' : result[0].telephone,
                        'street' : result[0].street,
                        'street_2' : result[0].street_2,
                  });

                  self.pos_config_branch_info = branch_data;
                }
            })

        },

        init_from_JSON: function(json) {
    	   SuperOrder.init_from_JSON.apply(this,arguments);
           this.voucher_id = json.voucher_id
           this.voucher_amount = json.voucher_amount
           this.pos_config_branch_info = json.pos_config_branch_info;
        },

        export_as_JSON: function() {
            var self = this;
            var load = SuperOrder.export_as_JSON.call(this);
            SuperOrder.export_as_JSON.call(this);
            load.pos_config_branch_info = this.pos_config_branch_info;
            load.voucher_id = this.voucher_id
            load.voucher_amount = this.voucher_amount
            return load;
        },
    });

    models.load_models([{
        model: 'pos.payment',
        fields: ['id', 'name', 'payment_method_id', 'amount'],
        loaded: function(self, payments) {
            self.db.all_payments = payments;
            self.db.payment_by_id = {};
            payments.forEach(function(payment) {
                self.db.payment_by_id[payment.id] = payment;
                self.db.payment_by_id[payment.id]['journal_id'] = payment.payment_method_id
                delete self.db.payment_by_id[payment.id]['payment_method_id']
            });
        },
    }]);

    class PosOrderDetail extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('reprint_order', () => this.RePrintOrder());
            useListener('register_amount', () => this.registerAmount());
            useListener('edit_order', () => this.editOrder());
            useListener('cancel_order', () => this.cancelOrder());
            useListener('action_invoice', () => this.actionInvoice());
            useListener('download_invoice', () => this.downloadInvoice());
            useListener('return_order', () => this.returnOrder());
            useListener('refill_order', () => this.refillOrder());
            useListener('continue-order', () => this.updateOrder());
            useListener('covert_to_voucher', () => this.covertToVoucher());
            useListener('download_order_report', () => this.downloadOrderReport());
            useListener('download_delivery_report', () => this.downloadDeliveryReport());
            useListener('pay_receivable', () => this.payReceivable());
            useListener('multipay_receivable', () => this.multipayReceivable());
        }

        async payReceivable(){
            let partner_name = '';
            if(this.props.order.partner){
                partner_name = this.props.order.partner.name;
            }
            let payment_methods = this.env.pos.payment_methods.filter((p) => p.is_receivables == false && p.is_edc_bca == false);
            let {confirmed, payload: result} = await Gui.showPopup('PayReceivablePopUps', {
                payment_methods: payment_methods,
                amount_total: this.props.order.amount_total,
                partner_name: partner_name,

            });
            if (confirmed) {
                let response = await this.rpc({
                    model: 'pos.make.payment',
                    method: 'action_pay_receivable_frontend',
                    args: [[], {
                        'pos_order_id': this.props.order.id,
                        'payment_method_id': result.payment_method_id,
                        'amount': result.amount,
                    }],
                    context: {}
                });
            }
        }

        async multipayReceivable(){
            let self = this;
            let order = this.env.pos.db.order_by_id[this.props.order.id];
            console.log('Test:this.env.pos.payment_methods:', this.env.pos.payment_methods)
            let payment_methods = this.env.pos.payment_methods.filter((p)=>{{}
                if(typeof p.is_edc_bca != 'undefined'){
                    if(!p.is_edc_bca && !p.is_receivables){
                        return true;
                    }
                }
                if(!p.is_receivables){
                    return true;
                }
                return false;
            });
            let {confirmed, payload: result} = await Gui.showPopup('MultiPayReceivablePopUps', {
                order: order,
                payment_methods: payment_methods,
            });
            if(confirmed){
                if(result.data_order){
                    let data_order = result.data_order;
                    if(data_order.write_date != order.write_date){
                        self.env.pos.pos_order_model.loaded(self.env.pos, [data_order]);
                        self.env.pos.indexed_db.write('pos.order', [data_order]);
                    }

                    this.props.order.state = data_order.state;
                    
                    this.env.pos.db.order_by_id[data_order.id] = data_order;
                    if(result.payments){
                        this.env.pos.db.order_by_id[data_order.id]['payments'] = result.payments;
                        this.props.order['payments'] = result.payments;
                    }
                    var new_order = this.env.pos.db.order_by_id[this.props.order.id];
                    
                    this.props.order = new_order;
                    this.render()
                }
            }
        }

        async downloadOrderReport() {
            this.env.pos.do_action('equip3_pos_masterdata.report_pos_order', {
                additional_context: {
                    active_ids: [this.props.order.id],
                }
            });
        }

        async downloadDeliveryReport() {
            let picking_ids = await this.rpc({
                model: 'stock.picking',
                method: 'search_read',
                domain: [['pos_order_id', '=', this.props.order.id]],
                fields: ['id'],
                context: {
                    limit: 1
                }
            })
            if (picking_ids.length > 0) {
                this.env.pos.do_action('stock.action_report_picking', {
                    additional_context: {
                        active_ids: [picking_ids[0]['id']],
                    }
                });
            }
        }

        async covertToVoucher() {
            const order = this.props.order;
            const lines = order['lines'];
            this.env.pos.add_return_order(order, lines);
            const selectedOrder = this.env.pos.get_order();
            selectedOrder['name'] = this.env._t('Return and covert to Voucher of Order / ') + order['name']
            if (selectedOrder) {
                let number = await this.env.pos._getVoucherNumber()
                const {confirmed, payload} = await this.showPopup('PopUpPrintVoucher', {
                    title: this.env._t('Covert Return Order to Voucher'),
                    number: number,
                    value: -selectedOrder.get_total_with_tax(),
                    period_days: this.env.pos.config.expired_days_voucher,
                });
                if (confirmed) {
                    let order_ids = this.env.pos.push_single_order(selectedOrder, {})
                    console.log('[covertToVoucher] pushed last order to return order: ' + order_ids)
                    let values = payload.values;
                    let error = payload.error;
                    if (!error) {
                        let voucher = await this.rpc({
                            model: 'pos.voucher',
                            method: 'create_from_ui',
                            args: [[], values],
                            context: {}
                        })
                        let url_location = window.location.origin + '/report/barcode/EAN13/';
                        voucher['url_barcode'] = url_location + voucher['code'];
                        let report_html = qweb.render('VoucherCard', this.env.pos._get_voucher_env(voucher));
                        await this.rpc({
                            model: 'pos.order',
                            method: 'write',
                            args: [[this.props.order.id], {
                                'is_returned': true
                            }],
                            context: {}
                        })
      
                        var new_order = this.env.pos.db.order_by_id[this.props.order.id];
                        this.props.order = new_order;
                        this.trigger('close-temp-screen');
                        this.showScreen('ReportScreen', {
                            report_html: report_html
                        });
                        this.env.pos.do_action('equip3_pos_masterdata.report_pos_voucher_small_size', {
                            additional_context: {
                                active_ids: [voucher.id],
                            }
                        });
                    } else {
                        this.env.pos.alert_message({
                            title: this.env._t('Error'),
                            body: error,
                        })
                    }
                    selectedOrder.destroy({'reason': 'abandon'});
                }
            }
        }

        async updateOrder() {
            let order = this.props.order;
            let lines = order['lines'];
            if (!lines || lines.length == 0) {
                return this.env.pos.alert_message({
                    title: this.env._t('Error'),
                    body: this.env._t('Order Lines not found')
                })
            }
            let {confirmed, payload: confirm} = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Continue order or update Order'),
                body: this.env._t("You can change items in cart, payment amount .... But if you need add new Order, please Drop it. If finished update and need save again to Draft, you can click to Save to Draft Order on bottom of Product page !"),
            })
            if (confirmed) {
                const newOrder = this.env.pos.add_refill_order(order, lines);
                if (order.session_id[0] != this.env.pos.pos_session.id) {
                    let update = await this.rpc({
                        model: 'pos.order',
                        method: 'write',
                        args: [[order.id], {'session_id': this.env.pos.pos_session.id}],
                    })
                }
                newOrder['ean13'] = order['ean13']
                newOrder['name'] = order['pos_reference']
                newOrder['backend_id'] = order['id']
                for (let i = 0; i < order.payments.length; i++) {
                    let payment = order.payments[i]
                    let payment_method = _.find(this.env.pos.payment_methods, function (method) {
                        return payment['payment_method_id'][0] == method.id
                    });
                    if (payment_method) {
                        newOrder.add_paymentline(payment_method);
                        newOrder.selected_paymentline.set_amount(payment['amount']);
                    }
                }
                newOrder.trigger('change', newOrder)
                this.trigger('close-temp-screen');
            }
        }

        async refillOrder() {
            let order = this.props.order;
            let lines = order['lines'];
            if (!lines || lines.length == 0) {
                return this.env.pos.alert_message({
                    title: this.env._t('Error'),
                    body: this.env._t('Order Lines not found')
                })
            }
            this.env.pos.add_refill_order(order, lines);
            this.trigger('close-temp-screen');
        }

        async returnOrder() {
            var self = this;
            if (this.env.pos.config.validate_return) {
                let validate = await this.env.pos._validate_action(this.env._t('Need Approve of Your Manager'));
                if (!validate) {
                    return false;
                }
            }
            
            let order = this.props.order;
            let lines = order['lines'];
            if (!lines || lines.length == 0) {
                this.env.pos.alert_message({
                    title: this.env._t('Error'),
                    body: this.env._t('Order Lines not found')
                })
                return false
            }

            var order_list = self.env.pos.db.pos_all_orders;
            var order_line_data = self.env.pos.db.pos_all_order_lines;
            var order_id = this.id;
            var message = '';
            var non_returnable_products = false;
            var original_orderlines = [];
            var allow_return = true;
            if (order.return_status == 'Fully-Returned') {
                message = 'No items are left to return for this order!!'
                allow_return = false;
            }
            var all_pos_orders = self.env.pos.get('orders').models || [];
            var return_order_exist = _.find(all_pos_orders, function(pos_order) {
                if (pos_order.return_order_id && pos_order.return_order_id == order.id)
                    return pos_order;

            });
            if (return_order_exist) {
                self.showPopup('MyMessagePopup', {
                    'title': self.env._t('Refund Already In Progress'),
                    'body': self.env._t("Refund order is already in progress. Please proceed with Order Reference " + return_order_exist.sequence_number),
                });
            } else if (allow_return) {
                for (var i = 0; i < lines.length; i++) {
                    var line = lines[i];
                    var product = self.env.pos.db.get_product_by_id(line.product_id[0]);
                    if (product == null) {
                        non_returnable_products = true;
                        message = 'Some product(s) of this order are unavailable in Point Of Sale, do you wish to return other products?'
                    } else if (product.not_returnable) {
                        non_returnable_products = true;
                        message = 'This order contains some Non-Returnable products, do you wish to return other products?'
                    } else if (line.qty - line.line_qty_returned > 0)
                        original_orderlines.push(line);
                }

                if (original_orderlines.length == 0) {
                    this.showPopup('MyMessagePopup', {
                        'title': self.env._t('Cannot Return This Order!!!'),
                        'body': self.env._t("There are no returnable products left for this order. Maybe the products are Non-Returnable or unavailable in Point Of Sale!!"),
                    });
                }
                else {
                    this.showPopup('OrderReturnPopup', {
                        'orderlines': original_orderlines,
                        'order': order,
                        'is_partial_return': false,
                    });
                }
            } else {
                this.showPopup('MyMessagePopup', {
                    'title': self.env._t('Warning!!!'),
                    'body': self.env._t(message),
                });
            }
        }

        async downloadInvoice() {
            let order = this.props.order;
            let download_invoice = await this.env.pos.do_action('account.account_invoices', {
                additional_context: {
                    active_ids: [order.account_move[0]]
                }
            })
            return download_invoice
        }

        async orderToInvoice() {
            var self = this;
            let order = this.props.order;
            let result = await this.rpc({
                model: 'pos.order',
                method: 'action_pos_order_invoice',
                args: [[order.id]],
                context: {
                    'return_data': true
                }
            }).then(function (result) {
                return result;
            }, function (err) {
                return self.env.pos.query_backend_fail(err);
            })
            var new_order = this.env.pos.db.order_by_id[this.props.order.id];
            this.props.order = new_order;
            this.render();

            if(!this.props.order.account_move){
                if(result.data && !this.props.order.account_move){
                    this.props.order.account_move = [result.data.id, result.data.name];
                }
            }
            if(this.props.order.account_move){
                this.downloadInvoice();
            }
        }

        async actionInvoice() {
            var self = this;
            let order = this.props.order;
            if (order.account_move) {
                return this.downloadInvoice()
            } else {
                if (!order.partner_id) {
                    this.showPopup('ConfirmPopup', {
                        title: this.env._t('Alert'),
                        body: this.env._t('Please set customer to Order before do action invoice')
                    })
                    let {confirmed, payload: newClient} = await this.showTempScreen(
                        'ClientListScreen',
                        {client: null}
                    );
                    if (newClient) {
                        await this.rpc({
                            model: 'pos.order',
                            method: 'write',
                            args: [[order.id], {'partner_id': newClient.id}],
                        })
                        return this.orderToInvoice()
                    } else {
                        this.env.pos.alert_message({
                            title: this.env._t('Warning'),
                            body: this.env._t('Order missed Partner, please set Partner for this Order first')
                        })
                    }
                } else {
                    return this.orderToInvoice()
                }
            }
        }

        async cancelOrder() {
            var self = this;
            let order = this.props.order
            let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Warning'),
                body: this.env._t('Are you want cancel this Order')
            })
            if (confirmed) {
                await this.rpc({
                    model: 'pos.order',
                    method: 'action_pos_order_cancel',
                    args: [[order.id]],
                }).then(function (result) {
                    return result
                }, function (err) {
                    self.env.pos.query_backend_fail(err);
                    return false;
                })
                var new_order = this.env.pos.db.order_by_id[this.props.order.id];
                this.props.order = new_order;
                this.render()
            }
        }

        async registerAmount() {
            var self = this;
            let debit_amount = await this.rpc({ // todo: template rpc
                model: 'pos.order',
                method: 'get_debit',
                args: [[], this.props.order.id],
            }).then(function (debit_amount) {
                return debit_amount
            }, function (err) {
                return self.env.pos.query_backend_fail(err);
            })
            if (debit_amount != 0) {
                const {confirmed, payload: values} = await this.showPopup('PopUpRegisterPayment', {
                    order: this.props.order,
                    id: this.props.order.id,
                    title: this.env._t('Do Register Payment:' + this.props.order.pos_reference),
                    amount: debit_amount,
                    payment_reference: this.props.order.pos_reference,
                    payment_methods: this.env.pos.payment_methods.filter((p) => (p.journal && p.pos_method_type && p.pos_method_type == 'default') || (!p.journal && !p.pos_method_type)),
                    payment_date: new Date().toISOString().split('T')[0],
                })
                if (confirmed) {
                    let payment_val = values.values
                    let payment = {
                        pos_order_id: this.props.order.id,
                        payment_method_id: payment_val.payment_method_id,
                        amount: payment_val['amount'],
                        name: payment_val['payment_reference'],
                        payment_date: payment_val['payment_date']
                    };
                    if (!payment.payment_method_id) {
                        return this.env.pos.alert_message({
                            title: this.env._t('Error'),
                            body: this.env._t('Payment Mode is required`')
                        })
                    }
                    if (payment_val['amount'] > debit_amount) {
                        payment_val['amount'] = debit_amount
                    }
                    if (!payment.payment_date) {
                        payment.payment_date = moment().format('YYYY-MM-DD');
                    }
                    await this.rpc({
                        model: 'pos.make.payment',
                        method: 'add_payment',
                        args: [[], payment],
                    }).then(function (payment_id) {
                        return payment_id
                    }, function (err) {
                        return self.env.pos.query_backend_fail(err);
                    })
            
                    let new_order = this.env.pos.db.order_by_id[self.props.order.id];
                    this.props.order = new_order;
                    this.render()
                }
            } else {
                return this.env.pos.alert_message({
                    title: this.env._t('Warning'),
                    body: this.env._t('Order is Paid full or Your server offline, could not check Amount Debit of Order')
                })
            }
        }

        async RePrintOrder() {
            const order = await this.addBackOrder();
            setTimeout(function () {
                order.destroy({'reason': 'abandon'});
            }, 2000)
            if (this.env.pos.proxy.printer && this.env.pos.config.proxy_ip) {
                return this.env.pos.proxy.printer.printXmlReceipt(qweb.render('XmlReceipt', this.env.pos.getReceiptEnv()));
            } else {
                let orderRequest = null
                const fixture = document.createElement('div');
                const orderReceipt = new (Registries.Component.get(OrderReceiptReprint))(null, {order, orderRequest});
                await orderReceipt.mount(fixture);
                const receiptHtml = orderReceipt.el.outerHTML;
                await this.showScreen('ReportScreen', {
                    report_html: receiptHtml,
                    report_xml: null,
                    order:order,
                });
            }
        }

        async editOrder() {
            await this.addBackOrder(true);
            this.trigger('close-temp-screen');
        }

        async addBackOrder(draft) {
            const self = this
            const order = this.props.order;
            const lines = order['lines'];
            if (!lines || !lines.length) {
                return this.env.pos.alert_message({
                    title: this.env._t('Error'),
                    body: this.env._t('Your order is blank cart'),
                });
            }
            if (draft) {
                let setToDraft = await this.rpc({ // todo: template rpc
                    model: 'pos.order',
                    method: 'write',
                    args: [[order.id], {'state': 'draft'}],
                })
                if (!setToDraft) {
                    return;
                }
            }
            const paymentLines = order['payments']
            var new_order = new models.Order({}, {pos: this.env.pos, temporary: true});
            var partner = order['partner_id'];
            if (partner) {
                var partner_id = partner[0];
                var partner = this.env.pos.db.get_partner_by_id(partner_id);
                new_order.set_client(partner);
            }
            for (var i = 0; i < lines.length; i++) {
                var line = lines[i];
                if(line.product_id){
                    var product = this.env.pos.db.get_product_by_id(line.product_id[0]);
                    if (!product) {
                        continue
                    } else {
                        var new_line = new models.Orderline({}, {
                            pos: this.env.pos,
                            order: new_order,
                            product: product
                        });
                        new_line.set_quantity(line.qty, 'keep price, for re-print receipt');
                        new_order.orderlines.add(new_line);
                        if (line.discount) {
                            new_line.set_discount(line.discount);
                        }
                        if (line.discount_reason) {
                            new_line.discount_reason = line.discount_reason;
                        }
                        if (line.promotion) {
                            new_line.promotion = line.promotion;
                        }
                        if (line.promotion_reason) {
                            new_line.promotion_reason = line.promotion_reason;
                        }
                        if (line.note) {
                            new_line.set_line_note(line.note);
                        }
                        if (line.plus_point) {
                            new_line.plus_point = line.plus_point;
                        }
                        if (line.redeem_point) {
                            new_line.redeem_point = line.redeem_point;
                        }
                        if (line.uom_id) {
                            var uom_id = line.uom_id[0];
                            var uom = this.env.pos.uom_by_id[uom_id];
                            if (uom) {
                                new_line.set_unit(uom_id);
                            }
                        }
                        if (line.notice) {
                            new_line.notice = line.notice;
                        }
                        if (line.pos_coupon_reward_description) {
                            new_line.pos_coupon_reward_description = line.pos_coupon_reward_description;
                        }
                        if (line.pos_coupon_reward_discount) {
                            new_line.pos_coupon_reward_discount = line.pos_coupon_reward_discount;
                        }
                        new_line.set_unit_price(line.price_unit);
                    }
                }
            }
            var orders = this.env.pos.get('orders');
            orders.add(new_order);
            new_order['uid'] = order['pos_reference'].split(' ')[1];
            new_order['pos_reference'] = order['pos_reference'];
            new_order['create_date'] = order['create_date'];
            new_order['ean13'] = order['ean13'];
            new_order['name'] = order['pos_reference'];
            new_order['date_order'] = order['date_order'];
            new_order['plus_point'] = order['plus_point'];
            new_order['redeem_point'] = order['redeem_point'];
            if(paymentLines){
                paymentLines.forEach(p => {
                    let payment_method = self.env.pos.payment_methods.find(m => m.id == p.payment_method_id[0])
                    if (payment_method) {
                        new_order.add_paymentline(payment_method)
                        new_order.selected_paymentline.set_amount(p.amount)
                    }
                })
            }
            return new_order;
        }

        get partnerImageUrl() {
            const order = this.props.order;
            const partner = order.partner_id
            if (partner) {
                return `/web/image?model=res.partner&id=${partner[0]}&field=image_128&unique=1`;
            } else {
                return false;
            }
        }

        get OrderUrl() {
            const order = this.props.order;
            return window.location.origin + "/web#id=" + order.id + "&view_type=form&model=pos.order";
        }
    }

    PosOrderDetail.template = 'PosOrderDetail';

    Registries.Component.add(PosOrderDetail);

    return PosOrderDetail;
});
