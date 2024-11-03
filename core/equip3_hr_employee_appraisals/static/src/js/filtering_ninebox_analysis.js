odoo.define('equip3_hr_employee_appraisals.ControlPanel', function (require) {
    "use strict";

    const ControlPanel = require('app_search_range_date_number.ControlPanel');
    const rpc = require('web.rpc');

    class nineBoxControlPanel extends ControlPanel {
        _attachAdditionalContent() {
            super._attachAdditionalContent(...arguments);
            this._hideFilteringNineboxAnalysisFields();

            if (this.el != null) {
                const evaluationPeriodInput = this.el.querySelector('.evaluation_period');
                const departmentInput = this.el.querySelector('.department');
                const employeeInput = this.el.querySelector('.employee');
                const jobPositionInput = this.el.querySelector('.job_position');

                const self = this
                if (self.env.action !== undefined) {
                    var view_xml_id = self.env.action.xml_id
                    
                    // no need to check again
                    if (view_xml_id == "equip3_hr_employee_appraisals.action_employee_performance_pivot1") { 
                        this._handleSearchButton();
                        this._createSelectionDepartment();
                        this._createSelectionEvaluationPeriod();
                        this._createSelectionEmployee();
                        this._createSelectionJobPosition();

                        evaluationPeriodInput.addEventListener('change', this._handleFilterInput.bind(this));
                        departmentInput.addEventListener('change', this._handleFilterInput.bind(this));
                        employeeInput.addEventListener('change', this._handleFilterInput.bind(this));
                        jobPositionInput.addEventListener('change', this._handleFilterInput.bind(this));

                    }
                }
            }
        }

        _handleSearchButton() {
            if (this.el != null) {
                const button = this.el.querySelector('.ninebox_filter_btn');
                if (button) {
                    button.addEventListener('click', this._handleFilterInput.bind(this));
                }
            }
        }

        _handleFilterInput() {
            const values = [];
            if (this.el != null) {
                const evaluationPeriod = this.el.querySelector('.evaluation_period').value;
                const department = this.el.querySelector('.department').value;
                const employee = this.el.querySelector('.employee').value;
                const jobPosition = this.el.querySelector('.job_position').value;

                if (evaluationPeriod !== "") {
                    values.push(parseInt(evaluationPeriod))
                }

                if (department !== "") {
                    values.push(parseInt(department))
                }

                if (employee !== "") {
                    values.push(parseInt(employee))
                }

                if (jobPosition !== "") {
                    values.push(parseInt(jobPosition))
                }
            }

            rpc.query({
                model: 'employee.performance',
                method: 'perform_search',
                args: values,
            }).then(result => {
                var self = this;
                const domain = [['id', 'in', result], ['state', '=', 'done']];
                // Update new domain
                self.model.config.domain = domain;
                // Trigger the search then it will be reloaded
                self.model.trigger('search', { keepOrder: true, keepFilters: true });
                self.do_search();
            });
        }

        _createSelectionEvaluationPeriod() {
            var self = this;
            // rpc.query({
            //     model: 'employee.performance',
            //     method: 'search_read',
            //     fields: ['date_range_id'],
            //     domain: [],
            // }).then(function (performances) {
            //     const periodInput = self.el.querySelector('.evaluation_period');
            //     if (periodInput) {
            //         // Clear existing options
            //         periodInput.innerHTML = '<option value="">Select Period</option>';
            //         // Create a set to store unique employee ids
            //         const periodIdsSet = new Set();
            //         performances.forEach((performance) => {
            //             if (performance.date_range_id && performance.date_range_id[0]) {
            //                 periodIdsSet.add(performance.date_range_id[0]);
            //             }
            //         });
            //         rpc.query({
            //             model: 'performance.date.range',
            //             method: 'search_read',
            //             fields: ['id', 'name'],
            //             domain: [['id', 'in', Array.from(periodIdsSet)]],
            //         }).then(function (periods) {
            //             periods.forEach((period) => {
            //                 const option = document.createElement('option');
            //                 option.value = period.id;
            //                 option.text = period.name;
            //                 periodInput.appendChild(option);
            //             });
            //         });
            //     }
            // });

            rpc.query({
                model: 'performance.date.range',
                method: 'search_read',
                fields: ['id', 'name'],
                domain: [],
            }).then(function (periods) {
                // Populate the department selection input with the fetched data
                if (self.el != null) {
                    const periodInput = self.el.querySelector('.evaluation_period');
                    if (periodInput) {
                        const selectedValue = periodInput.value;
                        // Clear existing options
                        periodInput.innerHTML = '<option value="">Select Period</option>';
                        periods.forEach((period) => {
                            const option = document.createElement('option');
                            option.value = period.id;
                            option.text = period.name;
                            periodInput.appendChild(option);
                        });
                        if (selectedValue) {
                            periodInput.value = selectedValue;
                        }
                    }
                }
            });
        }

        _createSelectionDepartment() {
            var self = this;

            rpc.query({
                model: 'hr.department',
                method: 'search_read',
                fields: ['id', 'name'],
                domain: [],
            }).then(function (departments) {
                // Populate the department selection input with the fetched data
                if (self.el != null) {
                    const departmentInput = self.el.querySelector('.department');
                    if (departmentInput) {
                        // Store the current selected value (if any)
                        const selectedValue = departmentInput.value;
                        // Clear existing options
                        departmentInput.innerHTML = '<option value="">Select Department</option>';
                        // Add options from departments data
                        departments.forEach((department) => {
                            const option = document.createElement('option');
                            option.value = department.id;
                            option.text = department.name;
                            departmentInput.appendChild(option);
                        });
                        // Set the previously selected value (if any) as the selected option
                        if (selectedValue) {
                            departmentInput.value = selectedValue;
                        }
                    }
                }
            });
            // rpc.query({
            //     model: 'employee.performance',
            //     method: 'search_read',
            //     fields: ['department_id'],
            //     domain: [],
            // }).then(function (performances) {
            //     const departmentInput = self.el.querySelector('.department');
            //     if (departmentInput) {
            //         // Clear existing options
            //         departmentInput.innerHTML = '<option value="">Select Department</option>';
            //         // Create a set to store unique employee ids
            //         const depertmentIdsSet = new Set();
            //         performances.forEach((performance) => {
            //             if (performance.department_id && performance.department_id[0]) {
            //                 depertmentIdsSet.add(performance.department_id[0]);
            //             }
            //         });
            //         rpc.query({
            //             model: 'hr.department',
            //             method: 'search_read',
            //             fields: ['id', 'name'],
            //             domain: [['id', 'in', Array.from(depertmentIdsSet)]],
            //         }).then(function (departments) {
            //             departments.forEach((department) => {
            //                 const option = document.createElement('option');
            //                 option.value = department.id;
            //                 option.text = department.name;
            //                 departmentInput.appendChild(option);
            //             });
            //         });
            //     }
            // });

            // rpc.query({
            //     model: 'hr.department',
            //     method: 'search_read',
            //     fields: ['id', 'name'],
            //     domain: [],
            // }).then(function (departments) {
            //     // Populate the department selection input with the fetched data
            //     console.log("dep: ", departments)
            //     const departmentInput = self.el.querySelector('.department');
            //     if (departmentInput) {
            //         // Clear existing options
            //         departmentInput.innerHTML = '<option value="">Select Department</option>';
            //         // Add options from departments data
            //         departments.forEach((department) => {
            //             const option = document.createElement('option');
            //             option.value = department.id;
            //             option.text = department.name;
            //             departmentInput.appendChild(option);
            //         });
            //     }
            // });
        }

        _createSelectionEmployee() {
            var self = this;
            // rpc.query({
            //     model: 'employee.performance',
            //     method: 'search_read',
            //     fields: ['employee_id'],
            //     domain: [],
            // }).then(function (performances) {
            //     const employeeInput = self.el.querySelector('.employee');
            //     if (employeeInput) {
            //         // Clear existing options
            //         employeeInput.innerHTML = '<option value="">Select Employee</option>';
            //         // Create a set to store unique employee ids
            //         const employeeIdsSet = new Set();
            //         // Collect unique employee ids from employee.performance data
            //         performances.forEach((performance) => {
            //             if (performance.employee_id && performance.employee_id[0]) {
            //                 employeeIdsSet.add(performance.employee_id[0]);
            //             }
            //         });
            //         // Fetch hr.employee data for the collected employee ids
            //         rpc.query({
            //             model: 'hr.employee',
            //             method: 'search_read',
            //             fields: ['id', 'name'],
            //             domain: [['id', 'in', Array.from(employeeIdsSet)]],
            //         }).then(function (employees) {
            //             // Add options from hr.employee data
            //             employees.forEach((employee) => {
            //                 const option = document.createElement('option');
            //                 option.value = employee.id;
            //                 option.text = employee.name;
            //                 employeeInput.appendChild(option);
            //             });
            //         });
            //     }
            // });

            rpc.query({
                model: 'hr.employee',
                method: 'search_read',
                fields: ['id', 'name'],
                domain: [],
            }).then(function (employees) {
                // Populate the department selection input with the fetched data
                if (self.el != null) {
                    const employeeInput = self.el.querySelector('.employee');
                    if (employeeInput) {
                        // Clear existing options
                        const selectedValue = employeeInput.value;
                        employeeInput.innerHTML = '<option value="">Select Employee</option>';
                        // Add options from employees data
                        employees.forEach((employee) => {
                            const option = document.createElement('option');
                            option.value = employee.id;
                            option.text = employee.name;
                            employeeInput.appendChild(option);
                        });

                        if (selectedValue) {
                            employeeInput.value = selectedValue
                        }
                    }
                }
            });
        }

        _createSelectionJobPosition() {
            var self = this;
            rpc.query({
                model: 'hr.job',
                method: 'search_read',
                fields: ['id', 'name'],
                domain: [],
            }).then(function (jobs) {
                // Populate the department selection input with the fetched data
                if (self.el != null) {
                    const jobInput = self.el.querySelector('.job_position');
                    if (jobInput) {
                        // Clear existing options
                        const selectedValue = jobInput.value;
                        jobInput.innerHTML = '<option value="">Select Job</option>';
                        // Add options from jobs data
                        jobs.forEach((job) => {
                            const option = document.createElement('option');
                            option.value = job.id;
                            option.text = job.name;
                            jobInput.appendChild(option);
                        });

                        if (selectedValue) {
                            jobInput.value = selectedValue
                        }
                    }
                }
            });

            // rpc.query({
            //     model: 'employee.performance',
            //     method: 'search_read',
            //     fields: ['job_id'],
            //     domain: [],
            // }).then(function (performances) {
            //     const jobPositionInput = self.el.querySelector('.job_position');
            //     if (jobPositionInput) {
            //         // Clear existing options
            //         jobPositionInput.innerHTML = '<option value="">Select Job</option>';
            //         // Create a set to store unique employee ids
            //         const jobtIdsSet = new Set();
            //         performances.forEach((performance) => {
            //             if (performance.job_id && performance.job_id[0]) {
            //                 jobtIdsSet.add(performance.job_id[0]);
            //             }
            //         });
            //         rpc.query({
            //             model: 'hr.job',
            //             method: 'search_read',
            //             fields: ['id', 'name'],
            //             domain: [['id', 'in', Array.from(jobtIdsSet)]],
            //         }).then(function (jobs) {
            //             jobs.forEach((job) => {
            //                 const option = document.createElement('option');
            //                 option.value = job.id;
            //                 option.text = job.name;
            //                 jobPositionInput.appendChild(option);
            //             });
            //         });
            //     }
            // });

            // rpc.query({
            //     model: 'hr.job',
            //     method: 'search_read',
            //     fields: ['id', 'name'],
            //     domain: [],
            // }).then(function (jobs) {
            //     const jobInput = self.el.querySelector('.job_position');
            //     if (jobInput) {
            //         // Clear existing options
            //         jobInput.innerHTML = '<option value="">Select Job Position</option>';
            //         // Add options from jobs data
            //         jobs.forEach((job) => {
            //             const option = document.createElement('option');
            //             option.value = job.id;
            //             option.text = job.name;
            //             jobInput.appendChild(option);
            //         });
            //     }
            // });
        }

        _hideFilteringNineboxAnalysisFields() {
            var self = this
            if (self.env.action !== undefined) {
                var view_xml_id = self.env.action.xml_id
                if (view_xml_id == "equip3_hr_employee_appraisals.action_employee_performance_pivot1") {
                    $('.ninebox_filter_container').show();
                }
                else {
                    $('.ninebox_filter_container').hide();
                }
            }
        }
    }

    nineBoxControlPanel.template = 'equip3_hr_employee_appraisals.ControlPanel';

    return nineBoxControlPanel;
});
