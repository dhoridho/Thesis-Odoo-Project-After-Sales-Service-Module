odoo.define('equip3_pos_masterdata.ProductCheckOut', function (require) {
    'use strict';
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ControlButtonsMixin = require('point_of_sale.ControlButtonsMixin');
    const {useState} = owl.hooks;
    const {useListener} = require('web.custom_hooks');
    const {posbus} = require('point_of_sale.utils');

    let totalWillPaidTimeout = null;

    class ProductCheckOut extends ControlButtonsMixin(PosComponent) {
        constructor() {
            super(...arguments);
            let self = this;
            this._currentOrder = this.env.pos.get_order();
            if (this._currentOrder) {
                this._currentOrder.orderlines.on('change', this.render, this);
                this._currentOrder.orderlines.on('remove', this.render, this);
                this._currentOrder.orderlines.on('change', () => {
                    clearTimeout(totalWillPaidTimeout);
                    totalWillPaidTimeout = setTimeout(function() {
                        self._totalWillPaid();
                    }, 300);
                }, this); 
                this._currentOrder.orderlines.on('remove', this._totalWillPaid, this);
                this._currentOrder.paymentlines.on('change', this._totalWillPaid, this);
                this._currentOrder.paymentlines.on('remove', this._totalWillPaid, this);
            }
            this.env.pos.on('change:selectedOrder', this._updateCurrentOrder, this);
            this.state = useState({
                total: 0,
                tax: 0,
                inputCustomer: '',
                countCustomers: 0,
                totalQuantities: 0,
                showButtons: this.env.pos.showAllButton
            });
            this._totalWillPaid()
        }

        async UpdateTheme() {
            await this.showPopup('PopUpUpdateTheme', {
                title: this.env._t('Modifiers POS Theme'),
            })
        }

        async setProductsView() {
            if (this.env.pos.config.product_view == 'list') {
                this.env.pos.config.product_view = 'box'
            } else {
                this.env.pos.config.product_view = 'list'
            }
            await this.rpc({
                model: 'pos.config',
                method: 'write',
                args: [[this.env.pos.config.id], {
                    product_view: this.env.pos.config.product_view,
                }],
            })
            this.env.qweb.forceUpdate();
        }

        async setLimitedProductsDisplayed() {
            const {confirmed, payload: number} = await this.showPopup('NumberPopup', {
                title: this.env._t('How many Products need Display on Products Screen'),
                startingValue: this.env.pos.db.limit,
            })
            if (confirmed) {
                if (number > 0) {
                    if (number > 1000) {
                        return this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t('Maximum can set is 1000')
                        })
                    } else {
                        this.env.pos.db.limit = number
                        this.env.qweb.forceUpdate();
                    }
                } else {
                    this.env.pos.alert_message({
                        title: this.env._t('Warning'),
                        body: this.env._t('Required number bigger than 0')
                    })
                }
            }
        }


        get isActiveShowGuideKeyboard() {
            return this.env.isShowKeyBoard
        }

        async showKeyBoardGuide() {
            this.env.isShowKeyBoard = !this.env.isShowKeyBoard;
            this.env.qweb.forceUpdate();
            return this.showPopup('ConfirmPopup', {
                title: this.env._t('Tip !!!'),
                body: this.env._t('Press any key to Your Keyboard, POS Screen auto focus Your Mouse to Search Products Box. Type something to Search Box => Press to [Tab] and => Press to Arrow Left/Right for select a Product. => Press to Enter for add Product to Cart'),
                disableCancelButton: true,
            })
        }

        async getProductsTopSelling() {
            const {confirmed, payload: number} = await this.showPopup('NumberPopup', {
                title: this.env._t('How many Products top Selling you need to show ?'),
                startingValue: 10,
            })
            if (confirmed) {
                const productsTopSelling = await this.rpc({
                    model: 'pos.order',
                    method: 'getTopSellingProduct',
                    args: [[], parseInt(number)],
                })
                let search_extends_results = []
                this.env.pos.productsTopSelling = {}
                if (productsTopSelling.length > 0) {
                    for (let index in productsTopSelling) {
                        let product_id = productsTopSelling[index][0]
                        let qty_sold = productsTopSelling[index][1]
                        this.env.pos.productsTopSelling[product_id] = qty_sold
                        let product = this.env.pos.db.get_product_by_id(product_id);
                        if (product) {
                            search_extends_results.push(product)
                        }
                    }
                }
                if (search_extends_results.length > 0) {
                    this.env.pos.set('search_extends_results', search_extends_results)
                    posbus.trigger('reload-products-screen')
                    posbus.trigger('remove-filter-attribute')
                }
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

        get isCustomerSet() {
            if (this.env.pos.get_order() && this.env.pos.get_order().get_client()) {
                return true
            } else {
                return false
            }
        }

        async onKeydown(event) {
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

        _updateCurrentOrder(pos, newSelectedOrder) {
            this._currentOrder.orderlines.off('change', null, this);
            if (newSelectedOrder) {
                this._currentOrder = newSelectedOrder;
                this._currentOrder.orderlines.on('change', this.render, this);
            }
        }

        _totalWillPaid() {
            const total = this._currentOrder ? this._currentOrder.get_total_with_tax() : 0;
            const due = this._currentOrder ? this._currentOrder.get_due() : 0;
            const tax = this._currentOrder ? total - this._currentOrder.get_total_without_tax() : 0;
            var currency = false
            if(this._currentOrder){
                currency = this._currentOrder.currency
            }
            this.state.total = total;
            this.state.tax = this.env.pos.format_currency(tax,false,currency);
            let totalQuantities = 0
            if (this._currentOrder) {
                for (let i = 0; i < this._currentOrder.orderlines.models.length; i++) {
                    let line = this._currentOrder.orderlines.models[i]
                    totalQuantities += line.quantity
                }
            }
            this.state.totalQuantities = totalQuantities
            // if (this.env.pos.config.promotion_auto_add && this.env.pos.apply_promotion_succeed) {
            //     this.env.pos.apply_promotion_succeed = false;
            //     var $button = $('button.order-total-btn').find('span.custom_apply_promotion');
            //     if ($button.length === 0) {
            //         $('button.order-total-btn').find('font').addClass('oe_hidden');
            //         $('button.order-total-btn').find('.pos_order_total').addClass('oe_hidden');
            //         $('button.order-total-btn').append($('<span class="custom_apply_promotion" style="font-size: 22px;"><i class="fa fa-check"/> Apply Promotion</span>'));
            //     }
            // }
            this.render();
        }

        mounted() {
            const self = this;
            super.mounted();
        }

        willUnmount() {
            super.willUnmount();
        }

        get client() {
            return this.env.pos.get_client();
        }

        get isLongName() {
            return this.client && this.client.name.length > 10;
        }

        get currentOrder() {
            return this.env.pos.get_order();
        }

        get invisiblePaidButton() {
            const selectedOrder = this._currentOrder;
            if (!selectedOrder || !this.env.pos.config.allow_payment || (selectedOrder && selectedOrder.get_orderlines().length == 0)) {
                return true
            } else {
                return false
            }
        }
    }

    ProductCheckOut.template = 'ProductCheckOut';

    Registries.Component.add(ProductCheckOut);

    return ProductCheckOut;
});
