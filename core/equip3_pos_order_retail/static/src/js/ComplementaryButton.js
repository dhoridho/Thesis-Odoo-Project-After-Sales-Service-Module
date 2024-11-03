odoo.define('equip3_pos_order_retail.ComplementaryButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t;

    class ComplementaryButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            let {confirmed, payload: selection} = await this.showPopup('SelectionPopup', {
                title: this.env._t('Selection Type Complementary Food'),
                list: [
                    {
                        label: this.env._t('Only Selected Order'),
                        item: true,
                        id: 1,
                    },
                    {
                        label: this.env._t('All order Have Item in Cart'),
                        item: false,
                        id: 2,
                    }
                ],
            })
            if (confirmed) {
                if (selection){
                    const product_data = this.env.pos.get_order().get_orderlines().map((x) => x.product) || []
                    let {confirmed, payload: product} = await this.showPopup('PopUpCardComplementaryNote', {'product_data': product_data})
                    if(confirmed){

                        _.each(this.env.pos.get_order().get_orderlines(), function(element, index){
                            var standard_price = 0.0;
                            var temp = index + 1;
                            var qty = parseInt($('.complementarynotepopup').find("input[name='quantity']").val());
                            var product_id = parseInt($('.complementarynotepopup').find("select[name='product']").val());
                            var note = $('.complementarynotepopup').find("input[name='notes']").val(); 
                            if (element.product.id == product_id){
                                element.set_quantity(qty);
                                element.set_is_complementary(true);
                                element.set_note(note);
                                element.set_unit_price(standard_price);
                            }
                        });
                    }
                }
                else{
                    _.each(this.env.pos.get_order().get_orderlines(), function(element, index){
                        var standard_price = 0.0;
                        element.set_is_complementary(true);
                        element.set_unit_price(standard_price);
                    });
                }
            }
        }
    }
    ComplementaryButton.template = 'ComplementaryButton';
    
    ProductScreen.addControlButton({
        component: ComplementaryButton,
        condition: function() {
            return this.env.pos.config.is_complementary;
        },
    });

    Registries.Component.add(ComplementaryButton);

    return ComplementaryButton;
});
