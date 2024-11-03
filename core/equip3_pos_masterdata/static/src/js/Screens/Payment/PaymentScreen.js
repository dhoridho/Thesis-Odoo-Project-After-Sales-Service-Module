odoo.define('equip3_pos_masterdata.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');
    const _t = core._t;
    const Session = require('web.Session');
    const {posbus} = require('point_of_sale.utils');
    const BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const {useState} = owl.hooks;
    const {Gui} = require('point_of_sale.Gui');
    const qweb = core.qweb;
    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const {Printer} = require('point_of_sale.Printer');
    const {parse} = require('web.field_utils');
    const {useBarcodeReader} = require('point_of_sale.custom_hooks');
    var utils = require('web.utils');
    const {useExternalListener} = owl.hooks;
    var round_di = utils.round_decimals;
    var round_pr = utils.round_precision;
    let pushOrderInBackgroundTimeout = null;
    const framework = require('web.framework');

    const RetailPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
                useExternalListener(window, 'keyup', this._keyUpPaymentScreen);
                useListener('reference-payment-line', this.setReferencePayment);
                useListener('cheque-tracking-payment-line', this.setChequeTrackingPaymentLine);
                useListener('click-journal', this.setJournal);
                useListener('click-coin', this.setCoin);

                this.buffered_key_events = []
                this._onKeypadKeyDown = this._onKeypadKeyDown.bind(this);
                useListener('show-popup', this.removeEventKeyboad);
                this._currentOrder = this.env.pos.get_order();
                this._currentOrder.orderlines.on('change', this.render, this);
