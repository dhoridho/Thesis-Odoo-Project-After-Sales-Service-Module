odoo.define('equip3_pos_general.PosOrderDetail', function (require) {
    'use strict';

    const PosOrderDetail = require('equip3_pos_masterdata.PosOrderDetail');
    const Orderline = require('point_of_sale.Orderline');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    const models = require('point_of_sale.models');
    const framework = require('web.framework');
    const {Gui} = require('point_of_sale.Gui');
    const time = require('web.time');
    const { Component } = owl;
    const current = Component.current;
    const core = require('web.core');
    const { useState } = owl.hooks;
    const _t = core._t;

    const {getDataURLFromFile} = require('web.utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const qweb = core.qweb;
    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const OrderReceiptReprint = require('equip3_pos_masterdata.OrderReceiptReprint');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const ProductScreen = require('point_of_sale.ProductScreen');
    var SuperPosModel = models.PosModel.prototype;


    models.load_fields('product.product', 'not_returnable','is_can_be_po');
    models.load_fields('pos.config', ['enable_void_time','void_time', 'void_order_pins', 'void_order_line_pins']);

    const GeneralOrderReceiptReprint = (OrderReceiptReprint) =>
        class extends OrderReceiptReprint {
        get receipt_template() {
            //TO DO: Get masterdata receipt template
            var receipt_templates = this.env.pos.db.receipt_templates
            var pos_receipt_template_id = this.env.pos.config.pos_receipt_template_id
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
                }
            }
            return pos_receipt_template;
        }
    }

    var super_order_model = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            super_order_model.initialize.apply(this, arguments);
            this.void_order_id = false;
            this.void_state = '';
            this.rounding_payment = 0
        },
        init_from_JSON: function (json) {
            let res = super_order_model.init_from_JSON.apply(this, arguments);
            this.void_order_id = json.void_order_id ? json.void_order_id : false;
            this.void_state = json.void_state ? json.void_state : '';
            this.rounding_payment = json.rounding_payment ? json.rounding_payment : '';
            return res;
        },
        export_as_JSON: function () {
            const json = super_order_model.export_as_JSON.apply(this, arguments);
            json.void_order_id = this.void_order_id ? this.void_order_id : false;
            json.void_state = this.void_state ? this.void_state : '';
            json.rounding_payment = this.rounding_payment ? this.rounding_payment : '';
            return json;
        },
        async suggestItems(product) {
            let order = this;
            let crossItems = this.pos.cross_items_by_product_tmpl_id[product.product_tmpl_id];
            if (!crossItems || crossItems.length == 0) {
                return this.pos.alert_message({
                    title: _t('Error'),
                    body: product.display_name + _t(' not active feature Cross Selling')
                })
            }
            let {confirmed, payload: results} = await Gui.showPopup('CrossSalePopUps', {
                title: _t('Product Suggestions'),
                items: crossItems,
            })
            if (confirmed) {
                let selectedCrossItems = results.items;
                for (let index in selectedCrossItems) {
                    let item = selectedCrossItems[index];
                    let product = this.pos.db.get_product_by_id(item['product_id'][0]);
                    if (product) {
                        if (!product) {
                            continue
                        }
                        let price = item['list_price'];
                        let discount = 0;
                        if (item['discount_type'] == 'fixed') {
                            price = price - item['discount']
                        }
                        if (item['discount_type'] == 'percent') {
                            discount = item['discount']
                        }
                        
                        var exist_in_orderline = false;
                        var is_pos_groupable = false;
                        if(order.get_orderlines().length > 1){
                            for (var i = 0; i < order.orderlines.length; i++) {
                                if(order.get_orderlines().at(i).product.id == product.id){
                                    let orderline = order.get_orderlines().at(i);
                                    exist_in_orderline = orderline;
                                    is_pos_groupable = orderline.get_unit().is_pos_groupable;
                                }
                            }
                        }

                        if(!is_pos_groupable){
                            exist_in_orderline = false
                        }

                        if(!exist_in_orderline){
                            order.add_product(product, {
                                quantity: item['quantity'],
                                price: price,
                                merge: false,
                                extras: {
                                    is_from_cross_sale: true,
                                }
                            });
                        }
                        
                        if(exist_in_orderline){
                           exist_in_orderline.set_quantity( exist_in_orderline.get_quantity() + 1);
                        }

                        if (discount > 0) {
                            order.get_selected_orderline().set_discount(discount)
                        }
                    } else {
                        this.pos.chrome.showNotification(item['product_id'][1], _t('Not available in POS'))
                    }
                }
            }
        },
    });

    models.PosModel = models.PosModel.extend({
        set_order: function(order) {
            SuperPosModel.set_order.call(this, order);
            if (order) {
                if (order != null && !order.is_return_order || order.is_exchange_order) {
                    $("#cancel_refund_order").hide();
                } else {
                    $("#cancel_refund_order").show();
                }
            };
        },
    });

    async function askPin(void_pin) {
        if (void_pin.includes(',')) {
            var void_pins = void_pin.split(',');
        } else {
            var void_pins = [void_pin];
        }
        const { confirmed, payload: inputPin } = await Gui.showPopup('NumberPopup', {
            isPassword: true,
            title: _t('Password ?'),
            startingValue: null,
        });

        if (!confirmed) return false;
        if (void_pins.includes(inputPin)) {
            return true;
        } else {
            await Gui.showPopup('ErrorPopup', {
                title: _t('Incorrect Password'),
            });
            return false;
        }
    }
    const GeneralOrderline = (Orderline) =>
        class extends Orderline {

            async _removeOrderLine() {
                // Validate void line PIN
                if (this.env.pos.config.void_order_line_pins) {
                    let auth = await askPin.call(current, this.env.pos.config.void_order_line_pins);
                    if (!auth) return;
                }

                let {confirmed, payload: note} = await this.showPopup('CancelReasonPopup', {
                    title: this.env._t('Cancel Reason'),
                })
                if (confirmed) {
                    const selectedOrder = this.env.pos.get_order()
                    const result = await this.env.services.rpc({
                        model: "product.cancel",
                        method: "create",
                        args: [{
                            'order_ref': selectedOrder.name,
                            'product_id': selectedOrder.selected_orderline.product.id,
                            'qty': selectedOrder.selected_orderline.quantity,
                            'uom_id': selectedOrder.selected_orderline.product.uom_id[0],
                            'src_location_id': selectedOrder.location ? selectedOrder.location.id : false ,
                            'cashier_id': selectedOrder.pos.user.id,
                            'cancel_reason': note,
                        }]
                    });
                    if(this.env.pos.config.validate_by_manager){
                        let validate = await this.env.pos._validate_action(this.env._t('Cancel Item'));
                        if (!validate) {
                            return false;
                        }
                    }
                    this.props.line.set_quantity(0);
                    this.props.line.set_item_state('cancelled');
                    this.env.pos.alert_message({
                        title: this.env._t('Warning'),
                        body: this.props.line.product.name + this.env._t(' just cancel out of Cart.')
                    })
                }
            }
        }

    // MyMessagePopup Popup
    class MyMessagePopup extends AbstractAwaitablePopup {}
    MyMessagePopup.template = 'MyMessagePopup';
    MyMessagePopup.defaultProps = { title: 'Message', value:'' };
    Registries.Component.add(MyMessagePopup);

    class OrderReturnPopup extends AbstractAwaitablePopup {
        click_return_order(event){
            var self = this;
            var all = $('.return_qty');
            var return_dict = {};
            var return_entries_ok = true;

            var current_order = self.env.pos.get_order();
            var currentDate = new Date();
            var return_period = this.env.pos.config.pos_order_period_return_days * 24 * 60 * 60 * 1000; // 30 days in milliseconds
            console.warn('[click_return_order] current_order:', current_order)

            if(!current_order){
                return this.showPopup('ErrorPopup', {
                    title: this.env._t('Warning'),
                    body: this.env._t('Cannot Return Order now, Please try again later!')
                })
            }
            if (currentDate.getTime() - current_order.creation_date.getTime() > return_period) {
                return this.showPopup('ErrorPopup', {
                    title: this.env._t('Error'),
                    body: this.env._t('This Order has Exceeded the Return Period')
                })
            } else if (currentDate.getTime() - current_order.creation_date.getTime() < return_period) {
                $.each(all, function(index, value) {
                    var input_element = $(value).find('input');
                    var line_quantity_remaining = parseFloat(input_element.attr('line-qty-remaining'));
                    var line_id = parseFloat(input_element.attr('line-id'));
                    var qty_input = parseFloat(input_element.val());
                    if (!$.isNumeric(qty_input) || qty_input > line_quantity_remaining || qty_input < 0) {
                        return_entries_ok = false;
                        input_element.css("background-color", "#ff8888;");
                        setTimeout(function() {
                            input_element.css("background-color", "");
                        }, 100);
                        setTimeout(function() {
                            input_element.css("background-color", "#ff8888;");
                        }, 200);
                        setTimeout(function() {
                            input_element.css("background-color", "");
                        }, 300);
                        setTimeout(function() {
                            input_element.css("background-color", "#ff8888;");
                        }, 400);
                        setTimeout(function() {
                            input_element.css("background-color", "");
                        }, 500);
                    }

                    if (qty_input == 0 && line_quantity_remaining != 0 && !self.props.is_partial_return) {
                        self.props.is_partial_return = true;
                    } else if (qty_input > 0) {
                        return_dict[line_id] = qty_input;

                        if (qty_input > line_quantity_remaining) {
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Warning!'),
                                body: this.env._t('Please Check the Returned Amount, There Input Quantity Exceeded Quantity Remaining')
                            })
                        }

                        if (qty_input < 0) {
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Warning!'),
                                body: this.env._t('Please Check the Returned Amount, There Input Quantity Must Not Lower Than 0')
                            })
                        }
                        
                        var request = new XMLHttpRequest();
                        request.open("POST", "/pos/update_return_qty", true);
                        request.setRequestHeader("Content-Type", "application/json");

                        // Prepare the data to be sent to the controller
                        var data = {
                            line_id : line_id,
                            input_qty : qty_input,
                        };

                        // Send the data as JSON
                        request.send(JSON.stringify(data));

                        if (line_quantity_remaining != qty_input && !self.props.is_partial_return) {
                            self.props.is_partial_return = true;
                            self.props.returned_qty = qty_input;
                        } else if (!self.props.is_partial_return) {
                            self.props.is_partial_return = false;
                        }
                    }
                });
                if (return_entries_ok){
                    console.warn('[click_return_order] return_dict:', return_dict);
                    self.create_return_order(return_dict);
                }
            }
        }
        async create_return_order(return_dict){
            var self = this;
            var order = self.props.order;
            var orderlines = self.props.orderlines;
            const lines = order['lines'];
            var newlines = []

            if (Object.keys(return_dict).length > 0) {
                self.env.pos.add_new_order()
                this.cancel();
                let refund_order = self.env.pos.get_order();
                refund_order.is_return_order = true;
                refund_order.set_client(self.env.pos.db.get_partner_by_id(order.partner_id[0]));

                Object.keys(return_dict).forEach(function(line_id) {
                    let line_return = self.env.pos.db.line_by_id[line_id];
                    let product = self.env.pos.db.get_product_by_id(line_return.product_id[0]);
                    refund_order.add_product(product, { 
                        quantity: -1 * parseFloat(return_dict[line_id]), 
                        price: line_return.price_unit,
                        discount: line_return.discount, 
                    });
                    let orderline = refund_order.selected_orderline;
                    orderline.original_line_id = line_return.id;
                    
                    if(line_return.promotion){
                        refund_order._apply_promotion_to_orderlines(
                            [orderline], 
                            line_return.promotion_id[0], // promotion_id
                            line_return.promotion_reason, 
                            0, 
                            line_return.discount
                        ) 
                    }
                });

                if (self.props.is_partial_return) {
                    refund_order.return_status = 'Partially-Returned';
                    refund_order.return_order_id = order.id;
                } else {
                    refund_order.return_status = 'Fully-Returned';
                    refund_order.return_order_id = order.id;
                }

                const selectedOrder = this.env.pos.get_order();
                if(!selectedOrder){
                    self.pos.set_order(refund_order);
                    selectedOrder = this.env.pos.get_order();
                }
                let currency_order = selectedOrder.currency

                this.trigger('close-temp-screen');

                let return_payment_method_ids = order.payments.map((p)=>p.payment_method_id[0]);
                let vals = { 'return_payment_method_ids': return_payment_method_ids, }

                if (this.env.pos.config.required_reason_return) {
                    let {confirmed, payload: note} = await this.showPopup('TextAreaPopup', {
                        title: this.env._t('Add some notes why customer return products ?'),
                    })
                    if (confirmed) {
                        selectedOrder.set_note(note);
                        selectedOrder.submitOrderToBackEnd(vals);
                        return true
                    } else {
                        return this.env.pos.alert_message({
                            title: this.env._t('Warning'),
                            body: this.env._t('Return Products/Order is required')
                        })
                    }
                } else {
                    const selectionList = this.env.pos.payment_methods.map((p) => ({
                        id: p.id,
                        item: p,
                        name: p.name,
                        // selected: return_payment_method_ids.includes(p.id),
                    }))
                    let {confirmed, payload: selectedItems} = await Gui.showPopup(
                        'PopUpSelectionBox',
                        {
                            title: _t('If have not Exchange Products, Please select one Payment Method for full fill Amount of Order: ') + this.env.pos.format_currency(selectedOrder.get_total_with_tax(),undefined,currency_order),
                            items: selectionList,
                            onlySelectOne: true,
                        }
                    );
                    if (confirmed && selectedItems['items'].length > 0) {
                        const paymentMethod = selectedItems['items'][0]['item']
                        selectedOrder.paymentlines.models.forEach(function (p) {
                            selectedOrder.remove_paymentline(p)
                        })
                        selectedOrder.add_paymentline(paymentMethod);

                        const paymentLine = selectedOrder.selected_paymentline;
                        paymentLine.set_amount(selectedOrder.get_total_with_tax());
                        selectedOrder.trigger('change', selectedOrder);

                        let order_ids = this.env.pos.push_single_order(selectedOrder, {})
                        console.log('{submitOrderToBackEnd} pushed succeed order_ids: ' + order_ids)
                        return this.env.pos.chrome.showScreen('ReceiptScreen');
                    } else {
                        selectedOrder.is_return = false
                        selectedOrder.trigger('change', selectedOrder);
                    }
                    return true
                }
            } else {
                $(".popup input").css("background-color", "#ff8888;");
                setTimeout(function() {
                    $(".popup input").css("background-color", "");
                }, 100);
                setTimeout(function() {
                    $(".popup input").css("background-color", "#ff8888;");
                }, 200);
                setTimeout(function() {
                    $(".popup input").css("background-color", "");
                }, 300);
                setTimeout(function() {
                    $(".popup input").css("background-color", "#ff8888;");
                }, 400);
                setTimeout(function() {
                    $(".popup input").css("background-color", "");
                }, 500);
            }
        };

        // ORIGINAL CODE
        //     if (Object.keys(return_dict).length > 0) {
        //         self.env.pos.add_new_order()
        //         this.cancel();
        //         var refund_order = self.env.pos.get_order();
        //         refund_order.is_return_order = true;
        //         refund_order.set_client(self.env.pos.db.get_partner_by_id(order.partner_id[0]));
        //         Object.keys(return_dict).forEach(function(line_id) {
        //             var line = self.env.pos.db.line_by_id[line_id];
        //             var product = self.env.pos.db.get_product_by_id(line.product_id[0]);
        //             refund_order.add_product(product, { quantity: -1 * parseFloat(return_dict[line_id]), price: line.price_unit, discount: line.discount });
        //             refund_order.selected_orderline.original_line_id = line.id;
        //         });
        //         if (self.props.is_partial_return) {
        //             refund_order.return_status = 'Partially-Returned';
        //             refund_order.return_order_id = order.id;
        //         } else {
        //             refund_order.return_status = 'Fully-Returned';
        //             refund_order.return_order_id = order.id;
        //         }
        //         // self.pos.set_order(refund_order);
        //         self.showScreen('PaymentScreen');
        //     } else {
        //         $(".popup input").css("background-color", "#ff8888;");
        //         setTimeout(function() {
        //             $(".popup input").css("background-color", "");
        //         }, 100);
        //         setTimeout(function() {
        //             $(".popup input").css("background-color", "#ff8888;");
        //         }, 200);
        //         setTimeout(function() {
        //             $(".popup input").css("background-color", "");
        //         }, 300);
        //         setTimeout(function() {
        //             $(".popup input").css("background-color", "#ff8888;");
        //         }, 400);
        //         setTimeout(function() {
        //             $(".popup input").css("background-color", "");
        //         }, 500);
        //     }
        // }


        click_complete_return(event){
            var self = this;
            var all = $('.return_qty');
            $.each(all, function(index, value) {
                var line_quantity_remaining = parseFloat($(value).find('input').attr('line-qty-remaining'));
                $(value).find('input').val(line_quantity_remaining);
            }); 
        }
    }
    OrderReturnPopup.template = 'OrderReturnPopup';
    OrderReturnPopup.defaultProps = { title: 'Message', value:'' };
    Registries.Component.add(OrderReturnPopup);


    const GeneralPosOrderDetail = (PosOrderDetail) =>
        class extends PosOrderDetail {
            constructor() {
                super(...arguments)
                useListener('void_order', () => this.VoidOrder());

                this.void_order_sync = useState({ state: ''  });
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
                    await this.showTempScreen('ReportScreen', {
                        report_html: receiptHtml,
                        report_xml: null,
                        order:order,
                        open_from: 'reprint_order',
                    });
                }
            }

            async VoidOrder() {
                let self = this;
                if (this.void_order_sync.state == 'connecting'){
                    return;
                }
                let order = this.props.order;
                var name_void = 'VOID/' + order['name'];
                var void_exist = _.filter(this.env.pos.db.pos_all_orders, function (line) {
                    return line.pos_reference.indexOf(name_void) >= 0;
                });
                if (void_exist.length > 0){
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Warning !'),
                        body: this.env._t("This order already void before.")
                    });
                }

                // Void Limit Time Settings
                if (this.env.pos.config.enable_void_time) {
                    let current_time = time.time_to_str(new Date());
                    let order_time = time.time_to_str(new Date(order.date_order));
                    let diff = Math.abs(new Date() - new Date(order.date_order));
                    let diff_minutes = Math.floor((diff/1000)/60);
                    if (diff_minutes >= this.env.pos.config.void_time) {
                        return this.env.pos.alert_message({
                            title: this.env._t('Error'),
                            body: this.env._t('Void Time Limit Exceeded!\nMax Void Time is '+this.env.pos.config.void_time+ ' minutes, but the pos order is created '+diff_minutes+':00 minutes ago.'),
                        })
                    }
                }
                let lines = order['lines'];
                if (!lines || lines.length == 0) {
                    return this.env.pos.alert_message({
                        title: this.env._t('Error'),
                        body: this.env._t('Order Lines not found!'),
                    })
                }

                // Validate orderline
                for(let line of lines){
                    let product = this.env.pos.db.get_product_by_id(line.product_id[0]);
                    if (!product) {
                        return Gui.showPopup('ConfirmPopup', {
                            title: _t('Warning'),
                            body: _t('Product ' + line.product_id[1] + '('+line.product_id[0]+')' + ' not available in POS, it not possible made return')
                        })
                    }
                    if (line.is_return) {
                        return Gui.showPopup('ConfirmPopup', {
                            title: _t('Warning'),
                            body: _t('This order is order return before, it not possible return again')
                        })
                    }
                    if (line.promotion_id){
                        let promotion = this.env.pos.promotion_by_id[line.promotion_id[0]];
                        if (!promotion) {
                            return Gui.showPopup('ConfirmPopup', {
                                title: _t('Warning'),
                                body: _t('Promotion ' + line.promotion_id[1] + '('+line.promotion_id[0]+')' + ' not available in POS, it not possible made return')
                            })
                        }
                    }
                }

                // Check already void
                if (order.void_state){
                    return this.env.pos.alert_message({
                        title: this.env._t('Error'),
                        body: this.env._t('This order is already void!'),
                    })
                }

                // Check already Posted
                if(order.state == 'done'){
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Warning !'),
                        body: this.env._t('Cannot void when the order already Posted.')
                    })
                }

                // Validate void PIN
                if (this.env.pos.config.void_order_pins) {
                    let auth = await askPin.call(current, this.env.pos.config.void_order_pins);
                    if (!auth) return;
                }

                // Validate Payment
                let payments = this.env.pos.pos_payment_by_order_id[order.id];
                if(payments.length){
                    let uniquePaymentIds = [];
                    payments = [...new Set(payments)].filter(e=>{if(!uniquePaymentIds.includes(e.id)){uniquePaymentIds.push(e.id);return true;}return false;});
                }
                if (!payments.length){
                    return Gui.showPopup('ConfirmPopup', { title: 'Warning', body: 'Payment is undefined' });
                }
                for(let payment of payments){
                    let payment_method = this.env.pos.payment_methods_by_id[payment.payment_method_id[0]];
                    if(!payment_method){
                        return Gui.showPopup('ConfirmPopup', { title: 'Warning', body: 'Payment is undefined -' + payment.payment_method_id[1] });
                    }
                }

                if(this.env.pos.config.module_pos_restaurant && this.env.pos.config.is_table_management){
                    if(!this.env.pos.table){
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t('Please select table first before continue!')
                        });
                        return;
                    }
                }

                console.warn('[VoidOrder] order:', order);
                console.warn('[VoidOrder] lines:', lines);
                let {confirmed, payload: confirm} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Void Order'),
                    body: this.env._t("Are you sure to void this order? This action will create reversal order in backend."),
                })
                if (confirmed) {
                    await this.create_void_order(order, lines);
                    self.trigger('close-temp-screen');
                    return;

                    /** POS VOID Online Mode
                    order['void_state'] = 'Void';
                    this.void_order_sync.state = 'connecting';
                    const pingServer = await this.env.pos._check_connection();
                    if (!pingServer) {
                        order['void_state'] = '';
                        this.void_order_sync.state = 'error';
                        return await this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t('Your Internet or Hashmicro Server Offline'),
                        });
                    }

                    let order_obj = await new models.Order({}, {pos: self.env.pos}); 
                    let values = {
                        config_id: self.env.session.config.id,
                        session_id: self.env.session.config.pos_session_id,
                        ean13: order_obj.ean13,
                        cid: order_obj.cid,
                        uid: order_obj.uid,
                    }
                    let result = await self.rpc({
                        model: 'pos.order',
                        method: 'create_void_order',
                        args: [[order.id], values],
                        context: {
                            shadow: true,
                            timeout: 600000 // 10 minutes
                        }
                    }).then(function (result) {
                        return result;
                    }).guardedCatch(function (error) {
                        order['void_state'] = '';
                        self.void_order_sync.state = 'error';
                        console.error('[VoidOrder] ~ create_void_order Error:', error)
                        return null;
                    });
                    console.warn('[VoidOrder] result: ', result);

                    if (result.status == 'failed'){
                        order['void_state'] = '';
                        self.void_order_sync.state = 'error';
                        return self.showPopup('ErrorPopup', {
                            title: self.env._t('Error'),
                            body: self.env._t(result.error_message),
                        });
                    }
                    if (result.status == 'success'){
                        order['void_state'] = 'Void';
                        self.void_order_sync.state = 'done';
                        order_obj.destroy({'reason':'abandon'});
                    }
                    self.trigger('close-temp-screen');
                    **/
                }
            }

            async create_void_order(order_return, lines_return) {
                let self = this;
                let return_order_id = order_return['id'];

                let void_order = new models.Order({}, {pos: this.env.pos});
                void_order['is_return'] = true;
                void_order['return_order_id'] = return_order_id;
                void_order['void_order_id'] = return_order_id;
                void_order['name'] = 'VOID/' + void_order['name'];
                void_order['pos_reference'] = void_order['name'];
                void_order['void_state'] = 'Void';

                if (order_return['fiscal_position_id'] && this.env.pos.fiscal_positions) {
                    let fiscal_position = this.env.pos.fiscal_positions.find(fp => fp.id == order_return['fiscal_position_id'][0])
                    if (fiscal_position) {
                        order['fiscal_position'] = fiscal_position
                    }
                }
                if (order_return['pricelist_id'] && this.env.pos.pricelist_by_id) {
                    let pricelist = this.env.pos.pricelist_by_id[order_return['pricelist_id'][0]];
                    if (pricelist) {
                        void_order.pricelist = pricelist // TODO: set direct, because order return not allow set pricelist
                    }
                }
                this.env.pos.get('orders').add(void_order);

                let partner_id = order_return.partner_id;
                if (partner_id && partner_id[0]) {
                    let client = this.env.pos.db.get_partner_by_id(partner_id[0]);
                    if (client) {
                        void_order.set_client(client);
                    } else {
                        void_order.set_to_invoice(false);
                    }
                } else {
                    void_order.set_to_invoice(false);
                }
                this.env.pos.set('selectedOrder', void_order);

                for(let line_return of lines_return){
                    let price = line_return['price_unit'];
                    if (price < 0) {
                        price = -price;
                    }

                    let product = this.env.pos.db.get_product_by_id(line_return.product_id[0]);
                    var line = new models.Orderline({}, {
                        pos: this.env.pos,
                        order: void_order,
                        product: product,
                    });
                    void_order.orderlines.add(line);

                    line['returned_order_line_id'] = line_return['id'];
                    line['is_return'] = true;
                    line.set_unit_price(price);
                    line.price_manually_set = true;
                    if (line_return.discount)
                        line.set_discount(line_return.discount);
                    if (line_return.discount_reason){
                        line.discount_reason = line_return.discount_reason;
                    }


                    if(line_return.promotion){
                        void_order._apply_promotion_to_orderlines(
                            [line], 
                            line_return.promotion_id[0], // promotion_id
                            line_return.promotion_reason, 
                            0, 
                            line_return.discount
                        );
                    }

                    let quantity = 0;
                    if (line_return['new_quantity']) {
                        quantity = -line_return['new_quantity'];
                    } else {
                        quantity = -line_return['qty'];
                    }
                    if (line_return.promotion) {
                        quantity = -quantity;
                    }
                    if (line_return.redeem_point) {
                        quantity = -quantity;
                        line.credit_point = line_return.redeem_point;
                    }
                    if (quantity > 0) {
                        quantity = -quantity;
                    }
                    line.set_quantity(quantity, 'keep price when return');

                    // TODO: set lot back
                    if(this.env.pos.pack_operation_lots_by_pos_order_line_id){
                        let pack_operation_lots = this.env.pos.pack_operation_lots_by_pos_order_line_id[line_return.id];
                        if (pack_operation_lots) {
                            let multi_lot_ids = [];
                            let lot_name_manual = null;
                            for (let pack_line of pack_operation_lots){
                                if (pack_line.lot_id) {
                                    multi_lot_ids.push({ 'id': pack_line.lot_id[0], 'quantity': pack_line.quantity });
                                } else {
                                    lot_name_manual = pack_line.lot_name;
                                }
                            }
                            if (multi_lot_ids.length) { // TODO: only for multi lot
                                line.set_multi_lot(multi_lot_ids)
                            }
                            if (lot_name_manual) { // TODO: only for one lot
                                let lot_lines = line.compute_lot_lines();
                                for(let lot_line of lot_lines){
                                    lot_line.set_lot_name(lot_name_manual);
                                }
                                lot_lines.remove_empty_model();
                                lot_lines.set_quantity_by_lot();
                                line.order.save_to_db();
                            }
                        }
                    }
                    // if (line_return['variant_ids']) {
                    //     line.set_variants(line_return['variant_ids'])
                    // }
                    if (line_return['tag_ids']) {
                        line.set_tags(line_return['tag_ids'])
                    }
                }

                if (this.env.pos.combo_picking_by_order_id) {
                    let combo_picking_id = this.env.pos.combo_picking_by_order_id[return_order_id];
                    if (combo_picking_id) {
                        moves = this.env.pos.stock_moves_by_picking_id[combo_picking_id];
                        for(let move of moves){
                            let price = 0;
                            let product = this.env.pos.db.get_product_by_id(move.product_id[0]);
                            if (!product) {
                                framework.unblockUI()
                                this.env.pos.alert_message({
                                    title: 'Warning',
                                    body: 'Product ID ' + move.product_id[1] + ' have removed out of POS. Take care'
                                });
                                continue
                            }
                            if (move.product_uom_qty == 0) {
                                continue
                            }
                            var line = new models.Orderline({}, {
                                pos: this.env.pos,
                                order: void_order,
                                product: product,
                            });
                            void_order.orderlines.add(line);
                            line['is_return'] = true;
                            line.set_unit_price(price);
                            line.price_manually_set = true;
                            line.set_quantity(-1 * move.product_uom_qty, 'keep price when return');
                        }
                    }
                }


                let payments = this.env.pos.pos_payment_by_order_id[order_return.id];
                if(payments.length){
                    let uniquePaymentIds = [];
                    payments = [...new Set(payments)].filter(e=>{if(!uniquePaymentIds.includes(e.id)){uniquePaymentIds.push(e.id);return true;}return false;});
                }
                for(let payment of payments){
                    let payment_method = this.env.pos.payment_methods_by_id[payment.payment_method_id[0]];
                    if(payment_method){
                        void_order.add_paymentline(payment_method);
                    }
                    void_order.selected_paymentline.set_amount( -1 * payment.amount);
                }

                void_order.trigger('change', void_order);
                this.env.pos.trigger('auto_update:paymentlines', this);

                let current_order = this.env.pos.get_order();
                current_order.name = void_order.name;
                this.env.pos.set_order(current_order);

                if(!this.env.pos.offlineModel){
                    const pingServer = await self.env.pos._check_connection();
                    if (!pingServer) {
                        this.env.pos.pushOrderInBackground = true;
                    }
                }

                await this.env.pos.push_single_order(void_order);
                void_order.destroy({'reason':'abandon'});

                Promise.resolve(true);
            }
        }
    Registries.Component.extend(OrderReceiptReprint, GeneralOrderReceiptReprint);
    Registries.Component.extend(PosOrderDetail, GeneralPosOrderDetail);
    Registries.Component.extend(Orderline, GeneralOrderline);

    return GeneralPosOrderDetail;
});
