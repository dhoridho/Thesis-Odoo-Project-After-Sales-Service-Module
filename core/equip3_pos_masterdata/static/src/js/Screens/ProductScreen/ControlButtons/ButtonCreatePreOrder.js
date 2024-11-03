odoo.define('equip3_pos_masterdata.ButtonCreatePreOrder', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const {Printer} = require('point_of_sale.Printer');
    const core = require('web.core');
    const _t = core._t;

    // TODO: let : là biến trong 1 khối, biến này được thay đổi giá trị và được duy trì trong khối mà thôi (khối là 1 block {} )
    // TODO: const : là 1 biến không bao giờ thay đổi và duy trì xuyên suốt trong 1 class

    class ButtonCreatePreOrder extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
            this._currentOrder = this.env.pos.get_order();
            this._currentOrder.orderlines.on('change', this.render, this);
            this.env.pos.on('change:selectedOrder', this._updateCurrentOrder, this);
        }

        willUnmount() {
            this._currentOrder.orderlines.off('change', null, this);
            this.env.pos.off('change:selectedOrder', null, this);
        }

        get isHighlighted() {
            var order = this.env.pos.get_order();
            if (order && order.is_pre_order) {
                return true;
            }
            return false
        }

        _updateCurrentOrder(pos, newSelectedOrder) {
            this._currentOrder.orderlines.off('change', null, this);
            if (newSelectedOrder) {
                this._currentOrder = newSelectedOrder;
                this._currentOrder.orderlines.on('change', this.render, this);
            }
        }

        async onClick() {
            let self = this;
            let order = this.env.pos.get_order();
            var is_can_be_po = true
            if (order) {
                if(!order.is_pre_order) {

                    if(order.orderlines.length <= 0) {
                        is_can_be_po = false
                        return this.env.pos.alert_message({
                            title: this.env._t('Warning!'),
                            body: this.env._t('Please add product first.'),
                        });
                    }


                    if(!order.get_client()){
                        is_can_be_po = false
                        return this.env.pos.alert_message({
                            title: this.env._t('Warning!'),
                            body: this.env._t('Please select member first.'),
                        });
                    }

                    var is_exist_product_po = false

                    for (let i = 0; i < order.orderlines.models.length; i++) {
                        let line = order.orderlines.models[i];
                        if (line.product.is_can_be_po) {
                            is_exist_product_po = true
                            break
                        }
                    }

                    if(!is_exist_product_po){
                        is_can_be_po = false
                        return this.env.pos.alert_message({
                            title: this.env._t('Warning!'),
                            body: this.env._t('There are no products that can be pre-ordered'),
                        });
                    }


                    if(is_can_be_po){
                        let {confirmed, payload} = await this.showPopup('PopUpConfirmPreOrder', { 
                            order: order,
                        });
                        if (!confirmed){
                            return false;
                        }
                        if (confirmed) {
                            order.is_pre_order = true
                            order.estimated_order_pre_order = payload['estimated_date']
                            this.render()
                        }
                    }

                }
                else{
                    let {confirmed, payload} = await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Pre - Order'),
                        body: this.env._t('Are you sure want to cancel Pre - Order ?')
                    })
                    if (confirmed) {
                        order.is_pre_order = false
                        order.estimated_order_pre_order = false
                        this.render()
                    }
                }
            }
            
        }
    }

    ButtonCreatePreOrder.template = 'ButtonCreatePreOrder';

    ProductScreen.addControlButton({
        component: ButtonCreatePreOrder,
        condition: function () {
            return 1==1;
        },
    });

    Registries.Component.add(ButtonCreatePreOrder);

    return ButtonCreatePreOrder;
});
