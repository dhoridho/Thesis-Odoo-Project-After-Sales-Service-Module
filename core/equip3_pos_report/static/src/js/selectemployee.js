odoo.define('pos_hr.useSelectEmployee', function (require) {
    'use strict';

    const ajax = require('web.ajax');

    const { Component } = owl;

    function useSelectEmployee() {
        const current = Component.current;
        var self = this
        async function askPin(employee) {
            const { confirmed, payload: inputPin } = await this.showPopup('NumberPopup', {
                isPassword: true,
                title: this.env._t('Password ?'),
                startingValue: null,
            });

            if (!confirmed) return false;

            if (employee.pin === Sha1.hash(inputPin)) {

                ajax.jsonRpc('/set_attendance_pos', 'call', {
                    'pos_id':this.env.pos.config_id,
                    'employee_id':employee.id,
                }).then((result) => {
                });

                return employee;
            } else {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Incorrect Password'),
                });
                return false;
            }
        }

        async function selectEmployee(selectionList) {
            const { confirmed, payload: employee } = await this.showPopup('SelectionPopup', {
                title: this.env._t('Change Cashier'),
                list: selectionList,
            });

            if (!confirmed) return false;

            if (!employee.pin) {

                ajax.jsonRpc('/set_attendance_pos', 'call', {
                    'pos_id':this.env.pos.config_id,
                    'employee_id':employee.id,
                }).then((result) => {
                });
                
                return employee;
            }

            return await askPin.call(current, employee);
        }
        return { askPin: askPin.bind(current), selectEmployee: selectEmployee.bind(current) };
    }

    return useSelectEmployee;
});
