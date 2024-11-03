odoo.define('equip3_pos_order_retail.combo_options', function(require) {
    'use strict';
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');

    const PosComboProductScreen = ProductScreen =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
            }
            async _clickProduct(event) {
                var self = this;
                super._clickProduct(event);
                var id_lst = this.env.pos.get_order().get_orderlines().map((x) => x.product.id)
                if (self.env.pos.config.required_ask_seat){
                    if (id_lst.includes(event.detail.id) != true){
                        let {confirmed, payload: input} = await this.showPopup('NumberPopup', {
                            title: this.env._t('Please Input Seat Number'),
                        })
                        if (confirmed) {
                            if (self.env.pos.get_order()){
                                self.env.pos.get_order().get_selected_orderline().set_required_ask_seat('S'+input)
                            }

                        }
                    }
                }
                const product = event.detail;
                var product_is_combo = product.is_combo_product;
                var product_is_combo_items = product.combo_option_items;
                // var pos_categories = this.posmodel.pos_category_by_id
                var pos_appe_categories_list=[];
                var pos_main_categories_list=[];
                var pos_dess_categories_list=[];
                _.each(posmodel.pos_categories, function(catg){
                    if (catg.category_type == 'appetizer') {
    //                    self.props.pos_categories_list.push(catg.id);
                        pos_appe_categories_list.push(catg.id)
                    } else if(catg.category_type == 'main') {
                        pos_main_categories_list.push(catg.id);
                    } else if(catg.category_type == 'dessert') {
                        pos_dess_categories_list.push(catg.id);
                    }
                });
                var pos_combo_categ_groups = [];
                pos_combo_categ_groups['appetizer'] = pos_appe_categories_list;
                pos_combo_categ_groups['main'] = pos_main_categories_list;
                pos_combo_categ_groups['dessert'] = pos_dess_categories_list;
                if(product && product.is_combo_product && product.combo_option_id){
                    let { confirmed, payload: result } = await this.showPopup('PosComboConfigurePopup', {
                        title: product.display_name,
                        product: product,
                        pos_combo_id: product.combo_option_id[0],
                        is_combo_product: product.is_combo_product,
                        pos_combo_categ_groups: pos_combo_categ_groups,
                    });
                    if(confirmed && result){
                        _.each(result, function(data){
                            self.env.pos.get_order().add_product(data.product, {quantity:1, merge: false, price:data.price});
                        });
                        
                    }
                }

            }
        };
    Registries.Component.extend(ProductScreen, PosComboProductScreen);
    
    class PosComboProductItem extends PosComponent {
        constructor() {
            super(...arguments);
        }
        get imageUrl() {
            const product = this.props.product;
            return `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
        }
        OnSelectComboProduct(event) {
            $(event.currentTarget).addClass('pselected');
        }
        onProductRemoveClick(event) {
            $(event.currentTarget).closest('.pselected').removeClass('pselected');
        }
        get price(){
            return this.env.pos.format_currency(this.props.extra_price);
        }
    }
    PosComboProductItem.template = 'PosComboProductItem';

    Registries.Component.add(PosComboProductItem);
    return {
        ProductScreen: ProductScreen,
        PosComboProductItem: PosComboProductItem
    }
});