//                this.state = useState({showAllMethods: this.env.pos.config.show_all_payment_methods});
                this.state = useState({showAllMethods: true});
                this._handlePushOrderError = async function (error) { // TODO: we need control error of payment screen, dont want use point_of_sale.custom_hooks
                    // This error handler receives `error` equivalent to `error.message` of the rpc error.
                    console.error('[_handlePushOrderError] error:', error)
                    if (!error.code) {
                        return this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t('Your Server or Your Internet Offline , POS change to offline mode. Please take care, dont close POS Screen')
                        })
                    }
                    if (error.message === 'Backend Invoice') {
                        await this.showPopup('ConfirmPopup', {
                            title: this.env._t('Please print the invoice from the backend'),
                            body:
                                this.env._t(
                                    'The order has been synchronized earlier. Please make the invoice from the backend for the order: '
                                ) + error.data.order.name,
                        });
                    } else if (error.code < 0) {
                        // XmlHttpRequest Errors
                        const title = this.env._t('Unable to sync order');
                        const body = this.env._t(
                            'Check the internet connection then try to sync again by clicking on the red wifi button (upper right of the screen).'
                        );
                        await this.showPopup('OfflineErrorPopup', {title, body});
                    } else if (error.code === 200) {
                        // OpenERP Server Errors
                        await this.showPopup('ErrorTracebackPopup', {
                            title: error.data.message || this.env._t('Server Error'),
                            body:
                                error.data.debug ||
                                this.env._t('The server encountered an error while receiving your order.'),
                        });
                    } else if (error.code === 700) {
                        // Fiscal module errors
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Fiscal data module error'),
                            body:
                                error.data.error.status ||
                                this.env._t('The fiscal data module encountered an error while receiving your order.'),
                        });
                    } else {
                        // ???
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Unknown Error'),
                            body: this.env._t(
                                'The order could not be sent to the server due to an unknown error'
                            ),
                        });
                    }
                }
                useBarcodeReader({
                    voucher: this._scanVoucherCode,
                }, true)
            }

            mounted() {
                super.mounted();
                this.state.showAllMethods = true
                posbus.on('closed-popup', this, this.addEventKeyboad);
                if (this.props.autoValidateOrder) {
                    return this.validateOrder(false)
                }
                this.addEventKeyboad()
            }
            
            async _keyUpPaymentScreen(event) {
                // if (["v", "V"].includes(event.key)) {
                //     this.changeCurrency()
                // }
            }

            async _scanVoucherCode(code) {
                if (code == "" || !code) {
                    return
                }
                const voucher = await this.env.pos.rpc({
                    model: 'pos.voucher',
                    method: 'get_voucher_by_code',
                    args: [code],
                })
                if (voucher == -1) {
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Error'),
                        body: this.env._t('Not found any Voucher or Voucher Expired Date')
                    });
                } else {
                    var order = this.env.pos.get_order();
                    if (order) {
                        return order.client_use_voucher(voucher)
                    }
                }
            }


            async validateOrder(isForceValidate) {
                if (this.isProcessing) {
                    return;
                }
                this.isProcessing = true;
                const self = this;

                // TO DO : SPLIT Order, PO pos order auto create SO
                var selectedOrder = this._currentOrder;
                var order_lines = selectedOrder.get_orderlines();
                if(selectedOrder && selectedOrder.is_pre_order && order_lines.length > 0){
                    let value_create_so = {
                        name: selectedOrder.name,
                        origin: self.env.pos.config.name,
                        partner_id: selectedOrder.get_client().id,
                        pricelist_id: selectedOrder.pricelist.id,
                        order_line: [],
                        is_self_pickup:true,
                        ean13: selectedOrder.ean13,
                        warehouse_id:self.env.pos.config.warehouse_id[0],
                        warehouse_new_id:self.env.pos.config.warehouse_id[0],
                        delivery_date: selectedOrder.estimated_order_pre_order,
                        commitment_date: selectedOrder.estimated_order_pre_order,
                        effective_date: selectedOrder.estimated_order_pre_order,
                        expected_date: selectedOrder.estimated_order_pre_order,
                    }

                    
                    var product_po_ids = order_lines.filter(i => i.product.is_can_be_po).map((l)=>l.product.id);
                    const so_val = selectedOrder.export_as_JSON();
                    for (var i = 0; i < so_val.lines.length; i++) {
                        var line_so = so_val.lines[i][2];
                        var line_so_val = selectedOrder._covert_pos_line_to_sale_line(line_so);
                        if(product_po_ids.includes(line_so_val[2].product_id)){
                            value_create_so.order_line.push(line_so_val);
                        }
                    }
                    
                    framework.blockUI();
                    let result_create_so = await this.rpc({
                    model: 'sale.order',
                    method: 'pos_create_sale_order',
                    args: [value_create_so, true, false, false]
                        }).then(async function (response) {
                            framework.unblockUI()
                            await self.env.pos.getSaleOrders();
                            return response
                        }, function (err) {
                            console.log(err)
                            return self.env.pos.query_backend_fail(err);
                        })
                        
                    if(product_po_ids.length==order_lines.length){
                
                        self.env.pos.db.remove_unpaid_order(selectedOrder);
                        self.env.pos.db.remove_order(selectedOrder['uid']);
                        self.showScreen('ReceiptScreen');
                        return false
                    }
                    
                }

                if(!this.env.pos.offlineModel){
                    setTimeout(function() {
                        self.env.pos._check_connection();
                    }, 1000);
                }

                if(this.env.pos.offlineModel){
                    this.env.pos._turn_on_save_order_to_server();
                }
                if(!this.env.pos.offlineModel){
                    this.env.pos.pushOrderInBackground = true;
                }

                if (this._currentOrder) {
                    let paymentLines = this._currentOrder.paymentlines.models
                    if(this.cardPayment()){
                        let has_error = false;
                        paymentLines.forEach(function (p) {
                            if(!p.card_payment_number || p.card_payment_number == ''){
                                has_error = true;
                            }
                        });
                        if(has_error){
                            return self.showPopup('ErrorPopup', {
                                title: self.env._t('Warning'),
                                body: self.env._t('Card Number is required!'),
                                confirmText: 'OK',
                                cancelText:''
                            });
                        }
                    }

                    let client = this.currentOrder.get_client();
                    let total_with_tax = this.currentOrder.get_total_with_tax();
                    let is_receivables = false;
                    paymentLines.forEach(function(p) {
                        if(p.payment_method.is_receivables){
                            is_receivables = true;
                        }
                    });
                    if(client && client.customer_credit && is_receivables){
                        client = self.env.pos.db.partner_by_id[client.id];
                        if(total_with_tax > client.customer_credit_limit){
                            const {confirmed, payload} = await self.showPopup('CreditLimitPopup');
                            if(confirmed){
                                this.showScreen( 'PosOrderScreen',{
                                    order: null,
                                    selectedClient: null,
                                    close_screen_button: true,
                                    filteredPartnerId: client.id,
                                    outstanding_receivable: true,
                                });
                            }
                            return false;
                        }
                    }

                    
                    // TODO: remove all payment lines has amount is zero
                    paymentLines.forEach(function (p) {
                        if(!p.origin_amount){
                            p.origin_amount = p.amount;
                        }
                        if (p.amount == 0) {
                            self._currentOrder.remove_paymentline(p);
                        } else{
                            // TODO: Update mdr amount
                            let mdr_amount = p.get_mdr_amount_rounding();
                            if(mdr_amount != 0){
                                p.mdr_amount = mdr_amount;
                                if(p.mdr_paid_by == 'Customer'){
                                    p.amount = p.origin_amount + mdr_amount;
                                }
                            }
                        }
                    });


                    self._currentOrder.rounding_from_payment = self._currentOrder.get_rounding_amount_order()
                    paymentLines.forEach(function (p) {
                        p.amount = p.get_amount_with_rounding()
                    })
                }

                var receipt_template = this.env.pos.get_receipt_template()
                this.currentOrder.voucher_number_use = false
                let total_without_tax = this.currentOrder.get_total_without_tax();
                if (receipt_template && receipt_template.is_voucher_receipt && receipt_template.generate_voucher_id){
                    try {
                        let rec_voucher_data = await this.env.pos.rpc({
                            model: 'generate.pos.voucher',
                            method: 'generate_from_ui_pos',
                            args: [receipt_template['generate_voucher_id'][0], receipt_template.id, total_without_tax],
                        }, {
                            shadow: true,
                            timeout: 800 // 0.8 second
                        }).then(function(response) {
                            return response;
                        }, function(error) {
                            if (error && error.message && error.message.code == -32098) {
                                console.error('[generate_from_ui_pos] ~ Server Offline:', error)
                            } else {
                                console.error('[generate_from_ui_pos] ~ Error 403:', error)
                            }
                            return Promise.resolve(null);
                        });
                        if(rec_voucher_data){
                            this.currentOrder.voucher_number_use = rec_voucher_data.number
                            this.currentOrder.voucher_expired_date = this.env.pos.format_date(rec_voucher_data.end_date)
                            var generate_voucher_value = 0
                            if(rec_voucher_data.apply_type=='percent'){
                                generate_voucher_value = rec_voucher_data.value + ' (%)'
                            }
                            else{
                                generate_voucher_value = this.env.pos.format_currency(rec_voucher_data.value)
                            }
                            this.currentOrder.generate_voucher_value = generate_voucher_value
                            if(rec_voucher_data.minimum_purchase_amount){
                                this.currentOrder.voucher_min_amount = this.env.pos.format_currency(rec_voucher_data.minimum_purchase_amount)
                            }
                            this.currentOrder.generate_voucher_id = receipt_template['generate_voucher_id'][0]
                        }
                    }
                    catch (error) {
                        if (error.message.code < 0) {
                            await this.showPopup('OfflineErrorPopup', {
                                title: this.env._t('Offline'),
                                body: this.env._t('Unable to save changes.'),
                            });
                        }
                    }
                }
                return super.validateOrder(isForceValidate)
            }

            async addTip() {
                if (!this.env.pos.config.tip_percent) {
                    return super.addTip()
                } else {
                    const {confirmed, payload} = await this.showPopup('NumberPopup', {
                        title: this.env._t('Are you want set Tip (%) base on Total Due ?'),
                        body: this.env._t('Maximum Tip (%) you can set is ') + this.env.pos.config.tip_percent_max + ' % .',
                        startingValue: this.env.pos.config.tip_percent_max
                    })
                    if (!confirmed) {
                        return super.addTip()
                    } else {
                        const tipPercent = parse.float(payload)
                        if (tipPercent <= 0 || tipPercent > this.env.pos.config.tip_percent_max) {
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Warning'),
                                body: this.env._t('Tip Percent required bigger than 0 and smaller than or equal ') + this.env.pos.config.tip_percent_max + ' %.',
                            })
                        } else {
                            const totalWithTax = this.currentOrder.get_total_with_tax()
                            const tipAmount = totalWithTax / 100 * tipPercent
                            this.currentOrder.set_tip(tipAmount)
                            return this.showPopup('ConfirmPopup', {
                                title: this.env._t('Successfully'),
                                body: this.env._t('Set tip Amount to Order: ') + this.env.pos.format_currency(tipAmount,false,this.currentOrder.currency),
                            })
                        }
                    }
                }
            }

            async changeCurrency() {
                const self = this
                const list = this.env.pos.multi_currencies.map(c => ({
                    id: c.id,
                    label: c.name,
                    isSelected: false,
                    item: c
                }))
                let {confirmed, payload: currency} = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Choice Currency for Payment Order'),
                    list: list,
                });
                if (confirmed) {
                    this.currentOrder.currency = currency
                    let paymentLines = this.currentOrder.paymentlines.models
                    paymentLines.forEach(function (p) {
                        self.currentOrder.remove_paymentline(p)
                    })
                    paymentLines.forEach(function (p) {
                        self.currentOrder.remove_paymentline(p)
                    })

                    var lines_to_recompute = _.filter(self.currentOrder.get_orderlines(), function (line) {
                        return ! line.price_manually_set;
                    });
                    _.each(lines_to_recompute, function (line) {
                        var conversion_rate = self.env.pos.currency.rate / self.env.pos.company_currency.rate;
                        var new_conversion_rate = currency.rate / self.env.pos.company_currency.rate;
                        var price = line.product.get_price(self.pricelist, line.get_quantity(), line.get_price_extra())
                        if(currency.id != self.env.pos.currency.id){
                            var price_before = round_pr(price / conversion_rate, self.env.pos.currency.rounding);
                            var price_new = round_pr(price_before * new_conversion_rate, currency.rounding);
                            price = price_new
                        }
                        line.set_unit_price(price);
                        self.currentOrder.fix_tax_included_price(line);
                    });
                    this.trigger('change');
                }
            }

            OnChangeNote(event) {
                const newNote = event.target.value;
                if (this._currentOrder) {
                    this._currentOrder.set_note(newNote)
                }
            }


