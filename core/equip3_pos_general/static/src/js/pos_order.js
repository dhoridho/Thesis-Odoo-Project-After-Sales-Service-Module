odoo.define('equip3_pos_general.pos_order', function (require) {
    'use strict';
    
    const models = require('point_of_sale.models');
    const OrderWidget = require('point_of_sale.OrderWidget');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen')
    const OrderSummary = require('point_of_sale.OrderSummary');
    const framework = require('web.framework');

    const {Gui} = require('point_of_sale.Gui');
    const {useListener} = require('web.custom_hooks');
    const {posbus} = require('point_of_sale.utils');
    const {useState} = owl;
    var rpc = require('web.rpc');

    const OrderSummaryExt = (OrderSummary) =>
        class extends OrderSummary {
            constructor() {
                super(...arguments);
            }
            get get_points() {
                return this.env.pos.get_order().get_client_points()
            }
        }
    Registries.Component.extend(OrderSummary, OrderSummaryExt);

    const ProductScreenExt = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);

                this.pos_sync_session_order = useState({ 
                    state: '',
                    p_state: '',
                });
            }
            async OnClickCustomer() { // single screen
                this.env.pos.syncProductsPartners()
                posbus.trigger('set-screen', 'Clients') // single screen
                setTimeout(function () {
                    $('.searchbox-client >input').focus()
                }, 200)
            }
            async reloadMasterData() {
                await this.env.pos.syncProductsPartners()
       
                const coupon_model = this.env.pos.models.find(m => m.model == 'coupon.coupon')
                if (coupon_model) {
                    await this.env.pos.load_server_data_by_model(coupon_model)
                }
                const pricelist_model = this.env.pos.models.find(m => m.model == 'product.pricelist')
                if (pricelist_model) {
                    await this.env.pos.load_server_data_by_model(pricelist_model)
                    this.env.pos.getProductPricelistItems()
                }
            }
            async ShowSummary(ev) {
                ev.preventDefault();
                ev.stopPropagation();
                let summary = $('.order-summary-data');
                let arrow = $('.button-summary-minimize');
                if (summary.length && arrow.length) {
                    if ($(arrow[0]).hasClass('fa-angle-double-up')){
                        $(arrow[0]).removeClass('fa-angle-double-up')
                        $(arrow[0]).addClass('fa-angle-double-down')
                    } else {
                        $(arrow[0]).removeClass('fa-angle-double-down')
                        $(arrow[0]).addClass('fa-angle-double-up')
                    }
                    if ($(summary[0]).hasClass('oe_hidden')) {
                        $(summary[0]).removeClass('oe_hidden')
                    }
                    else {
                        $(summary[0]).addClass('oe_hidden')
                    }
                }
            }
            async setDiscount() {
                let selectedOrder = this.env.pos.get_order();
                let {confirmed, payload: discount} = await this.showPopup('NumberPopup', {
                    title: this.env._t('Which value of discount Value would you apply to Order ?'),
                    startingValue: 0,
                    confirmText: this.env._t('Apply'),
                    cancelText: this.env._t('Remove Discount'),
                })
                if (confirmed) {
                    selectedOrder.set_discount_value(parseFloat(discount))
                }
            }
            async setTaxes() {
                let order = this.env.pos.get_order();
                let selectedLine = order.get_selected_orderline();
                if (!selectedLine) {
                    return this.env.pos.alert_message({
                        title: this.env._t('Error'),
                        body: this.env._t('Have not any line in cart')
                    })
                }
                if (selectedLine.is_return || order.is_return) {
                    return this.env.pos.alert_message({
                        title: this.env._t('Error'),
                        body: this.env._t('it not possible set taxes on Order return')
                    })
                }
                else {
                    return this.env.pos.alert_message({
                        title: this.env._t('Error'),
                        body: this.env._t('Please selected 1 line for set taxes')
                    })
                }

            }


            async onClickSyncSessionOrderSubmit(){

                const self = this;
                let selectedOrder = self.env.pos.get_order();
                framework.blockUI();
                self.pos_sync_session_order.submit_state = 'connecting';
                let result = this.env.pos.sumbit_session_order(selectedOrder);
                self.pos_sync_session_order.submit_state = 'done';
                framework.unblockUI();

                if(result){
                    self.showScreen('TicketScreen', {'sync_session_order': 1});
                }
            }

            async _syncSessionOrder(){
                let self = this;
                let selectedOrder = self.env.pos.get_order();
                if (self.env.pos.config.is_manual_sync_for_sync_between_session){
                    if(!selectedOrder.is_return && self.pos_sync_session_order.p_state != 'connecting'){
                        self.pos_sync_session_order.p_state = 'connecting';
                        let session_order_datas = await self.env.pos.get_session_order_datas(selectedOrder);
                        self.pos_sync_session_order.p_state = 'done';
                        if(session_order_datas.status == 'failed'){
                            self.env.pos.alert_message({
                                title: self.env._t('Warning'),
                                body: self.env._t('Failed sync order, please try again.'),
                            });
                        }
                        if(session_order_datas.status == 'success' && session_order_datas.data.length){
                            let data_order = session_order_datas.data[0];
                            if(data_order.state != 'draft'){
                                let __order_name = data_order.uid;
                                if (data_order.data && data_order.data.name){
                                    __order_name = data_order.data.name;
                                }
                                let {confirmed, payload: result} = await self.showPopup('ConfirmPopup', {
                                    title: self.env._t('Warning !!!'),
                                    body: self.env._t('(' + __order_name + ') already Paid in another session'),
                                    confirmText: 'Continue Payment',
                                    disableCancelButton: true,
                                });
                                // Change Receipt Number
                                selectedOrder.sequence_number = self.env.pos.pos_session.sequence_number;
                                selectedOrder.uid  = selectedOrder.generate_unique_id();
                                selectedOrder.name = _.str.sprintf(self.env._t("Order %s"), selectedOrder.uid);

                                selectedOrder.trigger('change', selectedOrder);
                                self.env.pos.pos_session.sequence_number = self.env.pos.pos_session.sequence_number + 1; 
                            }
                        }
                    }
                }
            }

            async _onClickPayBtn() {
                var self = this;
                let selectedOrder = this.env.pos.get_order();

                this.env.pos._check_connection();
                
                var apply_promotion_succeed = self.env.pos.apply_promotion_succeed;

                if(this.env.pos.selected_order_method != 'employee-meal'){
                    if(this.env.pos.config.promotion_auto_add && this.env.pos.apply_promotion_succeed){
                        this.env.pos.apply_promotion_succeed = false;
                        this.showScreen('PaymentScreen');
                        return;
                    }
                }
                

                //TODO: check and sync session order before payment
                if(selectedOrder.sync_write_date){
                    await self._syncSessionOrder();
                }

                //Employee Meal Limit Budget
                if(this.env.pos.selected_order_method == 'employee-meal'){
                    if(!selectedOrder.employeemeal_budget){
                        $('.pos_new_section .custom_column.btn-employee-meal').addClass('highlight');
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t('Please choose employee first'),
                            confirmText: 'OK',
                            cancelText: ''
                        });
                        return false;
                    }

                    let msg_employee_name = '';
                    let limit_budget = this.env.pos.config.limit_budget;
                    if(typeof selectedOrder.employeemeal_budget != 'undefined'){
                        limit_budget = selectedOrder.employeemeal_budget;
                        msg_employee_name += ' ('+selectedOrder.employeemeal_employee_name+' remaining budget is '
                            + this.env.pos.format_currency(selectedOrder.employeemeal_budget,undefined,selectedOrder.currency) +')';
                    }
                    if(selectedOrder.get_total_with_tax() > limit_budget){
                        console.log("Employee Budget limit is :", limit_budget);
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t('Employee meal reach budget limitation\n' + msg_employee_name),
                            confirmText: 'OK',
                            cancelText: ''
                        });
                        return false;
                    }
                    //set payment
                    this.AddEmployeeBudgetPayment(selectedOrder);
                }else{
                    // remove existing employee budget
                    selectedOrder.paymentlines.models.forEach(function (l) {
                        if(l.payment_method.name.toLowerCase().trim() == 'employee budget'){
                            l.allow_remove = true;
                            selectedOrder.remove_paymentline(l);
                        }
                    });
                }


                if (this.env.session.restaurant_order) {
                    if (!this.env.pos.first_order_succeed) {
                        let {confirmed, payload: guest_total} = await this.showPopup('NumberPopup', {
                            title: this.env._t('How many guests on your table ?'),
                            startingValue: 0
                        })
                        if (confirmed) {
                            selectedOrder.set_customer_count(parseInt(guest_total))
                        } else {
                            return this.showScreen('ProductScreen')
                        }
                    }
                    let {confirmed, payload: note} = await this.showPopup('TextAreaPopup', {
                        title: this.env._t('Have any notes for Cashiers/Kitchen Room of Restaurant ?'),
                    })
                    if (confirmed) {
                        if (note) {
                            selectedOrder.set_note(note)
                        }
                    }
                    if (selectedOrder.get_allow_sync()) {
                        let orderJson = selectedOrder.export_as_JSON()
                        orderJson.state = 'Waiting'
                        this.env.session.restaurant_order = false
                        this.env.pos.pos_bus.send_notification({
                            data: orderJson,
                            action: 'new_qrcode_order',
                            order_uid: selectedOrder.uid,
                        });
                        this.env.session.restaurant_order = true
                    } else {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Error'),
                            body: this.env._t('POS missed setting Sync Between Sessions. Please contact your admin resolve it')
                        })
                    }
                    this.env.pos.config.login_required = false // todo: no need login when place order more items
                    this.env.pos.first_order_succeed = true
                    this.env.pos.placed_order = selectedOrder
                    return this.showTempScreen('RegisterScreen', {
                        selectedOrder: selectedOrder
                    })
                } else {
                    if(this.env.pos.selected_order_method != 'employee-meal'){
                        if (this.env.pos.config.promotion_ids && this.env.pos.config.promotion_auto_add) {
                            selectedOrder.apply_promotion();

                            let tebus_murah_promotions = selectedOrder.get_promotions_active()['promotions_active'].filter((p)=>p.new_type == 'Tebus Murah'  && p.type != '17_tebus_murah_by_selected_brand');
                            if(tebus_murah_promotions){
                                for(let tebus_murah_promotion of tebus_murah_promotions){
                                    await selectedOrder.select_promotion_tebus_murah(tebus_murah_promotion);
                                }
                            }
                            // reset the apply promotion button
                            self.env.pos.apply_promotion_succeed = true;
                        }
                    }
                    if (selectedOrder.orderlines.length == 0) {
                        return this.env.pos.alert_message({
                            title: this.env._t('Error'),
                            body: this.env._t('Your Order is Blank Cart Items, please add items to cart before do Payment Order'),
                        })
                    }
                    let hasValidMinMaxPrice = selectedOrder.isValidMinMaxPrice()
                    if (!hasValidMinMaxPrice) {
                        return true
                    }
                    if (selectedOrder.is_to_invoice() && !selectedOrder.get_client()) {
                        const currentClient = selectedOrder.get_client();
                        const {confirmed, payload: newClient} = await this.showTempScreen(
                            'ClientListScreen',
                            {client: currentClient}
                        );
                        if (confirmed) {
                            selectedOrder.set_client(newClient);
                            selectedOrder.updatePricelist(newClient);
                        } else {
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Error'),
                                body: this.env._t('Order to Invoice, Required Set Customer'),
                            })
                        }
                    }
                    if (selectedOrder && selectedOrder.get_total_with_tax() == 0) {
                        this.env.pos.alert_message({
                            title: this.env._t('Warning !!!'),
                            body: this.env._t('Total Amount of Order is : ') + this.env.pos.format_currency(0,undefined,selectedOrder.currency)
                        })
                    }
                    if (!this.env.pos.config.allow_order_out_of_stock) {
                        const quantitiesByProduct = selectedOrder.product_quantity_by_product_id()
                        let isValidStockAllLines = true;
                        for (let n = 0; n < selectedOrder.orderlines.models.length; n++) {
                            let orderline = selectedOrder.orderlines.models[n];
                            let currentStockInCart = quantitiesByProduct[orderline.product.id]
                            if (orderline.product.type == 'product' && orderline.product.get_qty_available() < currentStockInCart) {
                                isValidStockAllLines = false;

                                this.env.pos.alert_message({
                                    title: this.env._t('Error'),
                                    body: orderline.product.display_name + this.env._t(' not enough for sale. Current stock on hand only have: ') + orderline.product.get_qty_available() + this.env._t(' . Your cart add ') + currentStockInCart + this.env._t(' (items). Bigger than stock on hand have of Product !!!'),
                                    timer: 10000
                                })
                            }

                            if (['serial', 'lot'].includes(orderline.product.tracking)) {
                                let lot_names = [];
                                for(let lot_line of orderline.get_lot_lines()){
                                    lot_names.push(lot_line.attributes.lot_name);
                                }
                                let lot_max_quantity = orderline.product.get_lot_qty_available(lot_names);

                                if (orderline.product.tracking == 'serial') {
                                    if(lot_max_quantity <= 0 || lot_max_quantity < orderline.quantity){
                                        isValidStockAllLines = false;

                                        this.env.pos.alert_message({
                                            title: this.env._t('Warning'),
                                            body: 'Lot/Serial: "' + lot_names.join() + '"' + this.env._t(' not enough for sale'),
                                            timer: 10000
                                        })
                                    }
                                }
                                if (orderline.product.tracking == 'lot') {
                                    if(lot_max_quantity <= 0){
                                        isValidStockAllLines = false;

                                        this.env.pos.alert_message({
                                            title: this.env._t('Warning'),
                                            body: 'Lot/Serial: "' + lot_names.join() + '"' + this.env._t(' not enough for sale'),
                                            timer: 10000
                                        })
                                    }
                                    if(orderline.quantity > lot_max_quantity){
                                        orderline.set_quantity(lot_max_quantity);
                                        isValidStockAllLines = false;

                                        this.env.pos.alert_message({
                                            title: this.env._t('Warning'),
                                            body: 'Lot/Serial: "' + lot_names.join() + '"' + this.env._t(' Exceed available stock, qty automatically set to max stock'),
                                            timer: 10000
                                        })
                                    }
                                }
                                
                            }

                        }
                        if (!isValidStockAllLines) {
                            return false;
                        }
                    }
                   
                    if (this.env.pos.couponProgramsAutomatic && this.env.pos.config.coupon_program_apply_type == 'auto') {
                        this.env.pos.automaticSetCoupon()
                    }
                    if (this.env.pos.config.rounding_automatic) {
                        await this.roundingTotalAmount()
                    }
                }
                let is_promotion = this.env.pos.config.promotion_auto_add && !apply_promotion_succeed;
                if(this.env.pos.selected_order_method == 'employee-meal'){
                    is_promotion = false;
                }
                if (is_promotion){
                    self.env.pos.apply_promotion_succeed = true;
                    this.render();
                } else{
                    this.showScreen('PaymentScreen');
                }
            }
            async AddEmployeeBudgetPayment(selectedOrder){
                let method = _.find(this.env.pos.payment_methods, function (method) {
                    return method.name.toLowerCase().trim() == 'employee budget';
                });
                if (!method){
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Warning'),
                        body: this.env._t('Employee Budget is not found'),
                        cancelText: '',
                    });
                }
                if (method) {
                    // remove existing payment method
                    selectedOrder.paymentlines.models.forEach(function (l) {
                        selectedOrder.remove_paymentline(l);
                    });
                    selectedOrder.paymentlines.models.forEach(function (l) {
                        if(l.payment_method.name.toLowerCase().trim() == 'employee budget'){
                            l.allow_remove = true;
                            selectedOrder.remove_paymentline(l);
                        }
                    });

                    let limit_budget = this.env.pos.config.employee_meal_limit_budget;
                    if(typeof selectedOrder.employeemeal_budget != 'undefined'){
                        limit_budget = selectedOrder.employeemeal_budget;
                    }
                    let orderlines = selectedOrder.get_orderlines();
                    let amount = 0;
                    for (var i = orderlines.length - 1; i >= 0; i--) {
                        amount += orderlines[i].get_price_with_tax();
                    }
                    if(amount > limit_budget){
                        amount = limit_budget;
                    }
                    if(amount > 0){
                        selectedOrder.add_paymentline(method);
                        let paymentline = selectedOrder.selected_paymentline; 
                        paymentline.set_amount(amount);
                    }
                }
            }
            async AddNewCustomer() {
                let {confirmed, payload: results} = await this.showPopup('PopUpCreateCustomer', {
                    title: this.env._t('Create New Customer'),
                    mobile: ''
                })
                if (confirmed) {
                    if (results.error) {
                        return this.env.pos.alert_message({
                            title: this.env._t('Error'),
                            body: results.error
                        })
                    }
                    const partnerValue = {
                        'name': results.name,
                    }
                    if (results.image_1920) {
                        partnerValue['image_1920'] = results.image_1920.split(',')[1]
                    }
                    if (results.title) {
                        partnerValue['title'] = results.title
                    }
                    if (!results.title && this.env.pos.partner_titles) {
                        partnerValue['title'] = this.env.pos.partner_titles[0]['id']
                    }
                    if (results.street) {
                        partnerValue['street'] = results.street
                    }
                    if (results.city) {
                        partnerValue['city'] = results.city
                    }
                    if (results.street) {
                        partnerValue['street'] = results.street
                    }
                    if (results.phone) {
                        partnerValue['phone'] = results.phone
                    }
                    if (results.mobile) {
                        partnerValue['mobile'] = results.mobile
                    }

                    if (results.birthday_date) {
                        partnerValue['birthday_date'] = results.birthday_date
                    }
                    if (results.barcode) {
                        partnerValue['barcode'] = results.barcode
                    }
                    if (results.comment) {
                        partnerValue['comment'] = results.comment
                    }
                    if (results.property_product_pricelist) {
                        partnerValue['property_product_pricelist'] = results.property_product_pricelist
                    } else {
                        partnerValue['property_product_pricelist'] = this.env.pos.pricelists[0].id
                    }
                    if (results.country_id) {
                        partnerValue['country_id'] = results.country_id
                    }
                    let partner_id = await this.rpc({
                        model: 'res.partner',
                        method: 'create',
                        args: [partnerValue],
                        context: {}
                    })
                    await this.reloadMasterData()
                    const partner = this.env.pos.db.partner_by_id[partner_id]
                    this.env.pos.get_order().set_client(partner)
                }
            }
            OpenFeatureButtonsMobile(){
                if ($('.pos_new_section').hasClass('pos-hidemobile')){
                    $('.pos_new_section').removeClass('pos-hidemobile')
                }
                else{
                    $('.pos_new_section').addClass('pos-hidemobile')
                }
                
            }
            OpenFeatureButtons() {
                this.env.pos.showAllButton = !this.env.pos.showAllButton
                this.state.showButtons = this.env.pos.showAllButton
            }

            

            async OnKeydown(event) {
                const order = this.env.pos.get_order();
                if (event.key === 'Enter' && this.state.inputCustomer != '') {
                    const partners = this.env.pos.db.search_partner(this.state.inputCustomer)
                    this.state.countCustomers = partners.length
                    if (partners.length > 1 && partners.length < 10) {
                        let list = []
                        for (let i = 0; i < partners.length; i++) {
                            let p = partners[i]
                            let pName = p.display_name
                            if (p.phone) {
                                pName += this.env._t(' , Phone: ') + p.phone
                            }
                            if (p.mobile) {
                                pName += this.env._t(' , Mobile: ') + p.mobile
                            }
                            if (p.email) {
                                pName += this.env._t(' , Email: ') + p.email
                            }
                            if (p.barcode) {
                                pName += this.env._t(' , Barcode: ') + p.barcode
                            }
                            list.push({
                                id: p.id,
                                label: pName,
                                isSelected: false,
                                item: p
                            })
                        }
                        let {confirmed, payload: client} = await this.showPopup('SelectionPopup', {
                            title: this.env._t('All Customers have Name or Phone/Mobile or Email or Barcode like Your Input: [ ' + this.state.inputCustomer + ' ]'),
                            list: list,
                            cancelText: this.env._t('Close')
                        })
                        if (confirmed) {
                            order.set_client(client);
                            this.state.countCustomers = 0
                            this.state.inputCustomer = ''
                        }
                    } else if (partners.length > 10) {
                        this.env.pos.alert_message({
                            title: this.env._t('Warning'),
                            body: this.env._t('have many Customers with your type, please type correct [name, phone, or email] customer')
                        })
                    } else if (partners.length == 1) {
                        order.set_client(partners[0]);
                        this.state.inputCustomer = ''
                        this.state.countCustomers = 0
                    } else if (partners.length == 0) {
                        this.env.pos.alert_message({
                            title: this.env._t('Warning'),
                            body: this.env._t('Sorry, We not Found any Customer with Your Type')
                        })
                    }
                } else {
                    const partners = this.env.pos.db.search_partner(this.state.inputCustomer)
                    this.state.countCustomers = partners.length
                }
            }
            setKitchenChecker(){
                this.create_order_list_lines();
            }
            async create_order_list_lines() {
                var self = this;
                //var orderList = this.env.pos.get_order_list()[0].collection.models;
                var order = this.env.pos.get_order();
                //_.each(orderList, function (order) {
                    var vals = {
                        'pos_order_name': order.name,
                        'table_id': order.table.id,
                        'floor_id': order.table.floor_id[0],
                    }
                    console.log(vals)
                    self.removeCheckerLine(vals);
                    _.each(order.get_orderlines(), function (line) {
                        if(line.product.id && line.quantity > 0){
                            vals['product_id'] = line.product.id
                            vals['product_qty'] = line.quantity
                            self.createCheckerLine(vals);
                        }
                    });
                //});
            }
            async removeCheckerLine(vals){
                await this.rpc({
                    model: "kitchen.checker.data",
                    method: "remove_checker_data",
                    args: [vals],
                }).then(function (results) {
                });
            }
            async createCheckerLine(vals){
                await this.rpc({
                    model: "kitchen.checker.data",
                    method: "set_checker_data",
                    args: [vals],
                }).then(function (results) {
                });
            }

        };

    Registries.Component.extend(ProductScreen, ProductScreenExt);

    const RetailOrderWidgetExt = (OrderWidget) =>
        class extends OrderWidget {
            constructor() {
                super(...arguments);

                this.pos_sync_session_order = useState({ state: '', submit_state: '' });
            }

            
            async onClickSyncSessionOrder(){
                let selectedOrder = this.env.pos.get_order();
                this.pos_sync_session_order.state = 'connecting';
                await this.env.pos.sync_session_order(selectedOrder);
                this.pos_sync_session_order.state = 'done';
            }


            async onClickSyncSessionOrderBySubmit(){
                const self = this;
                let selectedOrder = self.env.pos.get_order();
                framework.blockUI();
                self.pos_sync_session_order.submit_state = 'connecting';
                let result = this.env.pos.sumbit_session_order(selectedOrder);
                self.pos_sync_session_order.submit_state = 'done';
                framework.unblockUI();
            }
            
            async clearCart() {
                let selectedOrder = this.env.pos.get_order();
                let orderline = selectedOrder.get_orderlines();




                if (selectedOrder.orderlines.models.length > 0) {
                    let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Warning !!!'),
                        body: this.env._t('Are you want remove all Items in Cart ?')
                    })
                    if (confirmed) {
                        if (this.env.pos.config.validate_remove_line) {
                            let validate = await this.env.pos._validate_action(this.env.pos.env._t('Validate Remove all Items in Cart'));
                            if (!validate) {
                                return false;
                            }
                        }
                        
                        orderline.forEach((orderline) => {
                            var vals = []
                            var product_id = orderline.product.id
                            var qty = orderline.quantity
                            var date = new Date();

                            return rpc.query({
                                model: 'product.cancel',
                                method: 'SavelogProcuctCancel',
                                args: [[], vals, product_id, qty, date],
                            });
                        }); 

                        while (selectedOrder.orderlines.models.length > 0) {
                            selectedOrder.orderlines.models.forEach(l => selectedOrder.remove_orderline(l))
                        }
                        
                        selectedOrder.is_return = false;
                        selectedOrder.reset_client_use_coupon();

                        this.env.pos.alert_message({
                            title: this.env._t('Successfully'),
                            body: this.env._t('Order is empty cart !')
                        })
                    }
                } else {
                    this.env.pos.alert_message({
                        title: this.env._t('Warning !!!'),
                        body: this.env._t('Your Order Cart is blank.')
                    })
                }
            }
            async newOrder() {
                let self = this;
                let selectedOrder = this.env.pos.get_order();
                if (selectedOrder.orderlines.models.length > 0) {
                    let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Warning !!!'),
                        body: this.env._t('Are you want to add new order ?')
                    })
                    if (confirmed) {
                        self.env.pos.add_new_order();
                        let order = self.env.pos.get_order();
                        self.env.pos.set_order(order);
                        this.env.pos.alert_message({
                            title: this.env._t('Success!'),
                            body: this.env._t('New Order is Added !')
                        })
                    }
                } else {
                    this.env.pos.alert_message({
                        title: this.env._t('Warning !!!'),
                        body: this.env._t('Your Order Cart is blank.')
                    })
                }
            }

            // TODO: Show info promotion if fulfil the condition
            show_popup_promotion_information() {
                let is_show = false;
                let in_on_product_screen = $('.product-screen.screen').length;
                let in_on_load_pos = $('.loader .loader-feedback').length;
                let is_open_session_order = $('.screens > .ticket-screen.screen').length;
                if(in_on_product_screen && !in_on_load_pos){
                    is_show = true;
                    if (is_open_session_order){
                        is_show = false;
                    }
                    if (this.order.is_promotion_information == true){
                        is_show = false;
                    }
                    if (this.env.pos.apply_promotion_succeed == true){
                        is_show = false;
                    }
                }
                if (is_show){
                    let promotions = this.order.get_promotions_active()['promotions_active'];
                    if (promotions.length){
                        let priority_promotions = promotions.filter((p)=>p.is_priority && p.note);
                        if (priority_promotions.length){
                            let priority_promotion_note = '';
                            for (let promotion of priority_promotions){
                                priority_promotion_note = promotion.note;
                            }
                            if (priority_promotion_note){
                                Gui.showPopup('ConfirmPopup', { 
                                    title: this.env._t('Promotion Information'),
                                    body: priority_promotion_note,
                                    confirmText: 'Cancel',
                                    disableCancelButton: true,
                                });
                                this.order.is_promotion_information = true;
                            }
                        }
                    }
                }
            }

            // OVERRIDE
            _updateSummary() { 
                let productsSummary = {}
                let totalItems = 0
                let totalQuantities = 0
                let totalCost = 0
                var currency_order = false
                if (this.order) {
                    currency_order = this.order.currency
                    for (let i = 0; i < this.order.orderlines.models.length; i++) {
                        let line = this.order.orderlines.models[i]
                        totalCost += line.product.standard_price * line.quantity
                        if (!productsSummary[line.product.id]) {
                            productsSummary[line.product.id] = line.quantity
                            totalItems += 1
                        } else {
                            productsSummary[line.product.id] += line.quantity
                        }
                        totalQuantities += line.quantity
                    }

                    this.show_popup_promotion_information();
                }
                const discount = this.order ? this.order.get_total_discount_wo_pricelist() : 0;
                this.state.discount = this.env.pos.format_currency(discount,undefined,currency_order);

                const totalWithOutTaxes = this.order ? this.order.get_total_without_tax() : 0;
                this.state.totalWithOutTaxes = this.env.pos.format_currency(totalWithOutTaxes,undefined,currency_order);
                this.state.margin = this.env.pos.format_currency(totalWithOutTaxes - totalCost,undefined,currency_order)
                
                const totalWithTaxes = this.order ? this.order.get_total_with_tax() : 0;
                this.state.totalWithTaxes = this.env.pos.format_currency(totalWithTaxes,undefined,currency_order);

                this.state.totalItems = this.env.pos.format_currency_no_symbol(totalItems)
                this.state.totalQuantities = this.env.pos.format_currency_no_symbol(totalQuantities)

                const total_with_tax_without_rounding = this.order ? this.order.get_total_with_tax_without_rounding() : 0

                const total = this.order ? totalWithTaxes : 0;
                const tax = this.order ? total_with_tax_without_rounding - totalWithOutTaxes : 0;
                this.state.total = this.env.pos.format_currency(total,undefined,currency_order);
                this.state.tax = this.env.pos.format_currency(tax,undefined,currency_order);
                this.state.rounding_order = this.order ? totalWithTaxes - total_with_tax_without_rounding : 0;
                this.render();


                if (total <= 0) {
                    this.state.tax = this.env.pos.format_currency(0,undefined,currency_order);
                }
                if (this.env.pos.config.customer_facing_screen) {
                    this.env.pos.trigger('refresh.customer.facing.screen');
                }
                if (this.env.pos.config.iface_customer_facing_display) {
                    this.env.pos.send_current_order_to_customer_facing_display();
                }
                var self = this;
                this.render().then(function(){
                var $subElement = $('.sub-value');
                    if($subElement.length > 0){
                        $subElement[$subElement.length - 1].innerText = self.state.totalWithTaxes
                    }    
                })

                var total_without_tax_without_discount = 0;
                var totalPayment = self.state.totalWithTaxes;
                if (this.order) {
                    total_without_tax_without_discount = this.env.pos.format_currency(this.order.get_total_wo_tax_after_pricelist(),undefined,currency_order);
                    
                    if(typeof this.order.is_exchange_order != 'undefined'){
                        if(this.order.is_exchange_order && this.order.exchange_amount){
                            let exchangeAmount = this.order.exchange_amount;

                            let has_product_exchange = false;
                            let _orderLines = this.order.get_orderlines();
                            for (var i = _orderLines.length - 1; i >= 0; i--) {
                                if(_orderLines[i].quantity < 0 || _orderLines[i].is_product_exchange){
                                    has_product_exchange = true
                                    break;
                                }
                            }

                            $('.summary-exchange-amount-line').hide();
                            if(has_product_exchange){
                                if(totalWithTaxes > 0){
                                    if(totalWithTaxes <= exchangeAmount){
                                        totalPayment = this.env.pos.format_currency(0,undefined,currency_order);
                                    }
                                    if(totalWithTaxes > exchangeAmount){
                                        let totalWithTaxesExchangeAmount = totalWithTaxes - exchangeAmount;
                                        totalPayment = this.env.pos.format_currency(totalWithTaxesExchangeAmount,undefined,currency_order);
                                    }
                                }

                                let SummaryExchangeAmount = $('.summary-exchange-amount');
                                $('.summary-exchange-amount-line').show();
                                if (SummaryExchangeAmount.length) SummaryExchangeAmount[0].innerText = this.env.pos.format_currency(exchangeAmount);
                            }
                        }
                    }
                }


                if(this.env.pos.selected_order_method == 'employee-meal'){
                    let SummaryEmployeeBudget = $('.summary-employee-budget');
                    let $employee_name = $('.summary-employee-budget-line .employee_name')
                    let limit_budget = this.env.pos.config.employee_meal_limit_budget;

                    $employee_name.text('');
                    if(this.order){
                        if(typeof this.order.employeemeal_budget != 'undefined'){
                            limit_budget =  this.order.employeemeal_budget;
                            $employee_name.text(' (' + this.order.employeemeal_employee_name + ')');
                        }
                    }
                    if (SummaryEmployeeBudget.length) SummaryEmployeeBudget[0].innerText = this.env.pos.format_currency(limit_budget,undefined,currency_order);
                    $('.summary-employee-budget-line').show();

                    if(totalWithTaxes <= limit_budget){
                        this.state.totalWithTaxes = this.env.pos.format_currency(0,undefined,currency_order);
                        totalPayment = 0;
                    }else{
                        this.state.totalWithTaxes = this.env.pos.format_currency((totalWithTaxes - limit_budget),undefined,currency_order);
                        totalPayment = this.env.pos.format_currency((totalWithTaxes - limit_budget),undefined,currency_order);
                    }

                    $('.order-summary-data .summary-before-tax').parent().hide();
                    $('.order-summary-data .summary-tax').parent().hide();
                    $('.order-summary-data .summary-discount').parent().hide();
                }

                // Update Summary
                let SummaryBeforeTax = $('.summary-before-tax');
                if (SummaryBeforeTax.length) SummaryBeforeTax[0].innerText = total_without_tax_without_discount;
                let SummaryDiscount = $('.summary-discount');
                if (SummaryDiscount.length) SummaryDiscount[0].innerText = this.state.discount
                let SummaryTax = $('.summary-tax');
                if (SummaryTax.length) SummaryTax[0].innerText = this.state.tax
                let SummaryGrandTotal = $('.summary-grand-total');
                if (SummaryGrandTotal.length) SummaryGrandTotal[0].innerText = this.state.totalWithTaxes
                let SummaryItems = $('.summary-item');
                if (SummaryItems.length) SummaryItems[0].innerText = this.state.totalItems
                let SummaryQty = $('.summary-qty');
                if (SummaryQty.length) SummaryQty[0].innerText = this.state.totalQuantities
                let SummaryRO = $('.summary-rounding_order');
                if (SummaryRO.length) SummaryRO[0].innerText = this.env.pos.format_currency(this.state.rounding_order,undefined,currency_order);

                if($('.order-total-btn .pos_order_total').length > 0){
                    $('.order-total-btn .pos_order_total')[0].innerText = totalPayment;
                }
            }
        };

    Registries.Component.extend(OrderWidget, RetailOrderWidgetExt);
    return { OrderSummary, OrderWidget, ProductScreen }
})