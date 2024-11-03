odoo.define('equip3_pos_general_fnb.ComboOptionPopUps', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class ComboOptionPopUps extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {string} props.startingValue
         */
        constructor() {
            super(...arguments);
        }

        mounted() {

        }

        covertCurrency(rec){
            var price = rec.extra_price
            var order = this.env.pos.get_order()
            if(!order){
                this.env.pos.add_new_order();
                order = this.env.pos.get_order()
                price = this.env.pos.covertCurrency(order.pricelist,price)
            }
            else{
                price = this.env.pos.covertCurrency(order.pricelist,price)
            }
            return price
        }

        display_name(rec){
            let self = this;
            let display_name = rec.product_id[1];
            if(self.env.pos.config && self.env.pos.config.display_product_name_without_product_code){
                return display_name.replace(/[\[].*?[\]] */, '');
            }
            return display_name;
        }

        get_bom_components(option){
            let self = this;
            let components = [];
            let bom_components = self.env.pos.db.get_pos_bom_component_by_ids(option.pos_bom_line_ids);
            for (var i = bom_components.length - 1; i >= 0; i--) {
                let checked = false;
                if(!bom_components[i].is_extra){
                    checked = true;
                }
                components.push({
                    id: bom_components[i].id,
                    is_extra: bom_components[i].is_extra,
                    checked: checked,
                })
            }
            return JSON.stringify(components);
        }

        async onClickOption(ev){
            let $wrap = $(ev.target).closest('.combo-group');
            let maximum_pick = parseInt($wrap.attr('data-maximum_pick'));
            let $checked = $wrap.find('.combo-input:checked');
            $wrap.find('.combo-option').removeClass('disabled')
            if($checked.length == maximum_pick){
                $wrap.find('.combo-input:not(:checked)').closest('.combo-option').addClass('disabled');
            }
        }

        async on_change_bom_components(option){
            function configurableStatus(components){
                let not_configurable = components.filter((c)=> c.is_configurable == false);
                let state = 'configurable';
                if(not_configurable.length){
                    state = 'partial_configurable';
                }
                if(components.length == not_configurable.length){
                    state = 'not_configurable';
                }
                return state;
            }

            let self = this;
            let $target = $('.combo-option-form.option'+option.id);
            let components = self.env.pos.db.get_pos_bom_component_by_ids(option.pos_bom_line_ids);
            let title = option.product_id[1].replace(/[\[].*?[\]] */, '');

            let html_components = '';
            var bom_note = $target.attr('data-bom_component_notes') || ''
            var json_data_bom_components = $target.attr('data-bom_components') || ''
            if(json_data_bom_components!=''){
                json_data_bom_components = JSON.parse(json_data_bom_components)
            }
            var order = self.env.pos.get_order()
            if(!order){
                self.env.pos.add_new_order();
                order = self.env.pos.get_order()
            }

            for(let com of components){
                var price = self.env.pos.covertCurrency(order.pricelist,com.additional_cost)
                let additional_cost = self.env.pos.format_currency(price);
                let label = '';
                if(com.is_extra){
                    label += 'Extra ';
                }
                label += self.display_name(com);
                var class_bom = 'bom-line'
                if (!com.is_configurable){
                    class_bom += ' oe_hidden'
                }
                var checked_bom = ''
                if(json_data_bom_components){
                    var checked_bom_js = json_data_bom_components.filter((c)=> c.id == com.id)
                    if(checked_bom_js && checked_bom_js[0].checked){
                        checked_bom = 'checked="checked"'
                    }
                }
                html_components += `
                    <div class="${class_bom}" extra="${com.is_extra?'1':'0'}"  data-is_configure="${com.is_configurable?'1':'0'}">
                        <label for="bom-line-1">${label}</label>
                        <div class="bom-line-form">`;
                            if(com.is_extra){
                                html_components += `
                                    <span>+${additional_cost}</span>
                                    <input type="checkbox"
                                        id="bom-component${com.id}" 
                                        name="bom-component${com.id}" 
                                        data-id="${com.id}" ${checked_bom}/>
                                `;
                            }else{
                                if(json_data_bom_components){
                                    html_components += `
                                        <input type="checkbox"
                                            id="bom-component${com.id}" 
                                            name="bom-component${com.id}" 
                                            data-id="${com.id}"
                                            ${checked_bom}/>
                                    `;
                                }
                                else{
                                    html_components += `
                                        <input type="checkbox"
                                            id="bom-component${com.id}" 
                                            name="bom-component${com.id}" 
                                            data-id="${com.id}"
                                            checked="checked"/>
                                    `;
                                }
                                    
                            }

                html_components += `
                        </div>
                    </div>
                    `;
            }
            let $popup = $(`
                <div class="popups popups-customize_bom">
                    <div role="dialog" class="modal-dialog customize_bom_popups">
                        <div class="popup popup-textarea">
                            <header class="title drag-handle">
                                ${title}
                            </header>
                            <div class="bom-notes">
                                <label for="bom-notes">Notes</label>
                                <div class="bom-line-form">
                                    <textarea id="bom-notes"
                                        name="bom-notes" rows="4" placeholder="Add note here" value="${bom_note}"></textarea>
                                </div>
                            </div>
                            <div class="bom-component ${configurableStatus(components)}">
                                ${html_components}
                            </div>
                            <footer class="footer">
                                <div class="button cancel" t-on-click="cancel">
                                    Cancel
                                </div>
                                <div class="button confirm" t-on-click="confirm">
                                    Save Change
                                </div>
                            </footer>
                        </div>
                    </div>
                </div>
            `);
            $popup.appendTo('.o_action_manager>.pos');
            $('textarea#bom-notes').val(bom_note)
            $popup.find('.button.cancel').click(function (e) { $popup.remove(); });
            $popup.find('.button.confirm').click(function (e) { 
                let bom_component_notes = $popup.find('[name="bom-notes"]').val();
                let new_components = [];
                $popup.find('.bom-line input[type=checkbox]').each(function(){
                    let $i = $(this);
                    for (var i = components.length - 1; i >= 0; i--) {
                        let com = components[i];
                        if(com.id == parseInt($i.attr('data-id'))){
                            let new_components_vals = {
                                id: com.id,
                                is_extra: com.is_extra,
                                additional_cost: 0,
                                checked: $i.is(':checked'),
                            }
                            if (new_components_vals.is_extra && new_components_vals.checked) {
                                new_components_vals['additional_cost'] = com.additional_cost;
                            }
                            new_components.push(new_components_vals);
                        }
                    }
                });

                let additional_cost = new_components.reduce((acc, curr) => { return acc + curr.additional_cost }, 0);
                if (option.extra_price){
                    additional_cost += option.extra_price;
                }
                if (additional_cost){
                    $target.find('.extra_price').html('<span>+' + self.env.pos.format_currency(additional_cost) + '</span>');
                } else {
                    $target.find('.extra_price').html('<span>Free</span>');
                }

                $target.attr('data-bom_components', JSON.stringify(new_components));
                if(bom_component_notes){
                    $target.attr('data-bom_component_notes', bom_component_notes);
                }
                $popup.remove();
            });
        }

        getPayload() {
            let self = this;
            let values = { };
            let combo_options = [];
            var order = self.env.pos.get_order()
            if(!order){
                self.env.pos.add_new_order();
                order = self.env.pos.get_order()
            }

            $('.combo-option input[type=checkbox]:checked, .combo-option input[type=radio]:checked').each(function(){
                let $i = $(this);
                let res_id = parseInt($i.attr('data-id'))
                let option = self.env.pos.db.pos_combo_option_by_id[res_id];
                if(option && combo_options.includes(res_id) == false){
                    let opt_vals = {
                        id: option.id,
                        pos_combo_id: option.pos_combo_id,
                        product_id: option.product_id,
                        uom_id:option.uom_id,
                        extra_price: self.env.pos.covertCurrency(order.pricelist,option.extra_price),
                        pos_bom_line_ids: option.pos_bom_line_ids,
                        full_product_name: option.full_product_name,
                        product_only_name: option.product_only_name,
                    }
                    if(option.pos_bom_line_ids.length){
                        let new_components = [];
                        let bom_components = self.env.pos.db.get_pos_bom_component_by_ids(option.pos_bom_line_ids);
                        let curr_components = $i.closest('.combo-option-form').data('bom_components');
                        let bom_component_notes = $i.closest('.combo-option-form').data('bom_component_notes');
                        for(let com of curr_components){
                            for (var i = bom_components.length - 1; i >= 0; i--) {
                                let _com = bom_components[i];
                                if(_com.id == com.id){
                                    new_components.push({
                                        additional_cost: _com.additional_cost,
                                        bom_id: _com.bom_id,
                                        id: _com.id,
                                        is_extra: _com.is_extra,
                                        product_id: _com.product_id,
                                        product_qty: _com.product_qty,
                                        product_tmpl_id: _com.product_tmpl_id,
                                        full_product_name: _com.full_product_name,
                                        product_only_name: _com.product_only_name,
                                        checked: com.checked,
                                    });
                                }
                            }
                        }
                        
                        opt_vals.bom_components = new_components; // If Options is BoM Product
                        if(bom_component_notes){
                            opt_vals.bom_component_notes = bom_component_notes; // If Options is BoM Product
                        }
                    }
                    combo_options.push(opt_vals);
                }
            });

            if(combo_options.length){
                values['combo_options'] = combo_options;    
            }

            return values
        }
        confirm(){
            let has_error = [];
            $('.combo_option_popups .combo-group[data-required=1]').removeClass('has_error');
            $('.combo_option_popups .combo-group[data-required=1]').each(function(){
                let $group = $(this);
                let $input = $group.find('.combo-option input.combo-input:checked');
                if($input.length == 0){
                    $group.addClass('has_error');
                    has_error.push('required');
                }
            });
            if(has_error.length){
                return;
            }
            if($('.combo_option_popups .combo-option input.combo-input:checked').length == 0){
                return;
            }
            super.confirm();
        }
    }
    
    ComboOptionPopUps.template = 'ComboOptionPopUps';
    ComboOptionPopUps.defaultProps = {
        confirmText: 'Add Order',
        cancelText: 'Cancel',
        title: 'Combo Option',
        body: '',
    };
    Registries.Component.add(ComboOptionPopUps);
    return ComboOptionPopUps;
});
