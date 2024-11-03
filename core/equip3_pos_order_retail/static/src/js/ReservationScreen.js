odoo.define('equip3_pos_order_retail.ReservationScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent'); 
    const ProductScreen = require('point_of_sale.ProductScreen'); 
    const {useListener} = require('web.custom_hooks'); 
    const Registries = require('point_of_sale.Registries'); 
    
    class ReservationScreen extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('close-screen', this.back);
            useListener('search', this._onSearch);
            useListener('click-arrived', this._onClickArrived);
            useListener('click-cancel', this._onClickCancel);
            this.searchDetails = {};
            this.filter = null;
            this._initializeSearchFieldConstants();
        } 
        back() {
            this.trigger('close-temp-screen');
            this.showScreen('FloorScreen');
        }
        async willStart() {
            var self = this
            this.reserved_order = await this.rpc({
                model: 'reserve.order',
                method: 'search_read',
                domain: [],
                fields: ['name', 'state', 'customer_name', 'cust_phone_no', 'reservation_from', 'reservation_to', 'table_no', 'table_floor', 'reservation_seat'],
            }).then(function(data){
                if(data){
                    _.each(data,function(d){
                        d['reservation_from'] = moment.utc(d['reservation_from']).local().format('MM/DD/YYYY HH:mm:ss')
                        d['reservation_to'] = moment.utc(d['reservation_to']).local().format('MM/DD/YYYY HH:mm:ss')
                    })
                    return data
                }
            })
        }
        async getreserveOrder(){
            await this.rpc({
                model: 'sale.order',
                method: 'search_read',
                domain: [['reserve_order', '=', true]],
                fields: ['partner_id', 'reserve_from', 'reserve_to', 'reserve_table_id'],
            }).then(function(data){
                return data[0].id
            })
        }

        _onClickArrived(event) {
            var self = this;
            this.rpc({
                model: 'reserve.order',
                method: 'guest_arrived',
                args: [[event.detail.id]],
            })
            this.searched_reserved_order = false
            var curr_reserved_order = this.reserved_order
            if(curr_reserved_order && curr_reserved_order.length > 0){
                this.reserved_order = []
                _.each(curr_reserved_order,function(ord){
                    if(ord.id != event.detail.id){
                        var curr_tbl = self.env.pos.tables_by_id[event.detail.tbl_id]
                        self.rpc({
                            model: 'restaurant.table',
                            method: 'lock_table',
                            args: [[event.detail.tbl_id], {
                                'locked': false,
                                'date_reserve': false,
                            }],
                        }, {
                            timeout: 30000,
                            shadow: true,
                        })
                        curr_tbl.locked = false
                        self.reserved_order.push(ord)
                        self.render();
                    }
                })
            }
        }
        
        _onClickCancel(event) {
            var self = this;
            this.rpc({
                model: 'reserve.order',
                method: 'guest_cancel_order',
                args: [[event.detail.id]],
            })
            this.searched_reserved_order = false
            var curr_reserved_order = this.reserved_order
            if(curr_reserved_order && curr_reserved_order.length > 0){
                this.reserved_order = []
                _.each(curr_reserved_order,function(ord){
                    if(ord.id != event.detail.id){
                        var curr_tbl = self.env.pos.tables_by_id[event.detail.tbl_id]
                        self.rpc({
                            model: 'restaurant.table',
                            method: 'lock_table',
                            args: [[event.detail.tbl_id], {
                                'locked': false,
                                'date_reserve': false,
                            }],
                        }, {
                            timeout: 30000,
                            shadow: true,
                        })
                        curr_tbl.locked = false
                        self.reserved_order.push(ord)
                        self.render();
                    }
                })
            }
        }

        // Reservation Screen Search Bar
        _onSearch(event) {
            const searchDetails = event.detail;
            Object.assign(this.searchDetails, searchDetails);

            var self = this
            const { fieldValue, searchTerm } = self.searchDetails;
            const fieldAccessor = self._searchFields[fieldValue];
            const searchCheck = (order) => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(order);
                if (fieldValue === null) return true;
                if (!searchTerm) return true;
                return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (order) => {
                return searchCheck(order);
            };
            this.searched_reserved_order  = this.reserved_order.filter(predicate);
            this.render();
        }

        get searchBarConfig() {
            return {
                searchFields: this.constants.searchFieldNames,
                filter: { show: false, options: [] },
            };
        }
        get _searchFields() {
            const { ReceiptNumber, Date, Customer} = this.getSearchFieldNames();
            var fields = {
                'Reservation Id': (order) => order.name,
                'Customer Name': (order) => order.customer_name,
                'From': (order) => order.reservation_from,
                'To': (order) => order.reservation_to,
                'Table': (order) => order.table_no,
                'Floor': (order) => order.table_floor,
                'Seat': (order) => order.reservation_seat,
            };
            return fields;
        }
        _initializeSearchFieldConstants() {
            this.constants = {};
            Object.assign(this.constants, {
                searchFieldNames: Object.keys(this._searchFields),
            });
        }
        getSearchFieldNames() {
            return {
                ReceiptNumber: this.env._t('Name'),
                Date: this.env._t('Reserved Date'),
                Customer: this.env._t('Customer'),
            };
        }
        clearSearch() {
            this._initializeSearchFieldConstants()
            this.searchDetails = {};
            this.searched_reserved_order = false
            this.render()
        }
    } 
    
    ReservationScreen.template = 'ReservationScreen'; 
    Registries.Component.add(ReservationScreen); 
    return ReservationScreen; 
});
