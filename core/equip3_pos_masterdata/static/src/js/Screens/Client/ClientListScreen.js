odoo.define('equip3_pos_masterdata.ClientListScreen', function (require) {
    'use strict';

    const framework = require('web.framework');
    const ClientListScreen = require('point_of_sale.ClientListScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const { useState } = owl;
    var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;

    const RetailClientListScreen = (ClientListScreen) =>
        class extends ClientListScreen {
            constructor() {
                super(...arguments);
                this.buffered_key_events = [];
                this._onKeypadKeyDown = this._onKeypadKeyDown.bind(this);
                useListener('show-popup', this.removeEventKeyboad);
                useListener('show-reference-contact', () => this.showReferenceAddress());
                useListener('clear-search', () => this.clearSearch());
                useListener('set-customer-to-cart', this.setCustomerToCart);

                this.sync_state = useState({ state: '' });
                useListener('sync-pos-partner', () => this.syncPosPartner());
            }

            mounted() {
                super.mounted();
                posbus.on('closed-popup', this, this.addEventKeyboad);
                this.addEventKeyboad()
            }

            willUnmount() {
                super.willUnmount();
                posbus.off('closed-popup', this, null);
                this.removeEventKeyboad()
            }

            confirm() { // single screen
                try {
                    super.confirm()
                } catch (ex) {
                    const selectedOrder = this.env.pos.get_order();
                    selectedOrder.set_client(this.state.selectedClient)
                    posbus.trigger('reset-screen')
                }
            }

            back() { // single screen
                try {
                    super.back()
                } catch (ex) {
                    posbus.trigger('reset-screen')
                }
                const selectedOrder = this.env.pos.get_order();
                if(selectedOrder){
                    selectedOrder.is_home_delivery = false
                }

            }

            clickNext() {
                if(this.nextButton.command == 'deselect'){ 
                    const selectedOrder = this.env.pos.get_order();
                    if(selectedOrder){
                        selectedOrder.is_home_delivery = false
                    }
                    selectedOrder.paymentlines.models.forEach(function (p) {
                        if(p.payment_method.is_receivables){
                            selectedOrder.remove_paymentline(p);
                        }
                    })
                }
                super.clickNext()
            }

            clearSearch() {
                this.state.query = null
                this.render()
            }
            get lineHeaders() {
                return [
                    { 
                        name:'No.',
                        width: '3%',
                    },
                    { 
                        name:'Name',
                        width: '37%',
                    }, 
                    { 
                        name:'Address',
                        width: '10%',
                    }, 
                    { 
                        name:'Phone',
                        width: '10%',
                    }, 
                    { 
                        name:'Barcode',
                        width: '5%',
                    }, 
                    { 
                        name:'Child of',
                        width: '5%',
                    }, 
                    { 
                        name:'Type',
                        width: '5%',
                    }, 
                    { 
                        name:'Company Type',
                        width: '5%',
                    }, 
                    { 
                        name:'Orders Count',
                        width: '5%',
                    }, 
                    { 
                        name:'Purchase Count',
                        width: '5%',
                    }, 
                    { 
                        name:'Purchase Count',
                        width: '3%',
                    }, 
                ];
            }
            setCustomerToCart(event) {
                const selectedClient = event.detail.client;
                const selectedOrder = this.env.pos.get_order();
                if (!selectedOrder || (selectedOrder && selectedOrder['finalized'])) {
                    this.props.resolve({confirmed: true, payload: selectedClient});
                    return this.trigger('close-temp-screen');
                }
                if (selectedClient && selectedOrder) {
                    selectedOrder.set_client(selectedClient)
                    try {
                        this.props.resolve({confirmed: true, payload: selectedClient});
                        this.trigger('close-temp-screen');
                    } catch (ex) {

                    }
                    posbus.trigger('reset-screen')
                }
            }

            async showReferenceAddress() {
                const selectedClient = this.state.selectedClient;
                if (selectedClient) {
                    const customersReference = this.env.pos.db.partners_by_parent_id[selectedClient.id]
                    this.customersReference = customersReference;
                    this.render()
                }
            }

            get clients() {
                if (this.customersReference) {
                    let clients = this.customersReference
                    this.customersReference = null
                    return clients
                } else {
                    if (this.state.query && this.state.query.trim() !== '') {
                        return this.env.pos.db.search_partner(this.state.query.trim());
                    } else {
                        return this.env.pos.db.get_partners_sorted(1000);
                    }
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
                if (!_.contains(["INPUT", "TEXTAREA"], $(ev.target).prop('tagName'))) {
                    clearTimeout(this.timeout);
                    this.buffered_key_events.push(ev);
                    this.timeout = setTimeout(_.bind(this._keyboardHandler, this), BarcodeEvents.max_time_between_keys_in_ms);
                }
                if ([13, 27, 38, 40].includes(ev.keyCode)) {  // esc key
                    this.buffered_key_events.push(ev);
                    this.timeout = setTimeout(_.bind(this._keyboardHandler, this), BarcodeEvents.max_time_between_keys_in_ms);
                }
            }

            _keyboardHandler() {
                if (this.buffered_key_events.length > 2) {
                    this.buffered_key_events = [];
                    return true;
                }
                if (this.buffered_key_events.length == 1) {
                    var event_click = this.buffered_key_events[0]
                    if ([77,85,79].includes(event_click.keyCode)) {
                        return true;
                    }
                }
                for (let i = 0; i < this.buffered_key_events.length; i++) {
                    let event = this.buffered_key_events[i]

                    // -------------------------- product screen -------------
                    let key = '';
                    if (event.keyCode == 13) { // enter
                        if($('div[search_members="1"] input').val() && $('.tr_child_line').length){
                            $($('.tr_child_line')[0]).click()
                        }
                        else if($('.button.next').length==1){
                                $('.button.next').click()
                            }
                        else{
                            $('.button.back').click()
                        }
                    }
                    if (event.keyCode == 66 || event.keyCode == 27) { // b
                        $(this.el).find('.back').click()
                    }
                    if (event.keyCode == 69) { // e
                        $(this.el).find('.edit-client-button').click()
                    }
                    if (![27, 38, 40, 66, 69].includes(event.keyCode)) {
                        $(this.el).find('.searchbox-client >input').focus()
                    }
                    if ([38, 40].includes(event.keyCode)) {
                        const selectedClient = this.state.selectedClient;
                        let clients = [];
                        if (this.state.query && this.state.query.trim() !== '') {
                            clients = this.env.pos.db.search_partner(this.state.query.trim());
                        } else {
                            clients = this.env.pos.db.get_partners_sorted(1000);
                        }
                        if (clients.length != 0) {
                            if (!selectedClient) {
                                this.state.selectedClient = clients[[0]];
                                this.render();
                            } else {
                                let isSelected = false
                                for (let i = 0; i < clients.length; i++) {
                                    let client = clients[i]
                                    if (client.id == selectedClient.id) {
                                        let line_number = null;
                                        if (event.keyCode == 38) { // up
                                            if (i == 0) {
                                                line_number = clients.length - 1
                                            } else {
                                                line_number = i - 1
                                            }
                                        } else { // down
                                            if (i + 1 >= clients.length) {
                                                line_number = 0
                                            } else {
                                                line_number = i + 1
                                            }
                                        }
                                        if (clients[line_number]) {
                                            this.state.selectedClient = clients[line_number];
                                            this.render();
                                            isSelected = true
                                            break
                                        }
                                    }
                                }
                                if (!isSelected) {
                                    this.state.selectedClient = clients[0];
                                    this.render();
                                }
                            }
                        }

                    }

                }
                this.buffered_key_events = [];
            }

            // async saveChanges(event) {
            //     let self = this;
            //     let fields = event.detail.processedChanges;
            //     if (fields.phone && fields.phone != "" && this.env.pos.config.check_duplicate_phone) {
            //         let partners = await this.rpc({
            //             model: 'res.partner',
            //             method: 'search_read',
            //             domain: [['id', '!=', fields.id], '|', ['phone', '=', fields.phone], ['mobile', '=', fields.phone]],
            //             fields: ['id'],
            //         }, {
            //             shadow: true,
            //             timeout: 65000
            //         }).then(function (count) {
            //             return count
            //         }, function (err) {
            //             return self.env.pos.query_backend_fail(err);
            //         })
            //         if (partners.length) {
            //             return this.env.pos.alert_message({
            //                 title: this.env._t('Error'),
            //                 body: fields.phone + this.env._t(' already used by another customer')
            //             })
            //         }
            //     }
            //     if (fields.mobile && fields.mobile != "" && this.env.pos.config.check_duplicate_phone) {
            //         let partners = await this.rpc({
            //             model: 'res.partner',
            //             method: 'search_read',
            //             domain: [['id', '!=', fields.id], '|', ['phone', '=', fields.mobile], ['mobile', '=', fields.mobile]],
            //             fields: ['id']
            //         }, {
            //             shadow: true,
            //             timeout: 65000
            //         }).then(function (count) {
            //             return count
            //         }, function (err) {
            //             return self.env.pos.query_backend_fail(err);
            //         })
            //         if (partners.length) {
            //             return this.env.pos.alert_message({
            //                 title: this.env._t('Error'),
            //                 body: fields.mobile + this.env._t(' already used by another customer')
            //             })
            //         }
            //     }
            //     if (fields.email && fields.email != "" && this.env.pos.config.check_duplicate_email) {
            //         let partners = await this.rpc({
            //             model: 'res.partner',
            //             method: 'search_read',
            //             domain: [['id', '!=', fields.id], ['email', '=', fields.email]],
            //             fields: ['id']
            //         }, {
            //             shadow: true,
            //             timeout: 65000
            //         }).then(function (count) {
            //             return count
            //         }, function (err) {
            //             return self.env.pos.query_backend_fail(err);
            //         })
            //         if (partners.length) {
            //             return this.env.pos.alert_message({
            //                 title: this.env._t('Error'),
            //                 body: fields.email + this.env._t(' already used by another customer')
            //             })
            //         }
            //     }
            //     // TODO: we sync backend res.partner via longpolling, no need to call load_new_partners(), it reason no call super
            //     let partnerId = await this.rpc({
            //         model: 'res.partner',
            //         method: 'create_from_ui',
            //         args: [event.detail.processedChanges],
            //     });
            //     this.state.selectedClient = this.env.pos.db.get_partner_by_id(partnerId);
            //     this.state.detailIsShown = false;
            //     this.render();
            // }

            is_allow_create_client(){
                if(this.env.pos.config.add_client){
                    return true;
                }
                if (!this.env.pos.config.add_client) {
                    this.env.pos.alert_message({
                        title: this.env._t('Error'),
                        body: this.env._t('You have not permission create new Customer ! You can request admin go to your pos setting / Clients Screen [Tab] / Security and check to field [Allow add client]')
                    })
                }
                return false;
            }

            activateEditMode(event) {
                if(!this.is_allow_create_client()){
                    return;
                }
                super.activateEditMode(event)
                if (event.detail['parent_id']) {
                    this.state.editModeProps['partner']['parent_id'] = event.detail['parent_id'] // todo: send this to ClientDetailsEdit.js for saveChange can get it
                }
            }

            getChangesValues(detail){
                return detail.processedChanges;
            }

            async saveChanges(event) {
                const self = this
                let values = self.getChangesValues(event.detail);
                let partnerId = await this.rpc({
                    model: 'res.partner',
                    method: 'create_from_ui',
                    args: [values],
                }).then(function (clientID) {
                    return clientID
                }, function (error) {
                    self.env.pos.alert_message({
                        title: self.env._t('Error'),
                        body: self.env._t('Hashmicro Server Offline or Your Internet have lose connection')
                    })
                    return null
                })
                if (partnerId) {
                    let partners = await this.env.pos.getDatasByModel('res.partner', [['id', '=', partnerId]])
                    this.env.pos.partner_model.loaded(this.env.pos, partners)
                    this.env.pos.indexed_db.write('res.partner', partners)
                    this.state.selectedClient = this.env.pos.db.get_partner_by_id(partnerId)
                    this.state.detailIsShown = false
                    this.render()
                }
            }

            isShowSyncPosPartner(){
                let is_show = false;
                if(this.env.pos.config.is_manual_sync_member == true){
                    is_show = true;
                }
                return is_show;
            }
            
            async syncPosPartner() {
                const self = this;
                if(self.sync_state.state == 'connecting'){
                    console.log('[syncPosPartner] ~ Cannot Process, Wait for previous process to finish before Clicking again');
                    return;
                }

                let last_write_date = self.env.pos.db.write_date_by_model['res.partner']
                console.log('[syncPosPartner] ~ Get Last Updated after or equal to: ', last_write_date)
                 
                let args = [[], last_write_date];
                framework.blockUI();
                self.sync_state.state = 'connecting';
                let results = await this.rpc({
                    model: 'pos.cache.database',
                    method: 'sync_pos_partner', 
                    args: args
                }, {
                    shadow: true,
                    timeout: 1200000 // 20 minutes
                }).then(function (response) {
                    return response;
                }, function (error) {
                    framework.unblockUI();
                    if (error && error.message && error.message.code == -32098) {
                        console.error('[syncPosPartner] ~ Server Offline')
                    } else {
                        console.error('[syncPosPartner] ~ Error 403')
                    }
                    self.sync_state.state = 'error';
                    return null;
                })
                console.log('[syncPosPartner] ~ Results:', results == null? '0': results.length);
                if (results != null) {
                    console.log('[syncPosPartner] ~ Updating variable res.partner'); 
                    let active_records = results.filter(r => r['active'] == true);
                    let archived_records = results.filter(r => r['active'] == false);
                    for (let i = 0; i < archived_records.length; i++) {
                        self.env.pos.indexed_db.unlink('res.partner', archived_records[i]);
                    }
                    if(active_records.length){
                        self.env.pos.partner_model.loaded(self.env.pos, results)
                        self.env.pos.indexed_db.write('res.partner', active_records);
                    }
                    self.env.pos.db.add_partners(results);
                    self.env.pos.save_results('res.partner', results); 
                    self.env.pos.update_customer_in_cart(results);
                    self.render();
                    console.log('[syncPosPartner] ~ Finish variable res.partner');
                }
                if(self.sync_state.state == 'error'){
                    return self.showPopup('ConfirmPopup', {
                        title: self.env._t('Warning'),
                        body: self.env._t('Failed sync, please try again after 5 seconds'),
                        disableCancelButton: true,
                    })
                }

                framework.unblockUI();
                self.sync_state.state = 'done';
            }

            sync_pos_partner_button_label(){
                return 'Sync Partner';
            }


        }
    Registries.Component.extend(ClientListScreen, RetailClientListScreen);

    return ClientListScreen;
});
