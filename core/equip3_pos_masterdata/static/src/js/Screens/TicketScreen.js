odoo.define('equip3_pos_masterdata.TicketScreen', function (require) {
    'use strict';
    
    const models = require('point_of_sale.models');
    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');
    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const OrderReceipt1 = require('equip3_pos_masterdata.OrderReceipt1');
    const {useListener} = require('web.custom_hooks');
    const {posbus} = require('point_of_sale.utils');
    const {useState} = owl;
    var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;

    const RetailTicketScreen = (TicketScreen) =>
        class extends TicketScreen {
            constructor() {
                super(...arguments);
                this.buffered_key_events = []
                this._onKeypadKeyDown = this._onKeypadKeyDown.bind(this);
                this.pos_sync_session_order = useState({ state: '' });

                useListener('show-popup', this.removeEventKeyboad);
            }

            mounted() {
                super.mounted()
                posbus.on('closed-popup', this, this.addEventKeyboad);
                this.addEventKeyboad()
            }

            willUnmount() {
                super.willUnmount()
                posbus.off('closed-popup', this, null);
                this.removeEventKeyboad()
            }

            addEventKeyboad() {
                $(document).off('keydown.productscreen', this._onKeypadKeyDown);
                $(document).on('keydown.productscreen', this._onKeypadKeyDown);
            }

            removeEventKeyboad() {
                $(document).off('keydown.productscreen', this._onKeypadKeyDown);
            }

            _onKeypadKeyDown(ev) {
                if (!_.contains(["INPUT", "TEXTAREA"], $(ev.target).prop('tagName'))) {
                    clearTimeout(this.timeout);
                    this.buffered_key_events.push(ev);
                    this.timeout = setTimeout(_.bind(this._keyboardHandler, this), BarcodeEvents.max_time_between_keys_in_ms);
                }
                if (ev.keyCode == 27) {  // esc key
                    this.buffered_key_events.push(ev);
                    this.timeout = setTimeout(_.bind(this._keyboardHandler, this), BarcodeEvents.max_time_between_keys_in_ms);
                }
            }

            _keyboardHandler() {
                if (this.buffered_key_events.length > 2) {
                    this.buffered_key_events = [];
                    return true;
                }
                for (let i = 0; i < this.buffered_key_events.length; i++) {
                    let event = this.buffered_key_events[i]
                    if (event.keyCode == 27) { // esc
                        $(this.el).find('.search >input').blur()
                        $(this.el).find('.search >input')[0].value = "";
                    }
                    if (event.keyCode == 46) { // del
                        let selectedOrder = this.env.pos.get_order();
                        this.deleteOrder(selectedOrder)
                    }
                    if (event.keyCode == 66) { // b
                        $(this.el).find('.discard').click()
                    }
                    if (event.keyCode == 70) { // f
                        $(this.el).find('.filter').click()
                    }
                    if (event.keyCode == 78) { // n
                        this.createNewOrder()
                    }
                    if (event.keyCode == 83) { // s
                        $(this.el).find('.search >input').focus()
                    }
                }
                this.buffered_key_events = [];
            }

            getTable(order) {
                if (order.table) {
                    return super.getTable(order)
                } else {
                    return 'N/A'
                }
            }


            getFloorOnly(order) {
                if (order.table) {
                    return `${order.table.floor.name}`;
                } else {
                    return 'N/A'
                }
            }

            selectOrder(order) {
                super.selectOrder(order)
                this.trigger('close-temp-screen');
            }

            getSearchFieldNames() {
                return {
                    ReceiptNumber: this.env._t('Receipt Number'),
                    Date: this.env._t('Date'),
                    Customer: this.env._t('Customer'),
                    CardholderName: this.env._t('Cardholder Name'),
                    Number: this.env._t('Number'),
                };
            }
            get _searchFields() {
                const { ReceiptNumber, Date, Customer, CardholderName, Number } = this.getSearchFieldNames();
                var fields = {
                    [ReceiptNumber]: (order) => order.name,
                    [Date]: (order) => moment(order.creation_date).format('YYYY-MM-DD hh:mm A'),
                    [Customer]: (order) => order.get_client_name(),
                    [Number]: (order) => order.sync_sequence_number,
                };

                if (this.showCardholderName()) {
                    fields[CardholderName] = (order) => order.get_cardholder_name();
                }
                return fields;
            }

            getPosReference(order) {
                let users = this.env.pos.users;
                let pos_reference = order.name;
                let cashier_code = '';
                if(order.cashier){
                    if(order.cashier.cashier_code){
                        cashier_code = order.cashier.cashier_code;
                    }else{
                        if(order.cashier.user_id){
                            for (var i = users.length - 1; i >= 0; i--) {
                                if(users[i].id == order.cashier.user_id[0]){
                                    cashier_code = users[i].cashier_code;
                                    break;
                                }
                            }
                        }
                    }
                }
                if(cashier_code){
                    pos_reference = pos_reference.replace('-false-',`-${cashier_code}-`);
                }
                return pos_reference;
            }

            getTableOnly(order) {
                if (order.table) {
                    return `${order.table.name}`;
                } else {
                    return 'N/A'
                }
            }
            
            getCashier(order){
                if(order.cashier){
                    return order.cashier.name;
                }
                return '';
            }

            getGuestOnly(order) {
                if (order.table) {
                    return `${order.table.guest}`;
                } else {
                    return 'N/A'
                }
            }

            async createNewOrder() {
                if (this.env.pos.config.validate_new_order) {
                    let validate = await this.env.pos._validate_action(this.env._t('Need approve create new Order'));
                    if (!validate) {
                        return false;
                    }
                }
                let currentOrder = this.env.pos.get_order();
                if(currentOrder){
                    if(currentOrder.is_complete){
                        currentOrder.finalize();
                    }
                }
                return super.createNewOrder()
            }

            async createNewOrder() {
                let self = this;

                this.env.pos._check_connection();

                if (this.env.pos.config.validate_new_order) {
                    let validate = await this.env.pos._validate_action(this.env._t('Need approve create new Order'));
                    if (!validate) {
                        return false;
                    }
                }

                let currentOrder = this.env.pos.get_order();
                if(currentOrder){
                    if(currentOrder.is_complete){
                        currentOrder.finalize();
                    }
                }
                this.env.pos.add_new_order();

                let order = self.env.pos.get_order();
                let sync_sequence_number = await this.env.pos.get_sync_sequence_number();
                console.log('Get Sequence_number:', sync_sequence_number) 
                order.sync_sequence_number = sync_sequence_number;
                order.trigger('change', order);
            }

            async onClickSyncSessionOrders(){
                this.pos_sync_session_order.state = 'connecting';
                await this.env.pos.sync_session_orders();
                this.pos_sync_session_order.state = 'done';
            }

            async SyncSessionOrderDeleteOrder(order){
                const self = this;
                let vals = {
                    uid: order['uid'],
                    database: self.env.pos.session.db,
                    pos_config_id: self.env.pos.config.id,
                    pos_session_id: self.env.session.config.pos_session_id
                }
                console.log('[SyncSessionOrderDeleteOrder] ~ Sending Data: ', vals)
                self.rpc({
                    model: 'pos.sync.session.order',
                    method: 'remove_order', 
                    args: [[], vals]
                }, {
                    shadow: true,
                    timeout: 5000
                }).then(function (response) {
                    return response;
                }, function (error) {
                    if (error && error.message && error.message.code == -32098) {
                        console.error('[SyncSessionOrderDeleteOrder] ~ Server Offline')
                    } else {
                        console.error('[SyncSessionOrderDeleteOrder] ~ Error 403')
                    }

                    self.env.pos.alert_message({
                        title: self.env._t('Warning'),
                        body: self.env._t('Failed, please try again.'),
                    })
                    return Promise.reject(error);
                });
            }

            async removeAllOrders() {
                let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Warning'),
                    body: this.env._t('Are you sure remove all Orders ?')
                })
                if (confirmed) {
                    if (this.env.pos.config.validate_remove_order) {
                        let validate = await this.env.pos._validate_action(this.env._t('Need approve delete Order'));
                        if (!validate) {
                            return false;
                        }
                    }
                    const orders = this.env.pos.get('orders').models;
                    for (let i = 0; i < orders.length; i++) {
                        this.env.pos.saveOrderRemoved(orders[i])
                    }
                    orders.forEach(o => o.destroy({'reason': 'abandon'}))
                    orders.forEach(o => o.destroy({'reason': 'abandon'}))
                    orders.forEach(o => o.destroy({'reason': 'abandon'}))
                }
            }

            async deleteOrder(order) {
                let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Warning'),
                    body: this.env._t('Are you sure want to delete this order?')
                })
                if (!confirmed) {
                    return false;
                }

                if (this.env.pos.config.validate_remove_order && !order['temporary']) {
                    let validate = await this.env.pos._validate_action(this.env._t('Need approve delete Order'));
                    if (!validate) {
                        return false;
                    }
                }
                super.deleteOrder(order);
                this.env.pos.saveOrderRemoved(order);
                this.SyncSessionOrderDeleteOrder(order);
            }

            get orderList() {
                let orders = this.env.pos.get('orders').models;
                orders = orders.filter((o)=>o.is_complete!=true);
                return orders;
            }

            hideDeleteButton(order) {
                if (!this.env.pos.config.allow_remove_order) {
                    return false
                } else {
                    return super.hideDeleteButton(order)
                }
            }


            async printforstaff(order){
                const receipt_template = this.env.pos.get_receipt_template();
                console.log('Print Checker ~ printforstaf')
                if(receipt_template.icon_coupon_base64){
                    order['icon_coupon_base64'] = receipt_template.icon_coupon_base64;
                }
                let orderRequest = null
                const fixture = document.createElement('div');
                const orderReceipt = new (Registries.Component.get(OrderReceipt1))(null, {
                    order: order, 
                    orderRequest: orderRequest,
                    print_from_checker: true,
                    receipt_template: receipt_template,
                });
                await orderReceipt.mount(fixture);
                const receiptHtml = orderReceipt.el.outerHTML;
                this.showTempScreen('ReportScreen', {
                    report_html: receiptHtml,
                    report_xml: null,
                    open_from: 'checker'
                });
            }


            async printbeforepaid(){
                const order = this.env.pos.get_order();
                let orderRequest = null
                const fixture = document.createElement('div');
                const orderReceipt = new (Registries.Component.get(OrderReceipt))(null, {order, orderRequest});
                await orderReceipt.mount(fixture);
                const receiptHtml = orderReceipt.el.outerHTML;
                this.showScreen('ReportScreen', {
                    report_html: receiptHtml,
                    report_xml: null,
                });
            }

            async saveToPartialOrder(selectedOrder) {
                let {confirmed, payload: confirm} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Alert'),
                    body: this.env._t("Are you want save current Order to Draft Order ?"),
                })
                if (confirmed) {
                    if (selectedOrder.get_total_with_tax() <= 0 || selectedOrder.orderlines.length == 0) {
                        return this.env.pos.alert_message({
                            title: this.env._t('Error'),
                            body: this.env._t('Order has Empty Cart or Amount Total smaller than or equal 0')
                        })
                    }
                    const linePriceSmallerThanZero = selectedOrder.orderlines.models.find(l => l.get_price_with_tax() <= 0 && !l.coupon_program_id && !l.promotion)
                    if (this.env.pos.config.validate_return && linePriceSmallerThanZero) {
                        let validate = await this.env.pos._validate_action(this.env._t('Have one Line has Price smaller than or equal 0. Need Manager Approve'));
                        if (!validate) {
                            return false;
                        }
                    }
                    const lineIsCoupon = selectedOrder.orderlines.models.find(l => l.coupon_id || l.coupon_program_id);
                    if (lineIsCoupon && this.env.pos.config.validate_coupon) {
                        let validate = await this.env.pos._validate_action(this.env._t('Order add Coupon, Required need Manager Approve'));
                        if (!validate) {
                            return false;
                        }
                    }
                    if (this.env.pos.config.validate_payment) {
                        let validate = await this.env.pos._validate_action(this.env._t('Need Approve Payment'));
                        if (!validate) {
                            return false;
                        }
                    }
                    let lists = this.env.pos.payment_methods.filter((p) => (p.journal && p.pos_method_type && p.pos_method_type == 'default') || (!p.journal && !p.pos_method_type)).map((p) => ({
                        id: p.id,
                        item: p,
                        label: p.name
                    }))
                    let {confirmed, payload: paymentMethod} = await this.showPopup('SelectionPopup', {
                        title: this.env._t('Save Order to Partial Order, Please select one Payment Method !!'),
                        list: lists
                    })
                    if (confirmed) {
                        let {confirmed, payload: number} = await this.showPopup('NumberPopup', {
                            title: this.env._t('How much Amount Customer need Paid ? Total Amount Order is: ') + this.env.pos.format_currency(selectedOrder.get_total_with_tax(),undefined,selectedOrder.currency),
                            startingValue: 0
                        })
                        if (confirmed) {
                            this.selectOrder(selectedOrder)
                            number = parseFloat(number)
                            if (number < 0 || number > selectedOrder.get_total_with_tax()) {
                                return this.showPopup('ErrorPopup', {
                                    title: this.env._t('Warning'),
                                    body: this.env._t('Your register Amount bigger than Total Amount Order, Required smaller than or equal Total Amount Order')
                                })
                            }
                            if (number > 0) {
                                let paymentLines = selectedOrder.paymentlines.models
                                paymentLines.forEach(function (p) {
                                    selectedOrder.remove_paymentline(p)
                                })
                                selectedOrder.add_paymentline(paymentMethod);
                                let paymentline = selectedOrder.selected_paymentline;
                                paymentline.set_amount(number);
                                selectedOrder.trigger('change', selectedOrder);
                            }
                            this.env.pos.push_single_order(selectedOrder, {
                                draft: true
                            })
                            this.showPopup('TextInputPopup', {
                                title: this.env._t('Receipt Number: ') + selectedOrder['name'],
                                startingValue: selectedOrder['name'],
                                confirmText: this.env._t('Ok'),
                                cancelText: this.env._t('Close'),
                            });
                            return this.showScreen('ReceiptScreen');
                        }
                    }
                }
            }
        }
    TicketScreen.template = 'RetailTicketScreen';
    Registries.Component.extend(TicketScreen, RetailTicketScreen);

    return RetailTicketScreen;
});