//            get showAllPaymentMethodLabel() {
//                if (!this.state.showAllMethods) {
//                    return this.env._t('All Methods')
//                } else {
//                    return this.env._t('Basic Methods')
//                }
//            }

//            showAllPaymentMethods() {
//                this.state.showAllMethods = !this.state.showAllMethods;
//            }

            ButtonBackToProducts() {
                const order = this.env.pos.get_order();
                order.paymentlines.forEach(function (p) {
                    order.remove_paymentline(p)
                });

                if(order.client_use_voucher){
                    order.orderlines.models.forEach(l => {
                        if (l.is_product_voucher) {
                            order.remove_orderline(l);
                        }
                    });
                    order.reset_client_use_voucher();
                    order.trigger('change', order);
                }
                
                if(order.pos_coupon_id){
                    order.reset_client_use_coupon();
                    order.trigger('change', order);
                }

                order.currency = this.env.pos.currency
                order.set_pricelist(order.pricelist)
                order.remove_all_promotion_line();
                this.showScreen('ProductScreen');
            }

            cardPayment(){
                let selectedOrder = this.env.pos.get_order();
                if(selectedOrder){
                    if(selectedOrder.selected_card_payment_id){
                        return this.env.pos.db.get_card_payment_by_id(selectedOrder.selected_card_payment_id);
                    }
                }
                return false;
            }
            get PaymentMethods() {
                let self = this;
                this.env.pos.payment_methods.filter(method => this.env.pos.config.payment_method_ids.includes(method.id))
                this.env.pos.normal_payment_methods.filter(method => this.env.pos.config.payment_method_ids.includes(method.id))

                if(!this.env.pos.payment_methods_all){
                    this.env.pos.payment_methods_all = this.env.pos.payment_methods;
                }
                if(this.env.pos.payment_methods_all){
                    if(this.env.pos.payment_methods_all.length != this.env.pos.payment_methods.length){
                        this.env.pos.payment_methods = this.env.pos.payment_methods_all;
                    }
                }

                if(this.cardPayment()){
                    if(this.env.pos.payment_methods){
                        this.env.pos.payment_methods = this.env.pos.payment_methods.filter(
                            p=>p.is_bank==true 
                            && p.is_cash_count==false
                            && p.able_use_card==true
                        );
                    }
                }

                const selectedOrder = this._currentOrder;
                // Filter promotions in current order
                var promotion_ids = [];
                const CurrentOrder = this._currentOrder;
                CurrentOrder.orderlines.forEach(function (l) {
                    if (l.promotion && l.promotion_ids.length) {
                        promotion_ids = promotion_ids.concat(l.promotion_ids);
                    } else if(l.promotion && l.pos !== undefined && l.pos.promotion_ids !== undefined && l.pos.promotion_ids.length) {
                        promotion_ids = promotion_ids.concat(l.pos.promotion_ids);
                    }
                })
                promotion_ids = _.uniq(promotion_ids);
                // Filter payment methods linked with promotions
                var payment_method_ids = [];
                promotion_ids.forEach(function (promo_id) {
                    let promotion = self.env.pos.promotion_by_id[promo_id];
                    payment_method_ids = payment_method_ids.concat(promotion.payment_method_ids);
                })
                payment_method_ids = _.uniq(payment_method_ids);


                if (!selectedOrder) {
                    return []
                } else {

                    if (this.state.showAllMethods) {
                        if(promotion_ids.length >0)
                        {
                            let all_filter_data = []
                            var filter_pay_methods = this.env.pos.payment_methods
                            all_filter_data = filter_pay_methods.filter(line => payment_method_ids.includes(line.id));
                            return all_filter_data
                        }
                        else{
                        return this.env.pos.payment_methods
                        }
                    }
                    const selectedCurrency = selectedOrder.currency
                    let paymentMethods = []
                    let FinalPaymentMethods = []
                    if (selectedCurrency) {
                        this.env.pos.normal_payment_methods.forEach(p => {
                            if (!p.journal || (p.journal && !p.journal.currency_id) || (p.journal && p.journal.currency_id && p.journal.currency_id[0] == selectedCurrency['id'])) {
                                paymentMethods.push(p)
                            }
                        })
                        FinalPaymentMethods = paymentMethods.filter(method => this.env.pos.config.payment_method_ids.includes(method.id));
                    } else {
                        FinalPaymentMethods = this.env.pos.normal_payment_methods.filter(method => this.env.pos.config.payment_method_ids.includes(method.id));
                    }


                    if (promotion_ids && payment_method_ids) {
                        let FinalPaymentMethodsAll = []
                        FinalPaymentMethodsAll = FinalPaymentMethods.filter(line => payment_method_ids.includes(line.id));
                        if (!FinalPaymentMethodsAll) {
                            return this.env.pos.alert_message({
                                title: this.env._t('Error'),
                                body: this.env._t('Pos payment methods not configured for this promotion.')
                            })
                        }
                        return FinalPaymentMethodsAll
                    } else {
                        return FinalPaymentMethods
                    }
                }
            }

            get PaymentMethodsList(){
                return this.env.pos.payment_methods.filter(method => this.env.pos.config.payment_method_ids.includes(method.id) == true);
            }

            // OVERRIDE
            async _finalizeValidation(options) {
                if (!this.env.pos.proxy.printer) {
                    this.env.pos.config.iface_cashdrawer = false
                }
                if(this.currentOrder){
                    this.currentOrder.is_complete = true;
                }

                if ((this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) && this.env.pos.config.iface_cashdrawer) {
                    if (!this.env.pos.config.pos_bluetooth_printer) {
                        this.env.pos.proxy.printer.open_cashbox();
                    }
                }

                this.currentOrder.initialize_validation_date();
                this.currentOrder.finalized = true;

                let syncedOrderBackendIds = [];

                try {
                    /** No need wait because the order will be push in the background **/
                    if (this.currentOrder.is_to_invoice()) {
                        this.env.pos.push_and_invoice_order(
                            this.currentOrder
                        );
                    } else {
                        this.env.pos.push_single_order(
                            this.currentOrder,
                            options
                        );
                    }
                } catch (error) {
                    if (error.code == 700)
                        this.error = true;

                    if (typeof(error) === 'object' && 'code' in error) {
                        // We started putting `code` in the rejected object for invoicing error.
                        // We can continue with that convention such that when the error has `code`,
                        // then it is an error when invoicing. Besides, _handlePushOrderError was
                        // introduce to handle invoicing error logic.
                        await this._handlePushOrderError(error);
                    } else {
                        // We don't block for connection error. But we rethrow for any other errors.
                        if (this.isConnectionError(error)) {
                            this.showPopup('OfflineErrorPopup', {
                                title: this.env._t('Connection Error'),
                                body: this.env._t('Order is not synced. Check your internet connection'),
                            });
                        } else {
                            throw error;
                        }
                    }
                }
                if (syncedOrderBackendIds.length && this.currentOrder.wait_for_push_order()) {
                    const result = await this._postPushOrderResolve(
                        this.currentOrder,
                        syncedOrderBackendIds
                    );
                    if (!result) {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Error: no internet connection.'),
                            body: this.env._t('Some, if not all, post-processing after syncing order failed.'),
                        });
                    }
                }

                this.showScreen(this.nextScreen);
                
                
                // If we succeeded in syncing the current order, and
                // there are still other orders that are left unsynced,
                // we ask the user if he is willing to wait and sync them.
                if (syncedOrderBackendIds.length && this.env.pos.db.get_orders().length) {
                    const { confirmed } = await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Remaining unsynced orders'),
                        body: this.env._t(
                            'There are unsynced orders. Do you want to sync these orders?'
                        ),
                    });
                    if (confirmed) {
                        // NOTE: Not yet sure if this should be awaited or not.
                        // If awaited, some operations like changing screen
                        // might not work.
                        this.env.pos.push_orders();
                    }
                }
            }

            async askAddChargeAmount(method) {
                const dueAmount = this.currentOrder.get_due();
                if (dueAmount <= 0) {
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Warning'),
                        body: this.env._t('Order Full Fill Payments Amount')
                    })
                }
                let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Alert, need add Fees Charge'),
                    body: this.env._t('Your selected Payment Method need add Fees Charge ?'),
                    confirmText: this.env._t('Add Now !!!'),
                    cancelText: this.env._t('No, keep current Amount of Order')
                })
                if (confirmed) {
                    const productFee = this.env.pos.db.get_product_by_id(method.fees_product_id[0])
                    if (productFee) {
                        this.currentOrder.orderlines.models.forEach(l => {
                            if (l.product.id == productFee['id']) {
                                this.currentOrder.remove_orderline(l)
                            }
                        })
                        this.currentOrder.orderlines.models.forEach(l => {
                            if (l.product.id == productFee['id']) {
                                this.currentOrder.remove_orderline(l)
                            }
                        })
                        let feesAmount = 0
                        if (method.fees_type == 'fixed') {
                            feesAmount = method.fees_amount
                        } else {
                            feesAmount = dueAmount * method.fees_amount / 100
                        }
                        if (feesAmount < 0) {
                            feesAmount = -feesAmount
                        }
                        if (feesAmount != 0) {
                            this.env.pos.alert_message({
                                title: this.env._t('Successfully'),
                                body: this.env._t('Add Fees Amount: ') + this.env.pos.format_currency(feesAmount,false,this.currentOrder.currency)
                            })
                            return this.currentOrder.add_product(productFee, {
                                quantity: 1,
                                price: feesAmount,
                                merge: false
                            });
                        } else {
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Error'),
                                body: this.env._t('Fees Amount it not Possible is 0')
                            })
                        }
                    } else {
                        return this.showPopup('ErrorPopup', {
                            title: this.env._t('Error'),
                            body: method.fees_product_id[1] + this.env._t(' Not Available in POS')
                        })
                    }
                } else {
                    return false
                }
            }

            async askApplyDiscount(method) {
                method['discountStr'] = null
                if (method.discount_type == 'percent') {
                    method['discountStr'] = this.env._t('Applied Discount: ') + this.env.pos.format_currency_no_symbol(method.discount_amount) + ' %.'
                } else {
                    method['discountStr'] = this.env._t('Applied Discount: ') + this.env.pos.format_currency(method.discount_amount,false,this.currentOrder.currency)
                }
                const dueAmount = this.currentOrder.get_due();
                if (dueAmount <= 0) {
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Warning'),
                        body: this.env._t('Order Full Fill Payments Amount')
                    })
                }
                let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Alert, Method Allow add Discount'),
                    body: method['discountStr'],
                    confirmText: this.env._t('Add Now !!!'),
                    cancelText: this.env._t('No')
                })
                if (confirmed) {
                    const productDisc = this.env.pos.db.get_product_by_id(method.discount_product_id[0])
                    if (productDisc) {
                        this.currentOrder.orderlines.models.forEach(l => {
                            if (l.product.id == productDisc['id']) {
                                this.currentOrder.remove_orderline(l)
                            }
                        })
                        this.currentOrder.orderlines.models.forEach(l => {
                            if (l.product.id == productDisc['id']) {
                                this.currentOrder.remove_orderline(l)
                            }
                        })
                        let discountAmount = 0
                        if (method.discount_type == 'fixed') {
                            discountAmount = method.discount_amount
                        } else {
                            discountAmount = dueAmount * method.discount_amount / 100
                        }
                        if (discountAmount > 0) {
                            discountAmount = -discountAmount
                        }
                        if (discountAmount != 0) {
                            this.env.pos.alert_message({
                                title: this.env._t('Successfully'),
                                body: this.env._t('Add Discount Amount: ') + this.env.pos.format_currency(discountAmount,false,this.currentOrder.currency)
                            })
                            return this.currentOrder.add_product(productDisc, {
                                quantity: 1,
                                price: discountAmount,
                                merge: false
                            });
                        } else {
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Error'),
                                body: this.env._t('Fees Amount it not possible is 0')
                            })
                        }
                    } else {
                        return this.showPopup('ErrorPopup', {
                            title: this.env._t('Error'),
                            body: method.fees_product_id[1] + this.env._t(' Not Available in POS')
                        })
                    }
                } else {
                    return false
                }
            }

            async askAddPaymentMDR(paymentMethod) {
                const order = this.env.pos.get_order();
                let {confirmed, payload} = await this.showPopup('CardPaymentPopup', { 
                    selected_payment: order.get_selected_card_payment(),
                    payment_method: paymentMethod,
                });
                if (!confirmed){
                    return false;
                }
                if (confirmed) {
                    order.set_selected_card_payment(payload);

                    // TODO: Remove promotion if Card Payment not fulfil the Condition
                    let is_promotion_valid = this.currentOrder.is_promotion_fulfil_card_payment_condition();
                    if(!is_promotion_valid){
                        this.currentOrder.remove_all_promotion_line();
                        this.env.pos.apply_promotion_succeed = false;
                    }

                    return payload;
                }
            }

            async addNewPaymentLine({detail: paymentMethod}) {
                const linecheck = this.paymentLines.find((pline) => pline.payment_method.id === paymentMethod.id);
                if (linecheck) {
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Warning !'),
                        body: this.env._t("Not allowed to have multiple payment method. ")
                    });
                }
                if (paymentMethod.discount) {
                    await this.askApplyDiscount(paymentMethod)
                }
                if (paymentMethod.apply_charges && paymentMethod.fees_amount > 0) {
                    await this.askAddChargeAmount(paymentMethod)
                }

                let payment_mdr = false;
                if(paymentMethod.is_mdr){
                    payment_mdr = await this.askAddPaymentMDR(paymentMethod);
                    if (!payment_mdr){
                        return;
                    }
                }

                super.addNewPaymentLine({detail: paymentMethod});
                const selected_paymentline = this.currentOrder.selected_paymentline;

                if (selected_paymentline && payment_mdr){
                    selected_paymentline.card_payment_number = payment_mdr.card_number;
                    selected_paymentline.mdr_payment_card_id = payment_mdr.card_payment_id;
                    selected_paymentline.payment_mdr_id = payment_mdr.payment_mdr_id;
                    if(paymentMethod.is_mdr_discount){
                        selected_paymentline.mdr_paid_by = paymentMethod.mdr_paid_by;
                    }
                }

                this.env.pos.trigger('refresh.customer.facing.screen');
                if (paymentMethod && paymentMethod['cheque_bank_information'] && selected_paymentline) {
                    this.setChequeTrackingPaymentLine({
                        detail: { cid: selected_paymentline['cid'] }
                    })
                }
            }

            _updateSelectedPaymentline() {
                if(this.env.pos.selected_order_method == 'employee-meal'){
                    if(this.selectedPaymentLine.name.toLowerCase().trim() == 'employee budget'){
                        return;
                    }
                }

                super._updateSelectedPaymentline();

                if ((this.selectedPaymentLine && this.selectedPaymentLine.payment_method.pos_method_type == "rounding") || !this.selectedPaymentLine) {
                    const cashMethod = this.payment_methods_from_config.find(p => p.journal && p.is_cash_count && p.pos_method_type == 'default')
                    if (cashMethod) {
                        this.currentOrder.add_paymentline(cashMethod);
                    }
                }
                this.env.pos.trigger('refresh.customer.facing.screen');
            }

            deletePaymentLine(event) {
                const {cid} = event.detail;
                const line = this.paymentLines.find((line) => line.cid === cid);
                if (line) {
                    
                    if(line && line.payment_edc_state == 'paid'){
                        Gui.showPopup('ErrorPopup', {
                            title: _t('Warning'),
                            body: _t("Can't remove EDC payment already Paid!")
                        });
                        return;
                    }

                    super.deletePaymentLine(event);
                    this.env.pos.trigger('refresh.customer.facing.screen');
                    console.log('[deletePaymentLine] deleted payment line')
                }
            }

            selectPaymentLine(event) {
                super.selectPaymentLine(event);
                this.env.pos.trigger('refresh.customer.facing.screen');
            }

            willUnmount() {
                super.willUnmount();
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

            async _keyboardHandler() {
                if (this.buffered_key_events.length > 3) {
                    this.buffered_key_events = [];
                    return true;
                }
                for (let i = 0; i < this.buffered_key_events.length; i++) {
                    let event = this.buffered_key_events[i]
                    // -------------------------- product screen -------------
                    let key = '';
                    if (event.keyCode == 13 || event.keyCode == 39) { // enter or arrow right
                        $(this.el).find('.next').click()
                    }
                    // if (event.keyCode == 66 || event.keyCode == 27) { // b
                    //     $(this.el).find('.back').click()
                    // }
                    if (event.keyCode == 67) { // c Customer
                        this.selectClient()
                    }
                    // if (event.keyCode == 73) { // i Invoice
                    //     this.toggleIsToInvoice()
                    // }
                    if (event.keyCode == 82) { // r remove selected paymentline
                        let selectedPaymentline = this.currentOrder.selected_paymentline
                        if (selectedPaymentline && selectedPaymentline.payment_method && selectedPaymentline.payment_method.pos_method_type != 'rounding') {
                            this.currentOrder.remove_paymentline(selectedPaymentline)
                            if (this.currentOrder.paymentlines.models.length > 0) {
                                this.currentOrder.select_paymentline(this.currentOrder.paymentlines.models[0]);
                            }
                            NumberBuffer.reset()
                            this.render()
                        }
                    }
                    if (event.keyCode == 84) { // t TIP
                        this.addTip()
                    }
                    if (event.keyCode == 38 || event.keyCode == 40) { // arrow up
                        let selectedPaymentline = this.currentOrder.selected_paymentline
                        if (selectedPaymentline) {
                            for (let i = 0; i < this.currentOrder.paymentlines.models.length; i++) {
                                let line = this.currentOrder.paymentlines.models[i]
                                if (line.cid == selectedPaymentline.cid) {
                                    let payment_number = null;
                                    if (event.keyCode == 38) { // up
                                        if (i == 0) {
                                            payment_number = this.currentOrder.paymentlines.models.length - 1
                                        } else {
                                            payment_number = i - 1
                                        }
                                    } else { // down
                                        if (i + 1 >= this.currentOrder.paymentlines.models.length) {
                                            payment_number = 0
                                        } else {
                                            payment_number = i + 1
                                        }
                                    }
                                    this.currentOrder.select_paymentline(this.currentOrder.paymentlines.models[payment_number]);
                                    NumberBuffer.reset()
                                    this.render()
                                    break;
                                }
                            }
                        } else {
                            if (this.currentOrder.paymentlines.models.length >= 1) {
                                this.currentOrder.select_paymentline(this.currentOrder.paymentlines.models[0]);
                                NumberBuffer.reset()
                                this.render()
                            }
                        }
                    }
                    if (event.key) {
                        const line = this.paymentLines.find((line) => line.payment_method && line.payment_method.shortcut_keyboard === event.key);
                        if (line) {
                            this.currentOrder.select_paymentline(line);
                            NumberBuffer.reset();
                            this.render();
                        } else {
                            const paymentMethod = this.env.pos.payment_methods.find((p) => p.shortcut_keyboard && p.shortcut_keyboard.toUpperCase() === event.key.toUpperCase())
                            if (paymentMethod) {
                                await this.addNewPaymentLine({detail: paymentMethod});
                                this.render()
                            }
                        }
                    }
                }
                this.buffered_key_events = [];
            }

            setCoin(event) {
                let selectedOrder = this.currentOrder;
                let selectedPaymentline = selectedOrder.selected_paymentline
                if ((!selectedPaymentline) || (selectedPaymentline.payment_method && selectedPaymentline.payment_method.pos_method_type != 'default')) {
                    let cashMethod = this.env.pos.normal_payment_methods.find((p) => p.journal && p.pos_method_type == 'default' && p.is_cash_count)
                    if (!cashMethod) {
                        this.env.pos.alert_message({
                            title: this.env._t('Error'),
                            body: this.env._t(
                                'Cash method not found in your pos !'
                            ),
                        });
                    } else {
                        this.currentOrder.add_paymentline(cashMethod);
                        selectedPaymentline = this.currentOrder.selected_paymentline;
                        selectedPaymentline.set_amount(event.detail.amount);
                    }
                } else {
                    selectedPaymentline.set_amount(selectedPaymentline.amount + event.detail.amount);
                }
                this.currentOrder.trigger('change', this.currentOrder);
            }

            setJournal(event) {
                let selectedOrder = this.currentOrder;
                selectedOrder.payment_journal_id = event.detail.id
                selectedOrder.trigger('change', selectedOrder);
            }

            async setReferencePayment(event) {
                const {cid} = event.detail;
                const line = this.paymentLines.find((line) => line.cid === cid);
                let {confirmed, payload: ref} = await this.showPopup('TextInputPopup', {
                    title: this.env._t('Payment Reference Notes ?'),
                    startingValue: line.ref || ''
                })
                if (confirmed) {
                    line.set_reference(ref);
                    this.render()
                }
            }

            async roundingTotalPaid() {
                let selectedOrder = this.env.pos.get_order();
                let roundingMethod = this.env.pos.payment_methods.find((p) => p.journal && p.pos_method_type == 'rounding')
                if (!selectedOrder || !roundingMethod) {
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Warning'),
                        body: this.env._t('You active Rounding on POS Setting but your POS Payment Method missed add Payment Method [Rounding Amount]'),
                    })
                }
                selectedOrder.paymentlines.models.forEach(function (p) {
                    if (p.payment_method && p.payment_method.journal && p.payment_method.pos_method_type == 'rounding') {
                        selectedOrder.remove_paymentline(p)
                    }
                })
                let due = selectedOrder.get_due();
                if (due == 0) {
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Warning'),
                        body: this.env._t('Due Amount is 0, please remove all payments register the first'),
                    })
                }
                let amountRound = 0;
                if (this.env.pos.config.rounding_type == 'rounding_integer') {
                    let decimal_amount = due - Math.floor(due);
                    if (decimal_amount <= 0.25) {
                        amountRound = -decimal_amount
                    } else if (decimal_amount > 0.25 && decimal_amount < 0.75) {
                        amountRound = 1 - decimal_amount - 0.5;
                        amountRound = 0.5 - decimal_amount;
                    } else if (decimal_amount >= 0.75) {
                        amountRound = 1 - decimal_amount
                    }
                } else if (this.env.pos.config.rounding_type == 'rounding_up_down') {
                    let decimal_amount = due - Math.floor(due);
                    if (decimal_amount < 0.5) {
                        amountRound = -decimal_amount
                    } else {
                        amountRound = 1 - decimal_amount;
                    }
                } else {
                    let after_round = Math.round(due * Math.pow(10, roundingMethod.journal.decimal_rounding)) / Math.pow(10, roundingMethod.journal.decimal_rounding);
                    amountRound = after_round - due;
                }
                if (amountRound == 0) {
                    this.showPopup('ConfirmPopup', {
                        title: this.env._t("Warning"),
                        body: this.env._t("Total Paid of Order have not any rounding Amount"),
                    })
                } else {
                    selectedOrder.add_paymentline(roundingMethod);
                    let roundedPaymentLine = selectedOrder.selected_paymentline;
                    roundedPaymentLine.set_amount(-amountRound);
                }
            }


            async setChequeTrackingPaymentLine(event) {
                const {cid} = event.detail;
                const line = this.paymentLines.find((line) => line.cid === cid);
                let {confirmed, payload: datas} = await this.showPopup('PopUpSetChequePaymentLine', {
                    title: this.env._t('Set Cheque Bank Information'),
                    cheque_owner: line.cheque_owner,
                    cheque_bank_id: line.cheque_bank_id,
                    cheque_bank_account: line.cheque_bank_account,
                    cheque_check_number: line.cheque_check_number,
                    cheque_card_name: line.cheque_card_name,
                    cheque_card_number: line.cheque_card_number,
                    cheque_card_type: line.cheque_card_type,
                })
                if (confirmed) {
                    line.cheque_card_name = datas['cheque_card_name']
                    line.cheque_card_number = datas['cheque_card_number']
                    line.cheque_card_type = datas['cheque_card_type']
                    line.cheque_bank_account = datas['cheque_bank_account']
                    line.cheque_bank_id = parseInt(datas['cheque_bank_id'])
                    line.cheque_check_number = datas['cheque_check_number']
                    line.cheque_owner = datas['cheque_owner']
                    line.trigger('change', line)
                }
            }

            async _isOrderValid() {
                let extendValidate = true
                const self = this;
                if (this.currentOrder) {
                    let totalWithTax = this.currentOrder.get_total_with_tax();
                    if (!this.env.pos.config.allow_payment_zero && totalWithTax == 0) {
                        this.env.pos.alert_message({
                            title: this.env._t('Error'),
                            body: this.env._t(
                                'Your POS not allow payment order with Amount Total is 0, required difference 0'
                            ),
                        });
                        extendValidate = false
                    }
                }
                // if (this.env.pos.config.validate_payment) {
                //     let validate = await this.env.pos._validate_action(this.env._t('Go to Payment Order'));
                //     if (!validate) {
                //         return false;
                //     }
                // }
                const linePriceSmallerThanZero = this.currentOrder.orderlines.models.find(l => l.get_price_with_tax() <= 0 && !l.coupon_program_id && !l.promotion)
                if (this.env.pos.config.validate_return && linePriceSmallerThanZero) {
                    let validate = await this.env.pos._validate_action(this.env._t('Have one Line have Price smaller than or equal 0. Please check'));
                    if (!validate) {
                        extendValidate = false
                    }
                }

                const lineIsAmountSmallerThanZeroAndProductTypeIsConsu = this.currentOrder.orderlines.models.find(l => l.product.type == 'consu' && l.get_price_with_tax() <= 0 && !l.coupon_program_id && !l.promotion)
                if (lineIsAmountSmallerThanZeroAndProductTypeIsConsu && this.currentOrder.picking_type_id) {
                    const pickingType = this.env.pos.stock_picking_type_by_id[selectedOrder.picking_type_id]
                    if (!pickingType['return_picking_type_id']) {
                        extendValidate = false
                        this.env.pos.alert_message({
                            title: this.env._t('Warning'),
                            body: this.env._t('Your POS [Operation Type]: [ ') + pickingType.name + this.env._t(' ] not set Return Picking Type. Please set it for Return Packing bring stock on hand come back Your POS Stock Location. Operation Type for return required have Default Source Location difference Default Destination Location. Is correctly if Destination Location is your POS stock Location')
                        })
                    }
                }
                const lineIsCoupon = this.currentOrder.orderlines.models.find(l => l.gift_card_code || l.coupon_program_id);
                var check_giftcard = this.currentOrder.paymentlines.models.find(l => l.gift_card_code);
                if ((lineIsCoupon || check_giftcard) && this.env.pos.config.validate_coupon) {
                    let validate = await this.env.pos._validate_action(this.env._t('Order add Coupon / Giftcard, required need Manager Approve'));
                    if (!validate) {
                        extendValidate = false
                    }
                }
                const isValid = await super._isOrderValid()
                if (isValid) {
                    if (this.currentOrder.get_total_with_tax() < 0 && this.env.pos.config.return_covert_to_coupon && this.env.pos.config.return_coupon_program_id) {
                        let {confirmed, payload: confirming} = await this.showPopup('ConfirmPopup', {
                            title: this.env._t('Are you want Covert Refund Amount: ') + this.env.pos.format_currency(-this.currentOrder.get_total_with_tax(),false,this.currentOrder.currency) + this.env._t(' to Coupon for next Order'),
                            body: this.env._t('Coupon Amount can use any Times, any next Orders') + this.env.pos.format_currency(-this.currentOrder.get_total_with_tax(),false,this.currentOrder.currency)
                        })
                        if (confirmed) {
                            if (this.currentOrder.get_paymentlines().length > 0) {
                                this.currentOrder.paymentlines.models.forEach(function (p) {
                                    self.currentOrder.remove_paymentline(p)
                                })
                            }
                            let partner_id = null;
                            if (this.currentOrder.get_client()) {
                                partner_id = this.currentOrder.get_client().id
                            }
                            let couponValue = await this.rpc({
                                model: 'coupon.generate.wizard',
                                method: 'covert_return_order_to_giftcards',
                                args: [[], this.env.pos.config.return_coupon_program_id[0], -this.currentOrder.get_total_with_tax(), partner_id, this.env.pos.config.id, this.currentOrder.name],
                            }, {
                                shadow: true,
                                timeout: 65000
                            })
                            this.currentOrder['coupon_code'] = couponValue.coupon_code
                            await this.env.pos.do_action('coupon.report_coupon_code', {
                                additional_context: {
                                    active_id: couponValue['coupon_id'],
                                    active_ids: [couponValue['coupon_id']],
                                }
                            });
                        }
                    }
                }


                if (this.env.pos.config.warning_odoo_offline && !this.env.pos.offlineModel && !this.env.pos.pushOrderInBackground) {
                    const iot_url = this.env.pos.session.origin;
                    const connection = new Session(void 0, iot_url, {
                        use_cors: true
                    });
                    let pingServer = await connection.rpc('/pos/passing/login', {}).then(function (result) {
                        return result
                    }, function (error) {
                        extendValidate = false
                        return false;
                    })
                    if (!pingServer) {
                        this.env.pos.alert_message({
                            title: this.env._t('Warning'),
                            body: this.env._t('Your Internet has Problem or your Server Offline !'),
                        });
                    }
                    extendValidate = true
                }


                if (isValid && extendValidate) {
                    Gui.playSound('bell');
                } else {
                    Gui.playSound('error');
                }
                return isValid && extendValidate
            }

            async inputVoucherCode() {
                const due = this.currentOrder.get_due();
                if (due <= 0) {
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Error'),
                        body: this.env._t('Order full fill Amount, can not use Voucher')
                    })
                }
                const {confirmed, payload} = await this.showPopup('TextInputPopup', {
                    title: _t('You can Scan to Voucher Barcode or Input Code direct here !'),
                    body: _t('Please input Voucher Code or Number bellow'),
                    startingValue: '',
                    confirmText: this.env._t('Validate Code'),
                    cancelText: this.env._t('Close'),
                });
                if (confirmed) {
                    let code = payload;
                    let selectedOrder = this.env.pos.get_order();
                    let order_lines = selectedOrder.get_orderlines();
                    let product_ids = order_lines.map((l)=>l.product.id);
                    if(!code){
                        return this.showPopup('ErrorPopup', {
                            title: _t('Warning'),
                            body: _t('Voucher Code not found'),
                        })
                    }
                    if (code) {
                        let voucher = await this.env.pos.rpc({
                            model: 'pos.voucher',
                            method: 'get_voucher_by_code',
                            args: [code, product_ids],
                        })
                        if (voucher == -1) {
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Error'),
                                body: this.env._t('Voucher not found or Voucher have Expired Date or Voucher already used')
                            });
                        } 

                        if (voucher == -2) {
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Error'),
                                body: this.env._t('Voucher not Valid for The Order')
                            });
                        } else {
                            var order = this.env.pos.get_order();
                            if (order) {
                                if(voucher.brand_ids && voucher.brand_ids.length){
                                    let is_in_brand = false;
                                    order.orderlines.models.forEach(l => {
                                        let product_brand_ids = l.product.product_brand_ids;
                                        if(product_brand_ids && product_brand_ids.length){
                                            for (let product_brand_id of product_brand_ids){
                                                if(voucher.brand_ids.includes(product_brand_id) == true){
                                                    is_in_brand = true;
                                                    break;
                                                }
                                            }
                                        }
                                    });
                                    if(!is_in_brand){
                                        return this.showPopup('ErrorPopup', {
                                            title: this.env._t('Error'),
                                            body: this.env._t("Voucher can't be used for this product brand")
                                        });
                                    }
                                }
                                return order.client_use_voucher_new(voucher);
                            }
                        }
                    }
                }
            }

            async OrderSplitLine() {
                const order = this.env.pos.get_order();
                if (order.get_orderlines().length > 0) {
                    this.showScreen('SplitBillScreen');
                    
                }
                else{
                    this.showPopup('ConfirmPopup', {
                        title: this.env._t('Please select Minimum 1 Item'),
                        body: this.env._t('And click to button "Transfer to another Table"'),
                        disableCancelButton: true,
                    })
                }
            }

            async covertToVoucher() {
                const selectedOrder = this.currentOrder
                let value = selectedOrder.get_total_with_tax()
                if (value < 0) {
                    value = -value
                }
                if (value == 0) {
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Error'),
                        body: this.env._t('It not possible covert Order with amount 0 to Voucher')
                    });
                }
                let {confirmed, payload: confirming} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Covert Total Amount to Voucher'),
                    body: this.env._t('Are you want covert ' + this.env.pos.format_currency(value,false,this.currentOrder.currency) + ' of Order to Voucher ?')
                })
                if (confirmed) {
                    let number = await this.env.pos._getVoucherNumber()
                    const {confirmed, payload} = await this.showPopup('PopUpPrintVoucher', {
                        title: this.env._t('Covert Order to Voucher, current Order will drop and covert to Voucher'),
                        number: number,
                        value: value,
                        period_days: this.env.pos.config.expired_days_voucher,
                    });
                    if (confirmed) {
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
                            selectedOrder.destroy({'reason': 'abandon'});
                            this.env.pos.do_action('equip3_pos_masterdata.report_pos_voucher_small_size', {
                                additional_context: {
                                    active_ids: [voucher.id],
                                }
                            });
                            return this.showScreen('ReportScreen', {
                                report_html: report_html
                            });
                        } else {
                            this.env.pos.alert_message({
                                title: this.env._t('Error'),
                                body: error,
                            })
                        }
                    }
                }
            }

            async selectClient() {
                await super.selectClient()
                posbus.trigger('set-screen', 'Payment')
            }


        }
    Registries.Component.extend(PaymentScreen, RetailPaymentScreen);

    return RetailPaymentScreen;
});
