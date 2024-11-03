odoo.define('equip3_pos_general.ProductScreenSection1', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');
    const {useListener} = require('web.custom_hooks');
    const {useExternalListener} = owl.hooks;
    const {posbus} = require('point_of_sale.utils');
    var rpc = require('web.rpc');
    const {Gui} = require('point_of_sale.Gui');

    class ProductScreenSection1 extends PosComponent {
        constructor() {
            super(...arguments);
            
            useListener('fire-main-course', () => this.fireMainCourse());
            useListener('fire-dessert', () => this.fireDessert());
            useExternalListener(window, 'click', this.CheckClickAll);
        }

        OpenFeatureButtonsMobile(){
            if ($('.pos_new_section').hasClass('pos-hidemobile')){
                $('.pos_new_section').removeClass('pos-hidemobile')
            }else{
                $('.pos_new_section').addClass('pos-hidemobile')
            }
        }

        async CheckClickAll(event) {
            if(!$(event.target).hasClass('button_open_feature')&&!$(event.target).parents().hasClass('pos-button-list')&&!$(event.target).hasClass('pos-button-list')){
                if($('.pos-button-list').length > 0){
                    this.OpenFeatureButtons()
                }
            }
        }

        OpenFeatureButtons() {
            this.env.pos.showAllButton = !this.env.pos.showAllButton;
            posbus.trigger('change-list-feature-buttons');
        }

        async CardPaymentButton() {
            const card_groups = this.env.pos.db.get_card_groups() || []
            const { confirmed, payload: selected_payment_card_id} = await this.showPopup('PopUpCardPayment', {
                card_groups: card_groups
            });
            if (confirmed) {
                this.env.pos.get_order().set_selected_card_payment_id(selected_payment_card_id);
                var card_payment_obj = this.env.pos.db.get_card_payment_by_id(selected_payment_card_id);
                return this.env.pos.alert_message({
                    title: this.env._t('Card Selected!'),
                    body: this.env._t('Successfully Selected '+ card_payment_obj.card_name+ ' Card Payment.'),
                });
            }
        }


        async HomeDeliveryButtonClick() {
            var self = this;
            var order = self.env.pos.get_order();
            if (!order) {
                return this.env.pos.alert_message({
                    title: this.env._t('Warning!'),
                    body: this.env._t('Please create order first.'),
                });
            }

            if(order.orderlines.length <= 0) {
                return this.env.pos.alert_message({
                    title: this.env._t('Warning!'),
                    body: this.env._t('Please add product first.'),
                });
            }


            if(!order.get_client()){
                return this.env.pos.alert_message({
                    title: this.env._t('Warning!'),
                    body: this.env._t('Please select member first.'),
                });
            }
            await order._open_pop_up_home_delivery_order()


        }

        async SelfPickingButtonClick() {
            var self = this;
            var order = self.env.pos.get_order();
            if (!order) {
                return this.env.pos.alert_message({
                    title: this.env._t('Warning!'),
                    body: this.env._t('Please create order first.'),
                });
            }

            if(order.orderlines.length <= 0) {
                return this.env.pos.alert_message({
                    title: this.env._t('Warning!'),
                    body: this.env._t('Please add product first.'),
                });
            }


            if(!order.get_client()){
                return this.env.pos.alert_message({
                    title: this.env._t('Warning!'),
                    body: this.env._t('Please select member first.'),
                });
            }
            order.is_self_picking = true
            order.trigger('change', order);
            let order_ids = await this.env.pos.push_single_order(order, {
                draft: true
            })
            this.showPopup('ConfirmPopup', {
                title: this.env._t('New Self Picking Order ID: ' + order_ids[0]),
                body: this.env._t('Order saved to Draft State, please Full Fill Payment Order: ') + order.name,
                disableCancelButton: true,
            })
            return this.showScreen('ReceiptScreen');
        }

        async CardPaymentButonClick() {
            let { confirmed, payload: values} = await this.showPopup('CardPaymentPopup');
            if (confirmed) {
                let order = this.env.pos.get_order();
                order.set_selected_card_payment(values);
                let card_payment = this.env.pos.db.get_card_payment_by_id(values.card_payment_id);
                return this.env.pos.alert_message({
                    title: this.env._t('Successfully...'),
                    body: this.env._t('Successfully Selected '+ card_payment.card_name + ' Card Payment.'),
                });
            }
        }
        

        async PromotionButtonClick() {
            var self = this;
            var order = self.env.pos.get_order();
            if (order.is_return) {
                return false;
            }
            if(order.orderlines.length <= 0) {
                return this.env.pos.alert_message({
                    title: this.env._t('Warning!'),
                    body: this.env._t('Please add product first.'),
                });
            }
            
            //  Filter promotion display to make sure applied promo doesnt show again
            var promotions = order.get_promotions_active()['promotions_active'];
            _.filter(order.orderlines.models, function (line) {
                if (line['promotion_ids']) {
                    let applied_promo_ids = line['promotion_ids'] || [];
                    promotions = promotions.filter(p => !applied_promo_ids.includes(p.id));
                }
            });



            let ProductIds = order.orderlines.models.map(l => l.product.id);
            let ProductBrandArray = order.orderlines.models.map(l => l.product.product_brand_ids);
            let AllProductBrandIds = ProductBrandArray.reduce((a, b) => a.concat(b));

            if (promotions) {
                let promotion_list = [];
                promotions.forEach((promotion) => {
                    if (!promotion.product_brand_id || promotion.product_brand_id && AllProductBrandIds.includes(promotion.product_brand_id[0])) {
                        promotion_list.push({
                            label: self.env._t(promotion.name),
                            item: promotion,
                            id: promotion.id,
                        });
                    }
                });
                let {confirmed, payload: promotion_selected} = await self.showPopup('SelectionPopup', {
                    title: self.env._t('Select Promotion'),
                    list: promotion_list,
                });
                if (confirmed) {
                    const linesAppliedPromotion = order.orderlines.models.find(l => l.promotion);
                    if (!linesAppliedPromotion || (linesAppliedPromotion && promotion_selected.is_stack)) {
                        if (promotion_selected.new_type == 'Tebus Murah' && promotion_selected.type != '17_tebus_murah_by_selected_brand' && promotion_selected.type != '15_tebus_murah_by_specific_product'){
                            await order.select_promotion_tebus_murah(promotion_selected);
                        } else {
                            order.apply_promotion([promotion_selected])
                        }
                        // reset the apply promotion button
                        self.env.pos.apply_promotion_succeed = true;
                    } else {
                        self.env.pos.alert_message({
                            title: self.env._t('Warning'),
                            body: self.env._t('Can not apply multiple promotions! PROMOTION : '+ promotion_selected.name+ ' is not stackable.'),
                        })
                    }
                }
            } else {
                self.env.pos.alert_message({
                    title: self.env._t('Warning'),
                    body: self.env._t('Have not any Promotions active')
                })
            }
        }


        async PromotionCancelButtonClick() {
            var self = this;
            let selectedOrder = this.env.pos.get_order();
            const linesAppliedPromotion = selectedOrder.orderlines.models.find(l => l.promotion)

            if(selectedOrder && selectedOrder.is_return){
                return Gui.showPopup('ConfirmPopup', {
                    title: this.env._t('Warning'),
                    body: this.env._t('Return order can not cancel promotion that have already been applied.'),
                });
            }

            if (linesAppliedPromotion) {
                let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t("Cancel Promotions?"),
                    body: this.env._t("Are you sure to cancel all the applied promotions?"),
                })
                if (confirmed) {
                    selectedOrder.remove_all_promotion_line();
                    // reset the apply promotion button
                    self.env.pos.apply_promotion_succeed = false;

                    //remove coupon
                    selectedOrder.reset_client_use_coupon();
                }
            } else {
                this.env.pos.alert_message({
                    title: this.env._t('Warning'),
                    body: this.env._t('No promotions are active in current order!')
                })
            }
        }

    }

    ProductScreenSection1.template = 'ProductScreenSection1';
    Registries.Component.add(ProductScreenSection1);
    return ProductScreenSection1;
});
