odoo.define('equip3_pos_masterdata.SearchBar', function (require) {
    'use strict';

    const SearchBar = require('point_of_sale.SearchBar');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    const RetailSearchBar = (SearchBar) =>
        class extends SearchBar {
            constructor() {
                super(...arguments);
            }

            willUnmount() {
                super.willUnmount();
                posbus.off('clear-search-bar', null, null);
                if($('#mlkeyboard').length){
                    $('#mlkeyboard').remove()
                }
            }

            mounted() {
                super.mounted()
                posbus.on('clear-search-bar', this, this.autoClearSearchBox);

                if(this.props.virtualkeyboard){
                    this.virtualKeyboard();
                }
            }

            _onBlur() {
                posbus.trigger('blur.search.products')
            }

            _onClick() {
                posbus.trigger('click.search.products')
            }

            virtualKeyboard(){
                let $target = $(this.el).find('input[type=text]');
                if(!$target.hasClass('virtual-keyboard')){
                    $target.mlKeyboard({
                      layout: 'en_US',
                      SearchBar: this,
                    });
                }
                $target.addClass('virtual-keyboard');
            }
            closeVirtualKeyboard(){
                this.state.showSearchFieldsVK = false;
            }

            updateSearchBox(value){
                this.state.searchInput = value;
                this.state.showSearchFields = true;
                this.state.showSearchFieldsVK = true;
                this.trigger('update-search',value);
                this.render();
            }

            _hideOptions() {
                super._hideOptions();
                if(this.state.showSearchFieldsVK){
                    this.state.showSearchFields = true;
                }
            }
            autoClearSearchBox() {
                this.state.searchInput = ""
                this.trigger('update-search', "");
                this.render();
            }

            async clearInput() {
                // await this.env.pos.syncProductsPartners();
                this.state.searchInput = ""
                this.trigger('update-search', "");
                this.render();
            }

            onKeyup(event) {
                let key = event.which || event.keyCode;
                let ctrl = event.ctrlKey ? event.ctrlKey : ((key === 17) ? true : false);
                let ctrl_v = ctrl && event.code == 'KeyV'; //Ctrl + V
                let ctrl_z = ctrl && event.code == 'KeyZ'; //Ctrl + Z

                var only = false
                if (this.state.searchInput.length >= 6 && event.key === 'Enter') {
                    if (this.state.searchInput in this.env.pos.db.product_by_barcode){
                        only = true
                        return true
                    }
                    if(ctrl){
                        if (ctrl_v) {
                            this.trigger('update-search', event.target.value);
                        } 
                        if (ctrl_z) {
                            this.trigger('update-search', event.target.value);
                        }
                    }
                }
                if(this.state.searchInput=='onbarcode'){
                    this.state.searchInput = ''
                    return true
                }
                super.onKeydown(event);
            }

            onKeyup(event) {
                if (this.state.searchInput.length >= 6) {
                    if (this.state.searchInput in this.env.pos.db.product_by_barcode){
                        if (event.code == 'Enter') {
                            return true
                        }
                        var product = this.env.pos.db.product_by_barcode[this.state.searchInput]
                        var order = this.env.pos.get_order()
                        if(order){
                            order.add_product(product, {
                                quantity: 1,
                            });
                        }
                        this.state.searchInput = ""
                        event.target.value = ""
                        return true
                    }
                }
                
                // TODO: automaticSearchOrder variable from xml of screens: invoice, sale order and pos order
                // It can help this seachbar know it from 3 screen and trigger event typing of user and send to any screen available
                if (this.props.automaticSearchOrder) {
                    this.trigger('event-keyup-search-order', event.target.value);
                } else {
                    if (event.code == 'Enter' && this.state.searchInput.length >= 6) {
                        this.trigger('try-add-product', { searchWordInput: this.state.searchInput });
                    }
                }
            }
        }
    Registries.Component.extend(SearchBar, RetailSearchBar);

    return RetailSearchBar;
});
