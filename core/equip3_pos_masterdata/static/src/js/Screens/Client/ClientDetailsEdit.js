odoo.define('equip3_pos_masterdata.ClientDetailsEdit', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ClientDetailsEdit = require('point_of_sale.ClientDetailsEdit');
    const {useState} = owl.hooks;
    const {useListener} = require('web.custom_hooks');
    const models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');


    const RetailClientDetailsEdit = (ClientDetailsEdit) =>
        class extends ClientDetailsEdit {
            // constructor() {
            //     super(...arguments);
            //     this.intFields = ['country_id', 'state_id', 'property_product_pricelist'];
            //     const partner = this.props.partner;
            //     this.changes = {
            //         'country_id': partner.country_id && partner.country_id[0],
            //         'state_id': partner.state_id && partner.state_id[0],
            //     };
            // } // odoo15

            mounted() {
                let self = this; 
                super.mounted();
                var Interval = setInterval(function () {
                    if($('.membership-details-box input[name="barcode"]').length==1) {
                        if('name' in self.props.partner == false){
                            

                            let results = self.rpc({
                                model: 'res.partner',
                                method: 'get_barcode_string', 
                                args:[null]
                            }).then(function (response) {
                                $('.membership-details-box input[name="barcode"]').val(response)
                                return response;
                            }, function (error) {
                                if (error && error.message && error.message.code == -32098) {
                                    console.error('[Get Default Barcode Member] ~ Server Offline')
                                } else {
                                    console.error('[Get Default Barcode Member] ~ Error 403')
                                }
                                return null;
                            });


                        clearInterval(Interval);
                        }
                        
                    }
                }, 1000);
            }
            ordersPurchased() {

            }
            saveChanges() {
                var self = this
                let processedChanges = {};
                self.changes.company_id = this.env.pos.company.id
                for (let [key, value] of Object.entries(this.changes)) {
                    if (this.intFields.includes(key)) {
                        processedChanges[key] = parseInt(value) || false;
                    } else {
                        processedChanges[key] = value;
                    }
                }
                if (!processedChanges.name && !this.props.partner.id) {
                    return this.env.pos.alert_message({
                        title: _('A Customer Name Is Required'),
                    });
                }
                if (!processedChanges.special_name && !this.props.partner.id) {
                    return this.env.pos.alert_message({
                        title: _('A Special Name Is Required'),
                    });
                }
                if (!processedChanges.mobile && !this.props.partner.id) {
                    return this.env.pos.alert_message({
                        title: _('A Mobile Is Required'),
                    });
                }
                if (!processedChanges.email && !this.props.partner.id) {
                    return this.env.pos.alert_message({
                        title: _('A Email Is Required'),
                    });
                }
                processedChanges.id = this.props.partner.id || false;
                if (this.props.partner && this.props.partner['parent_id']) {
                    this.changes['parent_id'] = this.props.partner['parent_id']
                }
                if (this.props.partner.id) {
                    this.trigger('save-changes', {processedChanges});
                } else {
                    
                    if(!self.is_checking){
                     
                        this.env.pos.rpc({
                                model: 'res.partner',
                                method: 'check_member_is_duplicate',
                                args: [null,processedChanges.name,processedChanges.mobile,processedChanges.phone],
                            }).then(function (check_member) {
                                if(check_member){
                                    self.showPopup('ErrorPopup', {
                                        title: self.env._t('Warning'),
                                        body: self.env._t('Unable to save changes, member '+processedChanges.name+' already exist.'),
                                    });
                                }
                                else{
                                    self.is_checking = true
                                    self.saveChanges();
                                }
                            }, function (err) {
                                self.showPopup('ErrorPopup', {
                                title: self.env._t('Offline'),
                                body: self.env._t('Your internet or Hashmicro server Offline, not possible refresh POS Database Cache.'),
                            });
                        })
                                
                    }
                    else{
                         super.saveChanges()
                    }
                }
            }
        }
    Registries.Component.extend(ClientDetailsEdit, RetailClientDetailsEdit);

    return RetailClientDetailsEdit;
});
