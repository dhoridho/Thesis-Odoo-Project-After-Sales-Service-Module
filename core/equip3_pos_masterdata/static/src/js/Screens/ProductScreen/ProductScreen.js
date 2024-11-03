odoo.define('equip3_pos_masterdata.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen')
    const Registries = require('point_of_sale.Registries')
    const {posbus} = require('point_of_sale.utils')
    var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents
    const {useListener} = require('web.custom_hooks')
    const {useState} = owl.hooks
    const {Gui} = require('point_of_sale.Gui')
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    let lockedUpdateOrderLinesTimeout = null;
    let scrollCartToBottomTimeout = null;

    const RetailProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
                this.buffered_key_events = [];
                this._onKeypadKeyDown = this._onKeypadKeyDown.bind(this);
                useListener('show-popup', this.removeEventKeyboad);
                if (this.env.pos.config.showFullFeatures == undefined) {
                    this.env.pos.showFullFeatures = true
                } else {
                    this.env.pos.showFullFeatures = this.env.pos.config.showFullFeatures
                }
                let status = this.showCashBoxOpening()
                this.state = useState({
                    cashControl: status,
                    numpadMode: 'quantity',
                    screen: 'Products',
                    openCart: true,
                    displayCheckout: true,
                    showButtons: this.env.pos.showAllButton
                })
                useListener('remove-selected-customer', this._onRemoveSelectedClient);
                useListener('remove-selected-order', this._onRemoveSelectedOrder);
                useListener('open-cart', this._openCart);
                useListener('show-buttons', this._openListButtons);
            }

            mounted() {
                super.mounted();
                posbus.on('closed-popup', this, this.addEventKeyboad);
                posbus.on('reset-screen', this, this._resetScreen);
                posbus.on('set-screen', this, this._setScreen);
                posbus.on('close-cash-screen', this, this._closingOpenCashScreen);
                posbus.on('open-cash-screen', this, this._openOpenCashScreen);
                this.addEventKeyboad()
                posbus.on('blur.search.products', this, () => {
                    this.state.displayCheckout = true
                })
                posbus.on('click.search.products', this, () => {
                    this.state.displayCheckout = false
                })
                posbus.on('open-list-feature-buttons', this, this._openListButtons);
                posbus.on('change-list-feature-buttons', this, this._changeListButtons);

            }

            willUnmount() {
                super.willUnmount()
                posbus.off('closed-popup', this, null)
                posbus.off('reset-screen', this, null)
                posbus.off('set-screen', this, null)
                posbus.off('close-cash-screen', this, null)
                posbus.off('open-cash-screen', this, null)
                posbus.off('blur.search.products', null, this)
                posbus.off('click.search.products', null, this)
                posbus.off('open-list-feature-buttons', null, this)
                posbus.off('change-list-feature-buttons', null, this)
                this.removeEventKeyboad()
            }

            _openListButtons() {
                this.env.pos.showAllButton = !this.env.pos.showAllButton
                this.state.showButtons = this.env.pos.showAllButton
            }
            _changeListButtons(){
                this.state.showButtons = this.env.pos.showAllButton
            }

            _product_multi_barcode_(code) {
                if (!code || code == "") {
                    return false
                }
                if(this.env.pos.product_multi_barcode !== undefined){
                    var product_barcode = this.env.pos.product_multi_barcode.filter(l => l.name == code)
                    if( product_barcode.length > 0 ) {
                        var product = this.env.pos.db.getAllProducts().filter(p =>  p['id'] == product_barcode[0].product_id[0])
                        if(product.length>0){
                            
                            var product_id = product_barcode[0].product_id[0]
                            this.env.pos.db.clear_cache_product_price_by_id('product.product', product_id);
                            var order = this.env.pos.get_order()
                            var dict_add = {'quantity': 1}
                            var uom_id = product_barcode[0].uom_id[0]
                            dict_add['uom_id'] = uom_id
                            dict_add['price'] = product[0].get_price(this.env.pos._get_active_pricelist(), 1, 0, uom_id);
                            order.add_product(product[0], dict_add);
                            this.env.pos.db.clear_cache_product_price_by_id('product.product', product_id);
                            return true
                        } else{
                            return false
                        }
                    } else{
                        return false
                    }
                }
            }

            async suggestItemsCrossSelling(product){
                let self = this;
                let order = false;
                let crossItems = false;
                let is_cross_selling = false;

                // TODO: only offer cross selling product once
                if(product.cross_selling) {
                    if(product.product_tmpl_id){
                        crossItems = self.env.pos.cross_items_by_product_tmpl_id[product.product_tmpl_id];
                        if(crossItems){
                            is_cross_selling = true;
                        }
                    }
                    if(is_cross_selling){
                        order = self.env.pos.get_order();
                        if (!order.already_suggest_cross_selling_ids) {
                            is_cross_selling = true;
                        } else {
                            is_cross_selling = true;
                            if(order.already_suggest_cross_selling_ids.includes(product.id)){
                                is_cross_selling = false;
                            }
                        }
                    }
                }

                if(is_cross_selling){
                    if (!order.already_suggest_cross_selling_ids) {
                        order.already_suggest_cross_selling_ids = []
                    }
                    order.already_suggest_cross_selling_ids.push(product.id);

                    let {confirmed, payload: results} =  await Gui.showPopup('CrossSalePopUps', {
                        title: self.env._t('Product Suggestions'),
                        items: crossItems 
                    });
                    if (confirmed) {
                        let selectedCrossItems = results.items;
                        for (let index in selectedCrossItems) {
                            let item = selectedCrossItems[index];
                            var _product = self.env.pos.db.get_product_by_id(item['product_id'][0]);
                            if(_product) {
                                var price = item['list_price'];
                                var discount = 0;
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
                                        if(order.get_orderlines().at(i).product.id == _product.id){
                                            exist_in_orderline = order.get_orderlines().at(i);
                                            let orderline = order.get_orderlines().at(i);
                                            exist_in_orderline = orderline;
                                            is_pos_groupable = exist_in_orderline.get_unit().is_pos_groupable;
                                        }
                                    }
                                }

                                if(!is_pos_groupable){
                                    exist_in_orderline = false
                                }

                                if(!exist_in_orderline){
                                    order.add_product(_product, {
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
                            }
                        }
                    }
                }
                return Promise.resolve(is_cross_selling);
            }

            async _barcodeProductAction(code) {
                var product = this.env.pos.db.get_product_by_barcode(code.base_code)
                if(product && product.cross_selling){
                    await this.suggestItemsCrossSelling(product);
                }
                if (!product) {
                    const model = this.env.pos.get_model('product.product');
                    const domain = ['|', ['barcode', '=', code.base_code], ['default_code', '=', code.base_code]]
                    const context = this.env.session.user_context
                    const products = await this.env.pos.getDatasByModelInShadow(model['model'], domain, model.fields, context)
                    if (products.length != 0) {
                        this.env.pos.indexed_db.write('product.product', products);
                        this.env.pos.save_results('product.product', products);
                    }
                }
                var check_product_again = this.env.pos.db.get_product_by_barcode(code.base_code)
                if(check_product_again){
                    return await super._barcodeProductAction(code)
                }
                else{
                    var weight_scale_barcode = this._weight_scale_barcode(code.base_code)
                    var product_multi_barcode = false
                    if(!weight_scale_barcode){
                        product_multi_barcode = this._product_multi_barcode_(code.base_code)
                    }
                    if(!product_multi_barcode && !weight_scale_barcode){
                        this.showPopup('ErrorBarcodePopup', { code: code.base_code });
                    }
                }

            }

            async editCustomer(client) {
                this.partnerIntFields = ['title', 'country_id', 'state_id', 'property_product_pricelist', 'id']
                let {confirmed, payload: results} = await this.showPopup('PopUpCreateCustomer', {
                    title: this.env._t('Update Informaton of ') + client.name,
                    partner: client
                })
                if (confirmed) {
                    if (results.error) {
                        return this.showPopup('ErrorPopup', {
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
                        partnerValue['property_product_pricelist'] = null
                    }
                    if (results.country_id) {
                        partnerValue['country_id'] = results.country_id
                    }
                    let valueWillSave = {}
                    for (let [key, value] of Object.entries(partnerValue)) {
                        if (this.partnerIntFields.includes(key)) {
                            valueWillSave[key] = parseInt(value) || false;
                        } else {
                            if ((key == 'birthday_date' && value != client.birthday_date) || key != 'birthday_date') {
                                valueWillSave[key] = value;
                            }
                        }
                    }
                    await this.rpc({
                        model: 'res.partner',
                        method: 'write',
                        args: [[client.id], valueWillSave],
                        context: {}
                    })
                    const self = this
                    const clientID = client.id
                    setTimeout(() => {
                        let client = self.env.pos.db.get_partner_by_id(clientID);
                        if (client) {
                            self.env.pos.get_order().set_client(client)
                        }
                    }, 1000)

                }
            }

            get isLongName() {
                let selectedOrder = this.env.pos.get_order()
                if (selectedOrder && selectedOrder.get_client()) {
                    return selectedOrder.get_client() && selectedOrder.get_client().name.length > 10;
                } else {
                    return false
                }
            }

            async addCustomSale() {
                let {confirmed, payload: productName} = await this.showPopup('TextAreaPopup', {
                    title: this.env._t('What a Custom Sale (Product Name)'),
                    startingValue: ''
                })
                if (confirmed) {
                    let product = this.env.pos.db.get_product_by_id(this.env.pos.config.custom_sale_product_id[0]);
                    if (product) {
                        let {confirmed, payload: number} = await Gui.showPopup('NumberPopup', {
                            'title': this.env._t('What Price of ') + productName,
                            'startingValue': 0,
                        });
                        if (confirmed) {
                            const selectedOrder = this.env.pos.get_order()
                            product.display_name = productName
                            selectedOrder.add_product(product, {
                                //price_extra: 0,
                                price: parseFloat(number),
                                quantity: 1,
                                merge: false,
                            })
                            let selectedLine = selectedOrder.get_selected_orderline()
                            selectedLine.set_full_product_name(productName)
                            this.showPopup('ConfirmPopup', {
                                title: productName + this.env._t(' add to Cart'),
                                body: this.env._t('You can modifiers Price and Quantity of Item'),
                                disableCancelButton: true,
                            })
                        }

                    } else {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env.pos.config.custom_sale_product_id[1] + this.env._t(' not Available In POS'),
                        })
                    }
                }
            }

            get payButtonClasses() {
                let _currentOrder = this.env.pos.get_order();
                if (!_currentOrder) return {};
                var $button = $('button.order-total-btn').find('span.custom_apply_promotion');
                if ($button.length) {
                    $('button.order-total-btn').find('font').removeClass('oe_hidden');
                    $('button.order-total-btn').find('.pos_order_total').removeClass('oe_hidden');
                    $button.remove();
                }
                let hidden = false
                let warning = false
                let highlight = false
                let auto_promo = false
                if(this.env.pos.selected_order_method != 'employee-meal'){
                    if (this.env.pos.config.promotion_auto_add && !this.env.pos.apply_promotion_succeed) {
                        auto_promo = true
                    }
                }
                if (!this.env.pos.config.allow_payment || this.state.screen != 'Products' || this.env.isMobile) {
                    hidden = true
                }
                if (_currentOrder.is_return || _currentOrder.get_total_with_tax() < 0) {
                    warning = true
                } else {
                    highlight = true
                }
                return {
                    oe_hidden: hidden,
                    auto_promo: auto_promo,
                    warning: warning
                };
            }


            async _barcodeErrorAction(code) {
                const codeScan = code.code
                this.env.pos.alert_message({
                    title: this.env._t('Found Code'),
                    body: code.code
                })
                if (!code.scanDirectCamera) {
                    super._barcodeErrorAction(code)
                }
                let resultScanPricelist = await this._scanPricelistCode(codeScan)
                if (resultScanPricelist) {
                    this.trigger('close-popup')
                    return true
                }
                let resultScanLot = await this._barcodeLotAction(codeScan)
                if (resultScanLot) {
                    this.trigger('close-popup')
                    return true
                }
                let resultScanCustomer = await this._barcodeClientAction(codeScan)
                if (resultScanCustomer) {
                    this.trigger('close-popup')
                    return true
                }
                let modelScan = await this.env.pos.scan_product(code)
                if (!modelScan) {
                    const appliedCoupon = await this.env.pos.getInformationCouponPromotionOfCode(codeScan);
                    if (!appliedCoupon && !code.scanDirectCamera) {
                        super._barcodeErrorAction(code)
                    } else {
                        this.trigger('close-popup')
                    }
                }
                else {
                    this.trigger('close-popup')
                }
            }

            _barcodeClientAction(code) {
                var ScanCode = code;
                if (typeof(code) === 'object') {
                    var ScanCode = code.code;
                }
                const partner = this.env.pos.db.get_partner_by_barcode(ScanCode);
                if (partner) {
                    if (this.currentOrder.get_client() !== partner) {
                        this.currentOrder.set_client(partner);
                        this.currentOrder.set_pricelist(
                            _.findWhere(this.env.pos.pricelists, {
                                id: partner.property_product_pricelist[0],
                            }) || this.env.pos.default_pricelist
                        );
                    }
                    return true;
                }
                return false;
            }

            async _scanPricelistCode(code) {
                let pricelist = this.env.pos.pricelists.find(p => p.barcode == code)
                if (pricelist) {
                    const selectedOrder = this.env.pos.get_order()
                    selectedOrder.set_pricelist(pricelist)
                    this.env.pos.alert_message({
                        title: this.env._t('Successfully'),
                        body: pricelist.name + this.env._t(' set to Order')
                    })
                    return true
                }
                return false
            }

            async _barcodeLotAction(code) {
                const self = this
                const selectedOrder = this.env.pos.get_order();
                let lots = this.env.pos.lots.filter(l => l.barcode == code || l.name == code)
                if (lots && lots.length) {
                    lots = _.filter(lots, function (lot) {
                        let product_id = lot.product_id[0];
                        let product = self.env.pos.db.product_by_id[product_id];
                        return product != undefined
                    });
                }
                if (lots && lots.length) {
                    if (lots.length > 1) {
                        const list = lots.map(l => ({
                            label: this.env._t('Lot Name: ') + l.name + this.env._t(' with quantity ') + l.product_qty,
                            item: l,
                            id: l.id
                        }))
                        let {confirmed, payload: lot} = await this.showPopup('SelectionPopup', {
                            title: this.env._t('Select Lot Serial'),
                            list: list,
                        });
                        if (confirmed) {
                            let productOfLot = this.env.pos.db.product_by_id[lot.product_id[0]]
                            selectedOrder.add_product(productOfLot, {merge: false})
                            let order_line = selectedOrder.get_selected_orderline()
                            if (order_line) {
                                if (lot.replace_product_public_price && lot.public_price) {
                                    order_line.set_unit_price(lot['public_price'])
                                    order_line.price_manually_set = true
                                }
                                const modifiedPackLotLines = {}
                                const newPackLotLines = [{
                                    lot_name: lot.name
                                }]
                                order_line.setPackLotLines({modifiedPackLotLines, newPackLotLines});
                                return true
                            } else {
                                return false
                            }
                        } else {
                            return false
                        }
                    } else {
                        const selectedLot = lots[0]
                        let productOfLot = this.env.pos.db.product_by_id[selectedLot.product_id[0]]
                        const newPackLotLines = lots
                            .filter(item => item.id)
                            .map(item => ({lot_name: item.name}))
                        const modifiedPackLotLines = lots
                            .filter(item => !item.id)
                            .map(item => ({lot_name: item.text}))
                        this.env.pos.alert_message({
                            title: this.env._t('Barcode of Lot/Serial'),
                            body: this.env._t('For Product: ') + productOfLot.display_name
                        })
                        const draftPackLotLines = {modifiedPackLotLines, newPackLotLines}
                        selectedOrder.add_product(productOfLot, {
                            draftPackLotLines,
                            price_extra: 0,
                            quantity: 1,
                            merge: false,
                        })
                        return true
                    }
                } else {
                    return false
                }
            }

            _openCart() {
                this.state.openCart = !this.state.openCart
            }

            get getMaxWidthLeftScreen() {
                if (this.env.isMobile) {
                    return 'unset !important'
                } else {
                    return this.env.session.config.cart_width + '% !important'
                }
            }

            _closingOpenCashScreen() {
                this.state.cashControl = false
            }

            _openOpenCashScreen() {
                this.state.cashControl = true
                // this.render()
            }

            _onMouseEnter(event) {
                $(event.currentTarget).css({'width': '450px'})
            }

            _onMouseLeave(event) {
                $(event.currentTarget).css({'width': '150px'})
            }

            async _onRemoveSelectedOrder() {
                const selectedOrder = this.env.pos.get_order();
                const screen = selectedOrder.get_screen_data();
                var currency = false
                if(selectedOrder){
                    currency = selectedOrder.currency
                }
                if (['ProductScreen', 'PaymentScreen'].includes(screen.name) && selectedOrder.get_orderlines().length > 0) {
                    const {confirmed} = await this.showPopup('ErrorPopup', {
                        title: 'Existing orderlines',
                        body: `${selectedOrder.name} has total amount of ${this.env.pos.format_currency(selectedOrder.get_total_with_tax(),false,currency)}, are you sure you want delete this order?`,
                    });
                    if (!confirmed) return;
                }
                if (selectedOrder) {
                    if (this.env.pos.config.validate_remove_order) {
                        let validate = await this.env.pos._validate_action(this.env._t('Delete this Order'));
                        if (!validate) {
                            return false;
                        }
                    }
                    selectedOrder.destroy({reason: 'abandon'});
                    this.showScreen('TicketScreen');
                    posbus.trigger('order-deleted');
                    this.env.pos.saveOrderRemoved(selectedOrder)
                }
            }

            async _onRemoveSelectedClient() {
                const selectedOrder = this.env.pos.get_order();
                if (selectedOrder) {
                    const lastClientSelected = selectedOrder.get_client()
                    selectedOrder.set_client(null);
                    if(selectedOrder){
                        selectedOrder.is_home_delivery = false
                    }
                    if (!lastClientSelected) {
                        this.env.pos.chrome.showNotification(this.env._t('Alert'), this.env._t('Order blank Customer'))
                        return true
                    }
                    this.env.pos.chrome.showNotification(lastClientSelected['name'], this.env._t(' Deselected, out of Order'))
                }
            }

            get blockScreen() {
                const selectedOrder = this.env.pos.get_order();
                if (!selectedOrder || !selectedOrder.is_return) {
                    return false
                } else {
                    return true
                }
            }

            get allowDisplayListFeaturesButton() {
                if (this.state.screen == 'Products') {
                    return true
                } else {
                    return false
                }
            }

            get blockScreen() {
                const selectedOrder = this.env.pos.get_order();
                if (!selectedOrder || !selectedOrder.is_return) {
                    return false
                } else {
                    return true
                }
            }

            _backScreen() {
                if (this.env.pos.lastScreen && this.env.pos.lastScreen == 'Payment') {
                    this.state.screen = this.env.pos.lastScreen
                } else {
                    this.state.screen = 'Products'
                }
                this.env.pos.config.sync_multi_session = true
            }

            _resetScreen() {
                const self = this
                this.state.screen = 'Products'
                this.env.pos.config.sync_multi_session = true
            }

            backToCart() {
                posbus.trigger('set-screen', 'Products')
                this.env.pos.config.sync_multi_session = true
            }

            _setScreen(screenName) {
                const self = this
                this.state.screen = screenName
                this.env.pos.lastScreen = screenName
            }


            async _updateSelectedOrderline(event) {
                const orderline = this.env.pos.get_order().get_selected_orderline()
                if (event.detail.buffer != null && event.detail.key == "Backspace" && this.env.pos.config.allow_remove_line && orderline) { 
                    return true
                }
                
                
                if (this.env.pos.lockedUpdateOrderLines) {
                    return true
                } else {
                    var need_validation = false
                    if(orderline && this.state.numpadMode === 'quantity' && this.env.pos.config.validate_quantity_change && this.env.pos.config.validate_by_manager){
                        let currentQuantity = orderline.get_quantity();
                        const parsedInput = parseFloat(event.detail.buffer) || 0
                        var newQty = parsedInput
                        if (this.env.pos.config.validate_quantity_change_type == 'increase' && parsedInput > currentQuantity){
                            need_validation = true
                            var text_validation = this.env._t(' Need approved set new Quantity: ') + parseFloat(newQty)
                            var body_validation = this.env._t('You have permission set Quantity, required request your Manager approve it.')
                        }
                        else if (this.env.pos.config.validate_quantity_change_type == 'decrease' && parsedInput < currentQuantity){
                            need_validation = true
                            var text_validation = this.env._t(' Need approved set new Quantity: ') + parseFloat(newQty)
                            var body_validation = this.env._t('You have permission set Quantity, required request your Manager approve it.')
                        }
                        else if (this.env.pos.config.validate_quantity_change_type == 'both'){
                            need_validation = true
                            var text_validation = this.env._t(' Need approved set new Quantity: ') + parseFloat(newQty)
                            var body_validation = this.env._t('You have permission set Quantity, required request your Manager approve it.')
                        }

                    }

                    if(orderline && this.state.numpadMode === 'price' && this.env.pos.config.validate_price_change && this.env.pos.config.validate_by_manager){
                        let currentPrice = orderline.price;
                        const parsedInput = parseFloat(event.detail.buffer) || 0
                        var newPrice = parsedInput
                        if (this.env.pos.config.validate_price_change_type == 'increase' && parsedInput > currentPrice){
                            need_validation = true
                            var text_validation = this.env._t(' Need approved set new Price: ') + parseFloat(newPrice)
                            var body_validation = this.env._t('You have permission set Price, required request your Manager approve it.')
                        }
                        else if (this.env.pos.config.validate_price_change_type == 'decrease' && parsedInput < currentPrice){
                            need_validation = true
                            var text_validation = this.env._t(' Need approved set new Price: ') + parseFloat(newPrice)
                            var body_validation = this.env._t('You have permission set Price, required request your Manager approve it.')
                        }
                        else if (this.env.pos.config.validate_price_change_type == 'both'){
                            need_validation = true
                            var text_validation = this.env._t(' Need approved set new Price: ') + parseFloat(newPrice)
                            var body_validation = this.env._t('You have permission set Price, required request your Manager approve it.')
                        }

                    }


                    if(orderline && this.state.numpadMode === 'discount' && this.env.pos.config.validate_discount_change && this.env.pos.config.validate_by_manager){
                        let currentDiscount = orderline.discount;
                        const parsedInput = parseFloat(event.detail.buffer) || 0
                        var newDiscount = parsedInput
                        if (this.env.pos.config.validate_discount_change_type == 'increase' && parsedInput > currentDiscount){
                            need_validation = true
                            var text_validation = this.env._t(' Need approved set new Discount: ') + parseFloat(newDiscount)
                            var body_validation = this.env._t('You have permission set Discount, required request your Manager approve it.')
                        }
                        else if (this.env.pos.config.validate_discount_change_type == 'decrease' && parsedInput < currentDiscount){
                            need_validation = true
                            var text_validation = this.env._t(' Need approved set new Discount: ') + parseFloat(newDiscount)
                            var body_validation = this.env._t('You have permission set Discount, required request your Manager approve it.')
                        }
                        else if (this.env.pos.config.validate_discount_change_type == 'both'){
                            need_validation = true
                            var text_validation = this.env._t(' Need approved set new Discount: ') + parseFloat(newDiscount)
                            var body_validation = this.env._t('You have permission set Discount, required request your Manager approve it.')
                        }

                    }

                    if(!need_validation && this.env.pos.config.validate_change_minus && this.env.pos.config.validate_by_manager && event.detail.key == '-'){
                        need_validation = true
                        var text_validation = this.env._t(' Need approved set +/-') 
                        var body_validation = this.env._t('You have permission set +/-, required request your Manager approve it.')
                    }

                    if(need_validation){
                        var validate = await this.env.pos._validate_action(text_validation);
                        if (!validate) {
                            return this.env.pos.alert_message({
                                title: this.env._t('Error'),
                                body: body_validation
                            });
                        }
                    }
                    return super._updateSelectedOrderline(event)

                }
            }

            addEventKeyboad() {
                $(document).off('keydown.productscreen', this._onKeypadKeyDown);
                $(document).on('keydown.productscreen', this._onKeypadKeyDown);
            }

            removeEventKeyboad() {
                $(document).off('keydown.productscreen', this._onKeypadKeyDown);
            }

            _onKeypadKeyDown(ev) {
                if (this.state.screen != 'Products') {
                    return true
                }
                if (!_.contains(["INPUT", "TEXTAREA"], $(ev.target).prop('tagName')) && ev.keyCode !== 13) {
                    clearTimeout(this.timeout);
                    this.buffered_key_events.push(ev);
                    this.timeout = setTimeout(_.bind(this._keyboardHandler, this), BarcodeEvents.max_time_between_keys_in_ms);
                }
                if (ev.keyCode == 27) {  // esc key (clear search)
                    clearTimeout(this.timeout);
                    this.buffered_key_events.push(ev);
                    this.timeout = setTimeout(_.bind(this._keyboardHandler, this), BarcodeEvents.max_time_between_keys_in_ms);
                }
            }


            // _setValue(val) {
            //     if (this.currentOrder.finalized || this.state.screen != 'Products') {
            //         console.warn('[Screen products state is not Products] or [Order is finalized] reject trigger event keyboard]')
            //         return false
            //     } else {
            //         super._setValue(val)
            //     }
            // }

           /**
            * @override
            */
            _setValue(val) {
                if (this.currentOrder.finalized || this.state.screen != 'Products') {
                    console.warn('[Screen products state is not Products] or [Order is finalized] reject trigger event keyboard]')
                    return false;
                }

                if (this.currentOrder.get_selected_orderline()) {
                    if (this.state.numpadMode === 'quantity') {
                        this.currentOrder.get_selected_orderline().set_quantity(val);
                    } else if (this.state.numpadMode === 'discount') {
                        // this.currentOrder.get_selected_orderline().set_discount(val);
                        this.currentOrder.get_selected_orderline().set_discount_from_numpad(val);
                    } else if (this.state.numpadMode === 'price') {
                        var selected_orderline = this.currentOrder.get_selected_orderline();
                        selected_orderline.price_manually_set = true;
                        selected_orderline.set_unit_price(val);
                    }
                    if (this.env.pos.config.iface_customer_facing_display) {
                        this.env.pos.send_current_order_to_customer_facing_display();
                    }
                }
            }


            async _keyboardHandler() {
                let self = this;
                const selectedOrder = this.env.pos.get_order()
                const selectedLine = selectedOrder.get_selected_orderline()

                if (this.env.pos.lockedUpdateOrderLines) {
                    this.buffered_key_events = [];
                    return true;
                }
                if (this.buffered_key_events.length > 2) {
                    this.buffered_key_events = [];
                    return true;
                }
                if(this.env.pos.config.select_shortcut && this.buffered_key_events.length==1){
                    var all_shortcuts = this.env.pos.db.shortcuts_by_id[this.env.pos.config.select_shortcut[0]];
                    for (let i = 0; i < this.buffered_key_events.length; i++) {
                        var array_list_btn_shortcut = []

                        array_list_btn_shortcut.push(all_shortcuts.customer_screen.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.next_screen.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.search_product.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.select_qty.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.select_discount.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.select_price.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.create_customer.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.back_screen.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.select_user.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.refresh.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.see_all_order.toUpperCase())
                        array_list_btn_shortcut.push(all_shortcuts.close_pos.toUpperCase())
                        var event_key = this.buffered_key_events[i].key.toUpperCase()
                        if(array_list_btn_shortcut.includes(event_key)){
                            return true;
                        }
                        
                    }
                }
                for (let i = 0; i < this.buffered_key_events.length; i++) {
                    let event = this.buffered_key_events[i]

                    // -------------------------- product screen -------------
                    let ctrlKey = event.ctrlKey;
                    let key = '';
                    let keyAccept = false;
                    if (event.keyCode == 8 && this.env.pos.config.allow_remove_line && selectedLine) { // Del

                        if (this.env.pos.config.validate_remove_line && this.env.pos.config.validate_by_manager) {
                            let validate = await this.env.pos._validate_action(this.env.pos.env._t('Remove Line'));
                            if (!validate) {
                                return false;
                            }
                        }
                        selectedOrder.remove_orderline(selectedLine);
                        keyAccept = true
                    }
                    // if (event.keyCode == 17 && selectedLine) { // ctrl
                    //     let uom_items = this.env.pos.uoms_prices_by_product_tmpl_id[selectedLine.product.product_tmpl_id];
                    //     if (uom_items) {
                    //         let list = uom_items.map((u) => ({
                    //             id: u.id,
                    //             label: u.uom_id[1],
                    //             item: u
                    //         }));
                    //         let {confirmed, payload: unit} = await this.showPopup('SelectionPopup', {
                    //             title: this.env._t('Select Unit of Measure for : ') + selectedLine.product.display_name,
                    //             list: list
                    //         })
                    //         if (confirmed) {
                    //             selectedLine.change_unit(unit);
                    //         }
                    //     }
                    //     keyAccept = true
                    // }
                    // if (event.keyCode == 27) { // esc , no need this code, SearchBar onKeyup() handle it
                    //     keyAccept = true
                    // }
                    if (event.keyCode == 77) { // M
                        keyAccept = true
                    }
                    if (event.keyCode == 17) { // CTRL
                        keyAccept = true
                    }
                    if (event.keyCode == 85) { // U
                        keyAccept = true
                    }
                    if (event.keyCode == 79) { // o
                        keyAccept = true
                    }
                    if (event.keyCode == 39) { // Arrow right
                        $(this.el).find('.pay').click()
                        keyAccept = true
                    }
                    if (event.keyCode == 38 || event.keyCode == 40) { // arrow up and down
                        if (selectedLine) {
                            for (let i = 0; i < selectedOrder.orderlines.models.length; i++) {
                                let line = selectedOrder.orderlines.models[i]
                                if (line.cid == selectedLine.cid) {
                                    let line_number = null;
                                    if (event.keyCode == 38) { // up
                                        if (i == 0) {
                                            line_number = selectedOrder.orderlines.models.length - 1
                                        } else {
                                            line_number = i - 1
                                        }
                                    } else { // down
                                        if (i + 1 >= selectedOrder.orderlines.models.length) {
                                            line_number = 0
                                        } else {
                                            line_number = i + 1
                                        }
                                    }
                                    selectedOrder.select_orderline(selectedOrder.orderlines.models[line_number])
                                }
                            }
                        }
                        keyAccept = true
                    }
                    // if (event.keyCode == 65) { // a : search client
                    //     $('.search-customer >input').focus()
                    //     keyAccept = true
                    // }
                    if (event.keyCode == 65) { // a
                        keyAccept = true
                    }
                    if (event.keyCode == 67) { // c
                        $(this.el).find('.set-customer').click()
                        keyAccept = true
                    }
                    if (event.keyCode == 78) { // n
                        keyAccept = true
                    }
                    if (event.keyCode == 68) { // d
                        this.trigger('set-numpad-mode', {mode: 'discount'});
                        keyAccept = true
                    }
                    if (event.keyCode == 72) { // h
                        $(this.el).find('.clear-icon').click()
                        keyAccept = true
                    }
                    if (event.keyCode == 76) { // l (logout)
                        $('.lock-button').click()
                        keyAccept = true
                    }
                    if (event.keyCode == 80) { // p
                        this.trigger('set-numpad-mode', {mode: 'price'});
                        keyAccept = true
                    }
                    if (event.keyCode == 81) { // q
                        this.trigger('set-numpad-mode', {mode: 'quantity'});
                        keyAccept = true
                    }
                    if (event.keyCode == 83) { // s : search product
                        $('.search >input')[0].focus()
                        keyAccept = true
                    }


                    if (event.keyCode == 187 && selectedLine && ctrlKey == false) { // +
                        selectedLine.set_quantity(selectedLine.quantity + 1)
                        keyAccept = true
                    }
                    if (event.keyCode == 189 && selectedLine && ctrlKey == false) { // -
                        let newQty = selectedLine.quantity - 1
                        setTimeout(function () {
                            selectedLine.set_quantity(newQty)
                        }, 200) // odoo core set to 0, i waiting 1/5 second set back -1
                        keyAccept = true
                    }
                    if (event.keyCode == 189 && selectedLine && ctrlKey == true) { 
                        // Prevent decrease qty when press CTRL + Minus (-)
                        self.env.pos.lockedUpdateOrderLines = true;
                        clearTimeout(lockedUpdateOrderLinesTimeout);
                        lockedUpdateOrderLinesTimeout = setTimeout(function () {

                            self.env.pos.lockedUpdateOrderLines = false; // timeout 0.5 seconds to unlock event keyboard
                        }, 500)
                    }


                    if (event.keyCode == 112) { // F1
                        $(this.el).find('.o_pricelist_button').click()
                        keyAccept = true
                    }
                    if (event.keyCode == 113) { // F2
                        $('.invoice-button').click()
                        keyAccept = true
                    }
                    if (event.keyCode == 114) { // F3: to invoice
                        keyAccept = true
                        $('.clear-items-button').click()
                    }
                    if (event.keyCode == 115) { // F4 : return mode
                        keyAccept = true
                        $('.return-mode-button').click()
                    }
                    if (event.keyCode == 117 || event.keyCode == 82) { // F6 or R: receipt
                        keyAccept = true
                        $('.print-receipt-button').click()
                    }
                    if (event.keyCode == 118) { // F7: set note
                        keyAccept = true
                        $('.set-note-button').click()
                    }
                    if (event.keyCode == 119) { // F8: set note
                        keyAccept = true
                        $('.set-service-button').click()
                    }
                    // if (event.keyCode == 120) { // F9
                    //     keyAccept = true
                    //     $('.orders-header-button').click()
                    // }
                    // if (event.keyCode == 121) { // F10
                    //     keyAccept = true
                    //     $('.sale-orders-header-button').click()
                    // }
                    // if (event.keyCode == 122) { // F11
                    //     keyAccept = true
                    //     $('.pos-orders-header-button').click()
                    // }
                    // if (event.keyCode == 123) { // F12
                    //     keyAccept = true
                    //     $('.invoices-header-button').click()
                    // }

                    if (!keyAccept && !["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "l", ".", "+", "-", "-", "=", "F1", "F2", "F3", "F4", "F6", "F7", "F8", "F9", "F10", "F11", "F12", " "].includes(event.key)) {
                        $('.search >input').focus()
                        if (event.key.length == 1) {
                            $('.search >input').val(event.key)
                        }
                    }
                }
                this.buffered_key_events = [];
            }

            async _validateMode(mode) {
                if (mode == 'discount' && (!this.env.pos.config.allow_numpad || !this.env.pos.config.allow_discount || !this.env.pos.config.manual_discount)) {
                    this.env.pos.alert_message({
                        title: this.env._t('Alert'),
                        body: this.env._t('You have not Permission change Discount')
                    })
                    return false;
                }
                if (mode == 'quantity' && (!this.env.pos.config.allow_numpad || !this.env.pos.config.allow_qty)) {
                    this.env.pos.alert_message({
                        title: this.env._t('Alert'),
                        body: this.env._t('You have not Permission change Quantity')
                    })
                    return false;
                }
                if (mode == 'price' && (!this.env.pos.config.allow_numpad || !this.env.pos.config.allow_price)) {
                    this.env.pos.alert_message({
                        title: this.env._t('Alert'),
                        body: this.env._t('You have not Permission change Quantity')
                    })
                    return false;
                }

                return true
            }

            async _setNumpadMode(event) {
                const {mode} = event.detail;
                const validate = await this._validateMode(mode)
                if (validate) {
                    posbus.trigger('set-numpad-mode', event)
                    return await super._setNumpadMode(event)
                } else {
                    posbus.trigger('set-numpad-mode', {
                        detail: {
                            mode: 'quantity'
                        }
                    })
                }
            }

            async autoAskPaymentMethod() {
                const selectedOrder = this.env.pos.get_order();
                var currency = false
                if(selectedOrder){
                    currency = selectedOrder.currency
                }
                if (selectedOrder.is_return) {
                    return this.showScreen('PaymentScreen')
                }
                if (selectedOrder.is_to_invoice() && !selectedOrder.get_client()) {
                    this.showPopup('ConfirmPopup', {
                        title: this.env._t('Warning'),
                        body: this.env._t('Order will process to Invoice, please select one Customer for set to current Order'),
                        disableCancelButton: true,
                    })
                    const {confirmed, payload: newClient} = await this.showTempScreen(
                        'ClientListScreen',
                        {client: null}
                    );
                    if (confirmed) {
                        selectedOrder.set_client(newClient);
                    } else {
                        return this.autoAskPaymentMethod()
                    }
                }
                if (selectedOrder && (selectedOrder.paymentlines.length == 0 || (selectedOrder.paymentlines.length == 1 && selectedOrder.paymentlines.models[0].payment_method.pos_method_type == 'rounding'))) {
                    const paymentMethods = this.env.pos.normal_payment_methods.map(m => {
                        if (m.journal && m.journal.currency_id) {
                            return {
                                id: m.id,
                                item: m,
                                name: m.name + ' (' + m.journal.currency_id[1] + ' ) '
                            }
                        } else {
                            return {
                                id: m.id,
                                item: m,
                                name: m.name
                            }
                        }
                    })
                    let {confirmed, payload: selectedItems} = await this.showPopup(
                        'PopUpSelectionBox',
                        {
                            title: this.env._t('Select the Payment Method. If you need add Multi Payment Lines, please click [Close] button for go to Payment Screen to do it.'),
                            items: paymentMethods,
                            onlySelectOne: true,
                            buttonMaxSize: true
                        }
                    );
                    if (confirmed) {
                        const paymentMethodSelected = selectedItems.items[0]
                        if (!paymentMethodSelected) {
                            this.env.pos.alert_message({
                                title: this.env._t('Error'),
                                body: this.env._t('Please select one Payment Method')
                            })
                            return this.autoAskPaymentMethod()
                        }
                        selectedOrder.add_paymentline(paymentMethodSelected);
                        const paymentline = selectedOrder.selected_paymentline;
                        paymentline.set_amount(0)
                        let {confirmed, payload: amount} = await this.showPopup('NumberPopup', {
                            title: this.env._t('How much Amount customer give ? Amount Total with taxes of Order is: ') + this.env.pos.format_currency(selectedOrder.get_total_with_tax(),false,currency),
                            body: this.env._t('Full fill due Amount, you can click to Button Validate Order for finish Order and get a Receipt !'),
                            activeFullFill: true,
                            confirmFullFillButtonText: this.env._t('Full Fill Amount: ') + this.env.pos.format_currency(selectedOrder.get_due(),false,currency),
                            fullFillAmount: selectedOrder.get_due()
                        })
                        if (confirmed) {
                            paymentline.set_amount(amount);
                            if (selectedOrder.get_due() <= 0) {
                                let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                                    title: this.env._t('Refund Amount of Order : ') + this.env.pos.format_currency(-selectedOrder.get_due(),false,currency),
                                    body: this.env._t('Click Submit button for finish the Order and print Receipt ? (Shortcut key: [Enter])'),
                                    cancelText: this.env._t('No. Close Popup'),
                                    confirmText: this.env._t('Submit')
                                })
                                if (confirmed) {
                                    this.showScreen('PaymentScreen', {
                                        autoValidateOrder: true,
                                        isShown: false,
                                    })
                                } else {
                                    this.showScreen('PaymentScreen')
                                }
                            } else {
                                this.showScreen('PaymentScreen')
                                return this.env.pos.alert_message({
                                    title: this.env._t('Warning'),
                                    body: this.env._t('Order not full fill Amount Total need to paid, Remaining Amount: ') + this.env.pos.format_currency(selectedOrder.get_due(),false,currency)
                                })
                            }
                        } else {
                            this.showScreen('PaymentScreen')
                        }
                    } else {
                        this.showScreen('PaymentScreen')
                    }
                } else {
                    this.showScreen('PaymentScreen')
                }
            }

            async _onClickPay() {
                let selectedOrder = this.env.pos.get_order();
                var currency = false
                if(selectedOrder){
                    currency = selectedOrder.currency
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
                            + this.env.pos.format_currency(selectedOrder.employeemeal_budget,false,currency) +')';
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
                    const linesAppliedPromotion = selectedOrder.orderlines.models.find(l => l.promotion)
                    if (!linesAppliedPromotion && this.env.pos.config.promotion_ids && this.env.pos.config.promotion_auto_add) {
                        selectedOrder.remove_all_promotion_line();
                        selectedOrder.apply_promotion();
                    }
                    if (linesAppliedPromotion) {
                        let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                            title: this.env._t("Your Order Applied Promotions"),
                            body: this.env._t("Are you wanted remove it and Applied All Promotions Active ?"),
                        })
                        if (confirmed) {
                            selectedOrder.remove_all_promotion_line();
                            selectedOrder.apply_promotion();
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
                            body: this.env._t('Total Amount of Order is : ') + this.env.pos.format_currency(0,false,currency)
                        })
                    }
                    if (!this.env.pos.config.allow_order_out_of_stock) {
                        const quantitiesByProduct = selectedOrder.product_quantity_by_product_id()
                        let isValidStockAllLines = true;
                        for (let n = 0; n < selectedOrder.orderlines.models.length; n++) {
                            let l = selectedOrder.orderlines.models[n];
                            let currentStockInCart = quantitiesByProduct[l.product.id]
                            if (l.product.type == 'product' && l.product.get_qty_available() < currentStockInCart) {
                                isValidStockAllLines = false
                                this.env.pos.alert_message({
                                    title: this.env._t('Error'),
                                    body: l.product.display_name + this.env._t(' not enough for sale. Current stock on hand only have: ') + l.product.get_qty_available() + this.env._t(' . Your cart add ') + currentStockInCart + this.env._t(' (items). Bigger than stock on hand have of Product !!!'),
                                    timer: 10000
                                })
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
                posbus.trigger('set-screen', 'Payment') // single screen
                // if (this.env.isMobile) {
                //     this.autoAskPaymentMethod()
                // } else {
                //
                // }
                //super._onClickPay() // this.showScreen('PaymentScreen');
            }


            async _onClickCustomer() { // single screen
                this.env.pos.syncProductsPartners()
                if (this.env.isMobile) {
                    super._onClickCustomer()
                } else {
                    posbus.trigger('set-screen', 'Clients') // single screen
                    setTimeout(function () {
                        $('.searchbox-client >input').focus()
                    }, 200)
                }
            }

            async updateStockEachLocation(product) {
                if (product.tracking == 'serial') {
                    return this.env.pos.alert_message({
                        title: this.env._t('Warning'),
                        body: product.display_name + this.env._t(' tracking By Unique Serial, not allow you re-update stock quantities')
                    })
                } else {
                    let stock_location_ids = this.env.pos.get_all_source_locations();
                    let stock_datas = await this.env.pos._get_stock_on_hand_by_location_ids([product.id], stock_location_ids).then(function (datas) {
                        return datas
                    });
                    if (stock_datas) {
                        let items = [];
                        let withLot = false
                        if (product.tracking == 'lot') {
                            withLot = true
                        }
                        if (!withLot) {
                            for (let location_id in stock_datas) {
                                let location = this.env.pos.stock_location_by_id[location_id];
                                if (location) {
                                    items.push({
                                        id: location.id,
                                        item: location,
                                        location_id: location.id,
                                        quantity: stock_datas[location_id][product.id]
                                    })
                                }
                            }
                        } else {
                            let stockQuants = await this.rpc({
                                model: 'stock.quant',
                                method: 'search_read',
                                domain: [['product_id', '=', product.id], ['location_id', 'in', stock_location_ids]],
                                fields: [],
                                context: {
                                    limit: 1
                                }
                            })
                            if (stockQuants) {
                                items = stockQuants.map((q) => ({
                                    id: q.id,
                                    item: q,
                                    lot_id: q.lot_id[0],
                                    lot_name: q.lot_id[1],
                                    location_id: q.location_id[0],
                                    location_name: q.location_id[1],
                                    quantity: q.quantity
                                }));
                            }
                        }
                        if (items.length) {
                            let {confirmed, payload: result} = await this.showPopup('UpdateStockOnHand', {
                                title: this.env._t('Summary Stock on Hand (Available - Reserved) each Stock Location of [ ') + product.display_name + ' ]',
                                withLot: withLot,
                                array: items,
                            })
                            if (confirmed) {
                                const newStockArray = result.newArray

                                for (let i = 0; i < newStockArray.length; i++) {
                                    let newStock = newStockArray[i];
                                    if (!withLot) {
                                        await this.rpc({
                                            model: 'stock.location',
                                            method: 'pos_update_stock_on_hand_by_location_id',
                                            args: [newStock['location_id'], {
                                                product_id: product.id,
                                                product_tmpl_id: product.product_tmpl_id,
                                                quantity: parseFloat(newStock['quantity']),
                                                location_id: newStock['location_id']
                                            }],
                                            context: {}
                                        }, {
                                            shadow: true,
                                            timeout: 65000
                                        })
                                    } else {
                                        await this.rpc({
                                            model: 'stock.quant',
                                            method: 'write',
                                            args: [newStock['id'], {
                                                quantity: parseFloat(newStock['quantity']),
                                            }],
                                            context: {}
                                        }, {
                                            shadow: true,
                                            timeout: 65000
                                        })
                                    }
                                }
                                this.env.pos.trigger('reload.quantity.available')
                                this.env.pos.alert_message({
                                    title: product.display_name,
                                    body: this.env._t('Successfully update stock on hand'),
                                    color: 'success'
                                })
                                return this.updateStockEachLocation(product)
                            }
                        } else {
                            return this.env.pos.alert_message({
                                title: this.env._t('Warning'),
                                body: product.display_name + this.env._t(' not found stock on hand !!!')
                            })
                        }
                    }
                }
            }

            //Overide
            async _getAddProductOptions(product) {
                let price_extra = 0.0;
                let draftPackLotLines, weight, description, packLotLinesToEdit;

                if (this.env.pos.config.product_configurator && _.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
                    let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id])
                                      .filter((attr) => attr !== undefined);
                    let { confirmed, payload } = await this.showPopup('ProductConfiguratorPopup', {
                        product: product,
                        attributes: attributes,
                    });

                    if (confirmed) {
                        description = payload.selected_attributes.join(', ');
                        price_extra += payload.price_extra;
                    } else {
                        return;
                    }
                }

                // Disable Create lots
                // Gather lot information if required.
                /** 
                if (['serial', 'lot'].includes(product.tracking) && (this.env.pos.picking_type.use_create_lots || this.env.pos.picking_type.use_existing_lots)) {
                    const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
                    if (isAllowOnlyOneLot) {
                        packLotLinesToEdit = [];
                    } else {
                        const orderline = this.currentOrder
                            .get_orderlines()
                            .filter(line => !line.get_discount())
                            .find(line => line.product.id === product.id);
                        if (orderline) {
                            packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                        } else {
                            packLotLinesToEdit = [];
                        }
                    }
                    const { confirmed, payload } = await this.showPopup('EditListPopup', {
                        title: this.env._t('Lot/Serial Number(s) Required'),
                        isSingleItem: isAllowOnlyOneLot,
                        array: packLotLinesToEdit,
                    });
                    if (confirmed) {
                        // Segregate the old and new packlot lines
                        const modifiedPackLotLines = Object.fromEntries(
                            payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                        );
                        const newPackLotLines = payload.newArray
                            .filter(item => !item.id)
                            .map(item => ({ lot_name: item.text }));

                        draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
                    } else {
                        // We don't proceed on adding product.
                        return;
                    }
                }
                */

                // Take the weight if necessary.
                if (product.to_weight && this.env.pos.config.iface_electronic_scale) {
                    // Show the ScaleScreen to weigh the product.
                    if (this.isScaleAvailable) {
                        const { confirmed, payload } = await this.showTempScreen('ScaleScreen', {
                            product,
                        });
                        if (confirmed) {
                            weight = payload.weight;
                        } else {
                            // do not add the product;
                            return;
                        }
                    } else {
                        await this._onScaleNotAvailable();
                    }
                }

                return { draftPackLotLines, quantity: weight, description, price_extra };
            }

            get_product_object(product){
                let self = this;
                var tmp_product = product
                if (self.env.pos.config.show_product_template) {
                    var product = self.env.pos.db.get_product_template_by_id(product.id);
                    if(tmp_product.product_tmpl_id) {
                        var product = self.env.pos.db.get_product_template_by_id(tmp_product.product_tmpl_id);
                    }
                } else {
                    var product = self.env.pos.db.get_product_by_id(product.id);
                }
                return product;
            }

            async get_product_variant_object(product){
                console.warn('[get_product_variant_object] product:', product);
                let self = this;
                if (self.env.pos.config.show_product_template) {
                    if (product.product_variant_count > 1) {
                        var product_list = [];
                        product.product_variant_ids.forEach((variant_id) => {
                            var variant_obj = self.env.pos.db.get_product_by_id(variant_id);
                            product_list.push({
                                label: self.env._t(variant_obj.display_name),
                                item: variant_obj,
                                id: variant_obj.id,
                            });
                        });
                        let {confirmed, payload: variant_selected} = await self.showPopup('SelectionPopup', {
                            title: self.env._t('Select Variant'),
                            list: product_list,
                        });
                        if (confirmed) {
                            var product = variant_selected;
                        }
                        // Do not add product if cancel Select Variant.
                        if(!confirmed){
                            return;
                        }
                    } else {
                        if(product.product_variant_ids){
                            var product = self.env.pos.db.get_product_by_id(product.product_variant_ids[0]);
                        }
                    }
                }
                return product;
            }

            get_product_variants(product){
                let self = this;
                let variants = [];
                if (self.env.pos.config.show_product_template) {
                    if (product.product_variant_count > 1) {
                        product.product_variant_ids.forEach((variant_id) => {
                            var variant_obj = self.env.pos.db.get_product_by_id(variant_id);
                            variants.push({
                                label: self.env._t(variant_obj.display_name),
                                item: variant_obj,
                                id: variant_obj.id,
                            });
                        });
                    } else {
                        if(product.product_variant_ids){
                            var variant_obj = self.env.pos.db.get_product_by_id(product.product_variant_ids[0]);
                            variants.push({
                                label: self.env._t(variant_obj.display_name),
                                item: variant_obj,
                                id: variant_obj.id,
                            });
                        }
                    }
                }
                return variants;
            }

            continue_action(product){
                //if product conmbo or bom will return false
                return true;
            }

            async _clickProduct(event) {
                const self = this;
                let addProductBeforeSuper = false
                const selectedOrder = this.env.pos.get_order();

                let product = self.get_product_object(event.detail);
                let is_continue = self.continue_action(product);
                if(product && is_continue){

                    let variants = self.get_product_variants(product);
                    if(variants.length > 1){
                        let {confirmed: variant_confirmed , payload: variant_selected} = await self.showPopup('SelectionPopup', {
                            title: self.env._t('Select Variant'),
                            list: variants,
                        });
                        if (variant_confirmed) {
                            product = variant_selected;
                        }
                        // Do not add product if cancel Select Variant.
                        if(!variant_confirmed){
                            return;
                        }
                    }else{
                        if(product.product_variant_ids){
                            product = self.env.pos.db.get_product_by_id(product.product_variant_ids[0]);
                        }
                    }

                    if(product){

                        //Employee Meal Limit Budged
                        if(this.env.pos.product_taxes_id){
                            if(this.env.pos.product_taxes_id[product.id]){
                                product['taxes_id'] = this.env.pos.product_taxes_id[product.id];
                            }
                        }
                        if(this.env.pos.selected_order_method == 'employee-meal'){ 
                            if(!this.env.pos.product_taxes_id){
                                this.env.pos.product_taxes_id = {}
                            }
                            if(product['taxes_id']){
                                this.env.pos.product_taxes_id[product.id] = product['taxes_id'];
                            }
                            product['taxes_id'] = [];

                            let limit_budget = this.env.pos.config.employee_meal_limit_budget;
                            if(typeof selectedOrder.employeemeal_budget != 'undefined'){
                                limit_budget = selectedOrder.employeemeal_budget;
                            }
                            let total_order = product.get_price_with_tax() + selectedOrder.get_total_with_tax();
                            console.log("Employee Budget limit is :", limit_budget);
                            if(total_order > limit_budget){
                                this.showPopup('ErrorPopup', { 
                                    title: this.env._t('Warning'),
                                    body: this.env._t('Employee meal reach budget limitation'),
                                    confirmText: 'OK',
                                    cancelText: ''
                                })
                                return false;
                            }
                        }

                        if (!addProductBeforeSuper) {
                            if (!self.currentOrder) {
                                self.env.pos.add_new_order();
                            }
                            const options = await this._getAddProductOptions(product);
                            // Do not add product if options is undefined.
                            if (!options){
                                // Do Nothing
                            } else{
                                // Add the product after having the extra information.
                                this.currentOrder.add_product(product, options);
                                NumberBuffer.reset();
                            }
                        }
                        
                        const selectedLine = selectedOrder.get_selected_orderline();
                        if (!selectedLine) {
                            return this.env.pos.alert_message({
                                title: this.env._t('Error'),
                                body: this.env._t('Line selected not found')
                            })
                            return false
                        }

                        if (product.multi_variant && this.env.pos.variant_by_product_tmpl_id[product.product_tmpl_id]) {
                            let variants = this.env.pos.variant_by_product_tmpl_id[product.product_tmpl_id];
                            let {confirmed, payload: results} = await this.showPopup('PopUpSelectionBox', {
                                title: this.env._t('Select Variants and Values'),
                                items: variants
                            })
                            if (confirmed) {
                                let variantIds = results.items.map((i) => (i.id))
                                selectedLine.set_variants(variantIds);
                            }
                        }

                        let combo_items = this.env.pos.combo_items.filter((c) => selectedLine.product.product_tmpl_id == c.product_combo_id[0])
                        if (combo_items && combo_items.length > 0) {
                            selectedOrder.setBundlePackItems()
                        }

                        if (self.env.pos.config.required_ask_seat && !self.env.pos.config.iface_floorplan){
                            let line_product_ids = this.env.pos.get_order().get_orderlines().map((x) => x.product.id);
                            if (line_product_ids.includes(event.detail.id) != true){
                                let {confirmed, payload: seat_number} = await this.showPopup('NumberPopup', {
                                    title: this.env._t('Please Input Seat Number'),
                                    isPassword: true,
                                })
                                if (confirmed) {
                                    selectedLine.set_required_ask_seat('S' + seat_number);
                                }
                            }
                        }
                        

                    }
                }

                clearTimeout(scrollCartToBottomTimeout);
                scrollCartToBottomTimeout = setTimeout(function() {
                    var scroll = $('.product-screen .order');
                    scroll.scrollTop(scroll.prop('scrollHeight'));
                }, 300);

            }

            async roundingTotalAmount() {
                let selectedOrder = this.env.pos.get_order();
                let roundingMethod = this.env.pos.payment_methods.find((p) => p.journal && p.pos_method_type == 'rounding')
                if (!selectedOrder || !roundingMethod) {
                    return this.env.pos.alert_message({
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
                    return true;
                } else {
                    selectedOrder.add_paymentline(roundingMethod);
                    let roundedPaymentLine = selectedOrder.selected_paymentline;
                    roundedPaymentLine.amount = -amountRound // TODO: not call set_amount method, because we blocked change amount payment line is rounding at payment screen
                    roundedPaymentLine.trigger('change', roundedPaymentLine)
                }
            }
        }
    Registries.Component.extend(ProductScreen, RetailProductScreen);

    return RetailProductScreen;
});
