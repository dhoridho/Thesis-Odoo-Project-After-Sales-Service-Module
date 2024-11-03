odoo.define('equip3_pos_masterdata_fnb.CustomComplementaryButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');
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
                let Order = this.env.pos.get_order();
                if (selection){
                    let Lines = Order.get_orderlines();
                    const product_data = Lines.map((x) => x.product) || [];
                    let {confirmed, payload: product} = await this.showPopup('PopUpCardComplementaryNote', {'product_data': product_data});
                    if(confirmed){
                        var qty = parseInt($('.complementarynotepopup').find("input[name='quantity']").val());
                        var product_id = parseInt($('.complementarynotepopup').find("select[name='product']").val());
                        var note = $('.complementarynotepopup').find("input[name='notes']").val();

                        let Orderline = _.chain(Lines)
                            .filter(l => l.product.id == product_id)
                            .sortBy(i => i.is_complementary)
                            .value();

                        if (Orderline.length) {
                            let TmplOrderLine = Orderline.at(0);
                            // let SelectedLine = Order.get_selected_orderline();
                            var new_qty = parseInt(TmplOrderLine.quantity - qty);
                            if (new_qty < 0) {
                                return Gui.showPopup('ErrorPopup', {
                                    title: _t('Error'),
                                    body: TmplOrderLine.product.display_name + _t(' quantity is smaller than it\'s Complementary quantity.')
                                });
                            }
                            // SelectedLine.set_note(note);
                            TmplOrderLine.set_note(note);
                            if (TmplOrderLine.quantity == qty && this.env.pos.config.tax_affect_compliment) {
                                TmplOrderLine.set_is_complementary(true);

                            } else if (TmplOrderLine.quantity == qty) {
                                TmplOrderLine.set_unit_price(0.0);
                                TmplOrderLine.set_is_complementary(true);

                            } else if (new_qty >= 0 && this.env.pos.config.tax_affect_compliment) {
                                TmplOrderLine.set_quantity(new_qty);
                                TmplOrderLine.set_is_complementary(false);

                                var newLine = TmplOrderLine.clone();
                                Order.add_orderline(newLine);
                                newLine.set_quantity(qty);
                                newLine.set_is_complementary(true);
                                newLine.trigger('change', newLine);

                            } else if (new_qty >= 0) {
                                TmplOrderLine.set_quantity(new_qty);
                                TmplOrderLine.set_is_complementary(false);

                                var newLine = TmplOrderLine.clone();
                                Order.add_orderline(newLine);
                                newLine.set_quantity(qty);
                                newLine.set_is_complementary(true);
                                newLine.set_unit_price(0.0);
                                newLine.trigger('change', newLine);
                            }
                        }
                    }
                }
                else{
                    _.each(Order.get_orderlines(), function(element, index){
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
        position: ['after', 'SubmitOrderButton'],
    });

    Registries.Component.add(ComplementaryButton);

    return ComplementaryButton;
});
