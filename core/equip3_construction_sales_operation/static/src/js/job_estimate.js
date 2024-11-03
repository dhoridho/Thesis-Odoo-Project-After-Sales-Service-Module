odoo.define('equip3_construction_sales_operation.job_estimate', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');
    var FieldX2Many = require('web.relational_fields').FieldX2Many;
    var dom = require('web.dom');

    FieldX2Many.include({

        _onFieldChanged: function (ev) {
            if (ev.target === this) {
                ev.initialEvent = this.lastInitialEvent;
                return;
            }
            ev.stopPropagation();
            // changes occured in an editable list
            var changes = ev.data.changes;
            if (this.model == "job.estimate") {

                function _isLockUpdate(self, ev, changes, id){

                    self._setValue({
                        operation: 'UPDATE',
                        id: id,
                        data: {'is_lock': changes['is_lock']},
                    }).then(function () {
                        if (ev.data.onSuccess) {
                            ev.data.onSuccess();
                            console.log('success')
                        }
                    }).guardedCatch(function (reason) {
                        if (ev.data.onFailure) {
                            ev.data.onFailure(reason);
                        }
                    });
                }

                function _sectionUpdate(self, ev, changes){
                    var project_scope_ids = self.recordData.project_scope_ids.data
                    var section_ids = self.recordData.section_ids.data
                    var variable_ids = self.recordData.variable_ids.data
                    let project_scope_id = project_scope_ids.find(x => x.id === ev.data.dataPointID)

                    let changed_section = []
                    if (project_scope_id) {
                        for (let i = 0; i < section_ids.length; i++) {
                            console.log('section_ids[i]', section_ids[i].data.project_scope.data)
                            if (section_ids[i].data.project_scope.data !== undefined) {
                                if (section_ids[i].data.project_scope.data.id === project_scope_id.data.project_scope.data.id) {
                                    if (changes['is_lock'] !== project_scope_id.data.is_lock) {
                                        _isLockUpdate(self, ev, changes, section_ids[i].id)
                                        changed_section.push(section_ids[i])
                                    }
                                }
                            }
                        }
                    }
                    if (changed_section.length > 0) {
                        for (let i = 0; i < changed_section.length; i++) {
                            console.log('changed_section[i]', changed_section[i])
                            for (let j = 0; j < variable_ids.length; j++) {
                                if (variable_ids[j].data.section_name.data.id === changed_section[i].data.section_name.data.id) {
                                    _variableUpdate(self, ev, changes, changed_section[i])
                                }
                            }
                            if (self.recordData.is_engineering !== undefined){
                                if (self.recordData.is_engineering){
                                    var manufacture_line = self.recordData.manufacture_line.data
                                    console.log('manufacture_line', manufacture_line)
                                    if (manufacture_line.length>0) {
                                        _manufactureUpdate(self, ev, changes, changed_section[i])
                                    }
                                }
                            }
                        }


                    }
                }

                function _variableUpdate(self, ev, changes, section){
                    var project_scope_ids = self.recordData.project_scope_ids.data
                    var section_ids = self.recordData.section_ids.data
                    var variable_ids = self.recordData.variable_ids.data
                    let section_id
                    if(section_ids.find(x => x.id === ev.data.dataPointID)){
                        section_id = section_ids.find(x => x.id === ev.data.dataPointID)
                    }else{
                        section_id = section
                    }
                    console.log('section_id', section_id)

                    for (let i = 0; i < variable_ids.length; i++) {
                        if (variable_ids[i].data.section_name.data !== undefined) {
                            if (variable_ids[i].data.section_name.data.id === section_id.data.section_name.data.id) {
                                if (changes['is_lock'] !== section_id.data.is_lock) {
                                    _isLockUpdate(self, ev, changes, variable_ids[i].id)
                                }
                                _estimationTabUpdate(self, ev, changes, variable_ids[i])
                                console.log('is_engineering')
                                if (self.recordData.is_engineering !== undefined) {
                                    if (self.recordData.is_engineering) {
                                        var manufacture_line = self.recordData.manufacture_line.data
                                        console.log('manufacture_line', manufacture_line)
                                        if (manufacture_line.length > 0) {
                                            _manufactureUpdate(self, ev, changes, variable_ids[i])
                                        }
                                    }
                                }
                            }

                        }
                    }
                }

                function _manufactureUpdate(self, ev, changes, source){
                    var project_scope_ids = self.recordData.project_scope_ids.data
                    var section_ids = self.recordData.section_ids.data
                    var variable_ids = self.recordData.variable_ids.data
                    var manufacture_line = self.recordData.manufacture_line.data

                    let project_scope_id = undefined
                    let section_id = undefined
                    let variable_id = undefined

                    if(project_scope_ids.find(x => x.id === source.id)){
                        project_scope_id = project_scope_ids.find(x => x.id === source.id)
                    }
                    if(project_scope_id === undefined){
                        if(section_ids.find(x => x.id === source.id)){
                            section_id = section_ids.find(x => x.id === source.id)
                        }
                        if(section_id === undefined){
                            if(variable_ids.find(x => x.id === source.id)){
                                variable_id = variable_ids.find(x => x.id === source.id)
                            }
                        }
                    }

                    console.log('source', source)

                    console.log('====================In Manuf Line =====================')
                    console.log('project_scope_id', project_scope_id)
                    console.log('section_id', section_id)
                    console.log('variable_id', variable_id)

                    if(project_scope_id !== undefined){
                        for (let i = 0; i < manufacture_line.length; i++) {
                            if (manufacture_line[i].data.project_scope_id.data.id === project_scope_id.data.project_scope.data.id){
                                if (changes['is_lock'] !== project_scope_id.data.is_lock) {
                                    _isLockUpdate(self, ev, changes, manufacture_line[i].id)
                                }
                                _estimationTabManufUpdate(self, ev, changes, manufacture_line[i])
                            }
                        }
                    }else if(section_id !== undefined){
                        for (let i = 0; i < manufacture_line.length; i++) {
                            if (manufacture_line[i].data.section_id.data.id === section_id.data.section_name.data.id){
                                if (changes['is_lock'] !== section_id.data.is_lock) {
                                    _isLockUpdate(self, ev, changes, manufacture_line[i].id)
                                }
                                _estimationTabManufUpdate(self, ev, changes, manufacture_line[i])
                            }
                        }
                    }
                    else if(variable_id !== undefined){
                        for (let i = 0; i < manufacture_line.length; i++) {
                            if (manufacture_line[i].data.variable_ref.data.id === variable_id.data.variable_name.data.id){
                                if (changes['is_lock'] !== variable_id.data.is_lock) {
                                    _isLockUpdate(self, ev, changes, manufacture_line[i].id)
                                }
                                _estimationTabManufUpdate(self, ev, changes, manufacture_line[i])
                            }
                        }
                    }
                }

                function _estimationTabUpdate(self, ev, changes, variable){
                    var project_scope_ids = self.recordData.project_scope_ids.data
                    var section_ids = self.recordData.section_ids.data
                    var variable_ids = self.recordData.variable_ids.data
                    var material_estimation_ids = self.recordData.material_estimation_ids.data
                    var labour_estimation_ids = self.recordData.labour_estimation_ids.data
                    var equipment_estimation_ids = self.recordData.equipment_estimation_ids.data
                    var overhead_estimation_ids = self.recordData.overhead_estimation_ids.data
                    var subcon_estimation_ids = self.recordData.subcon_estimation_ids.data
                    var internal_asset_ids = self.recordData.internal_asset_ids.data

                    let variable_id
                    if(variable_ids.find(x => x.id === ev.data.dataPointID)){
                        variable_id = variable_ids.find(x => x.id === ev.data.dataPointID)
                    }else{
                        variable_id = variable
                    }

                    for (let i = 0; i < material_estimation_ids.length; i++) {
                        if (material_estimation_ids[i].data.variable_ref.data.id === variable_id.data.variable_name.data.id){
                            if (changes['is_lock'] !== variable_id.data.is_lock) {
                                _isLockUpdate(self, ev, changes, material_estimation_ids[i].id)
                            }
                        }
                    }
                    for (let i = 0; i < labour_estimation_ids.length; i++) {
                        if (labour_estimation_ids[i].data.variable_ref.data.id === variable_id.data.variable_name.data.id){
                            if (changes['is_lock'] !== variable_id.data.is_lock) {
                                _isLockUpdate(self, ev, changes, labour_estimation_ids[i].id)
                            }
                        }
                    }
                    for (let i = 0; i < overhead_estimation_ids.length; i++) {
                        if (overhead_estimation_ids[i].data.variable_ref.data.id === variable_id.data.variable_name.data.id){
                            if (changes['is_lock'] !== variable_id.data.is_lock) {
                                _isLockUpdate(self, ev, changes, overhead_estimation_ids[i].id)
                            }
                        }
                    }
                    for (let i = 0; i < equipment_estimation_ids.length; i++) {
                        if (equipment_estimation_ids[i].data.variable_ref.data.id === variable_id.data.variable_name.data.id){
                            if (changes['is_lock'] !== variable_id.data.is_lock) {
                                _isLockUpdate(self, ev, changes, equipment_estimation_ids[i].id)
                            }
                        }
                    }
                    for (let i = 0; i < subcon_estimation_ids.length; i++) {
                        if (subcon_estimation_ids[i].data.variable_ref.data.id === variable_id.data.variable_name.data.id){
                            if (changes['is_lock'] !== variable_id.data.is_lock) {
                                _isLockUpdate(self, ev, changes, subcon_estimation_ids[i].id)
                            }
                        }
                    }
                    for (let i = 0; i < internal_asset_ids.length; i++) {
                        if (internal_asset_ids[i].data.variable_ref.data.id === variable_id.data.variable_name.data.id){
                            if (changes['is_lock'] !== variable_id.data.is_lock) {
                                _isLockUpdate(self, ev, changes, internal_asset_ids[i].id)
                            }
                        }
                    }
                }

                function _estimationTabManufUpdate(self, ev, changes, manufacture_line_source){
                    var manufacture_line = self.recordData.manufacture_line.data
                    var material_estimation_ids = self.recordData.material_estimation_ids.data
                    var labour_estimation_ids = self.recordData.labour_estimation_ids.data
                    var equipment_estimation_ids = self.recordData.equipment_estimation_ids.data
                    var overhead_estimation_ids = self.recordData.overhead_estimation_ids.data
                    var subcon_estimation_ids = self.recordData.subcon_estimation_ids.data
                    var internal_asset_ids = self.recordData.internal_asset_ids.data

                    let manufacture
                    if(manufacture_line.find(x => x.id === ev.data.dataPointID)){
                        manufacture = manufacture_line.find(x => x.id === ev.data.dataPointID)
                    }else{
                        manufacture = manufacture_line_source
                    }

                    for (let i = 0; i < material_estimation_ids.length; i++) {
                        if (material_estimation_ids[i].data.finish_good_id.data !== undefined) {
                            if (material_estimation_ids[i].data.finish_good_id.data.id === manufacture.data.finish_good_id.data.id) {
                                if (changes['is_lock'] !== manufacture.data.is_lock) {
                                    _isLockUpdate(self, ev, changes, material_estimation_ids[i].id)
                                }
                            }
                        }
                    }
                    for (let i = 0; i < labour_estimation_ids.length; i++) {
                        if (labour_estimation_ids[i].data.finish_good_id.data !== undefined) {
                            if (labour_estimation_ids[i].data.finish_good_id.data.id === manufacture.data.finish_good_id.data.id){
                                if (changes['is_lock'] !== manufacture.data.is_lock) {
                                    _isLockUpdate(self, ev, changes, labour_estimation_ids[i].id)
                                }
                            }
                        }

                    }
                    for (let i = 0; i < overhead_estimation_ids.length; i++) {
                        if (overhead_estimation_ids[i].data.finish_good_id.data !== undefined) {
                            if (overhead_estimation_ids[i].data.finish_good_id.data.id === manufacture.data.finish_good_id.data.id) {
                                if (changes['is_lock'] !== manufacture.data.is_lock) {
                                    _isLockUpdate(self, ev, changes, overhead_estimation_ids[i].id)
                                }
                            }
                        }
                    }
                    for (let i = 0; i < equipment_estimation_ids.length; i++) {
                        if (equipment_estimation_ids[i].data.finish_good_id.data !== undefined) {
                            if (equipment_estimation_ids[i].data.finish_good_id.data.id === manufacture.data.finish_good_id.data.id) {
                                if (changes['is_lock'] !== manufacture.data.is_lock) {
                                    _isLockUpdate(self, ev, changes, equipment_estimation_ids[i].id)
                                }
                            }
                        }
                    }
                    for (let i = 0; i < subcon_estimation_ids.length; i++) {
                        if (subcon_estimation_ids[i].data.finish_good_id.data !== undefined) {
                            if (subcon_estimation_ids[i].data.finish_good_id.data.id === manufacture.data.finish_good_id.data.id) {
                                if (changes['is_lock'] !== manufacture.data.is_lock) {
                                    _isLockUpdate(self, ev, changes, subcon_estimation_ids[i].id)
                                }
                            }
                        }
                    }
                    for (let i = 0; i < internal_asset_ids.length; i++) {
                        if (internal_asset_ids[i].data.finish_good_id.data !== undefined) {
                            if (internal_asset_ids[i].data.finish_good_id.data.id === manufacture.data.finish_good_id.data.id) {
                                if (changes['is_lock'] !== manufacture.data.is_lock) {
                                    _isLockUpdate(self, ev, changes, internal_asset_ids[i].id)
                                }
                            }
                        }
                    }
                }

                function _initiateIsLock(self, ev, value, id){
                    self._setValue({
                        operation: 'UPDATE',
                        id: id,
                        data: {'is_lock': value},
                    }).then(function () {
                        if (ev.data.onSuccess) {
                            ev.data.onSuccess();
                            console.log('success')
                        }
                    }).guardedCatch(function (reason) {
                        if (ev.data.onFailure) {
                            ev.data.onFailure(reason);
                        }
                    });
                }

                this.lastInitialEvent = undefined;
                if (Object.keys(changes).length) {
                    this.lastInitialEvent = ev;
                    this._setValue({
                        operation: 'UPDATE',
                        id: ev.data.dataPointID,
                        data: changes,
                    }).then(function () {
                        if (ev.data.onSuccess) {
                            ev.data.onSuccess();
                        }
                    }).guardedCatch(function (reason) {
                        if (ev.data.onFailure) {
                            ev.data.onFailure(reason);
                        }
                    });
                    console.log('this', this)
                    console.log('ev data', ev.data)
                    if (!("is_lock" in changes) === false)
                    {
                        if (this.name === 'project_scope_ids') {
                            _sectionUpdate(this, ev, changes)
                        }else if(this.name === 'section_ids'){
                            _variableUpdate(this, ev, changes)
                        }else if(this.name === 'variable_ids'){
                            _estimationTabUpdate(this, ev, changes)
                        }
                        else if(this.name == 'manufacture_line'){
                            _estimationTabManufUpdate(this, ev, changes)
                        }
                    }
                    if (this.name === 'section_ids'){
                        if (!("project_scope" in changes) === false) {
                            console.log('project_scope_ids', this.recordData.project_scope_ids.data)
                            let project_scope_ids = this.recordData.project_scope_ids.data
                            let section_ids = this.recordData.section_ids.data
                            let variable_ids = this.recordData.variable_ids.data
                            let temp_is_lock = false

                            console.log('change', changes)
                            for (let i = 0; i < project_scope_ids.length; i++) {
                                console.log('project_scope_ids', project_scope_ids[i].data.project_scope.data.id)
                                console.log('change id', changes['project_scope'].id)
                                console.log('result', project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id)
                                if (project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id) {
                                    if (project_scope_ids[i].data.is_lock) {
                                        temp_is_lock = true
                                    }
                                }
                            }
                            if (temp_is_lock) {
                                _initiateIsLock(this, ev, temp_is_lock, ev.data.dataPointID)
                            }
                        }
                    }

                    if (this.name === 'variable_ids'){
                        let temp_is_lock = false
                        let project_scope_ids = this.recordData.project_scope_ids.data
                        let section_ids = this.recordData.section_ids.data
                        let variable_ids = this.recordData.variable_ids.data

                        if (!("project_scope" in changes) === false){
                            for (let i = 0; i < project_scope_ids.length; i++) {
                                console.log('project_scope_ids', project_scope_ids[i].data.project_scope.data.id)
                                console.log('change id', changes['project_scope'].id)
                                console.log('result', project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id)
                                if (project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id){
                                    if (project_scope_ids[i].data.is_lock){
                                        temp_is_lock = true
                                    }
                                    break;
                                }
                            }

                        }
                        if (temp_is_lock===false) {
                            if (!("section_name" in changes) === false) {
                                for (let i = 0; i < section_ids.length; i++) {
                                    console.log('section_ids', section_ids[i].data.section_name.data.id)
                                    console.log('change id', changes['section_name'].id)
                                    console.log('result', section_ids[i].data.section_name.data.id === changes['section_name'].id)
                                    if (section_ids[i].data.section_name.data.id === changes['section_name'].id) {
                                        if (section_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock){
                            _initiateIsLock(this, ev, temp_is_lock, ev.data.dataPointID)
                        }
                    }

                    if (this.recordData.is_engineering !== undefined){
                        if (this.recordData.is_engineering){
                            if (this.name === 'manufacture_line'){
                                console.log('manuf this', this)
                                let project_scope_ids = this.recordData.project_scope_ids.data
                                let section_ids = this.recordData.section_ids.data
                                let variable_ids = this.recordData.variable_ids.data
                                let manufacture_line = this.recordData.manufacture_line.data

                                let temp_is_lock = false
                                if (!("project_scope" in changes) === false){
                                    for (let i = 0; i < project_scope_ids.length; i++) {
                                        console.log('project_scope_ids', project_scope_ids[i].data.project_scope.data.id)
                                        console.log('change id', changes['project_scope'].id)
                                        console.log('result', project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id)
                                        if (project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id){
                                            if (project_scope_ids[i].data.is_lock){
                                                temp_is_lock = true
                                            }
                                            break;
                                        }
                                    }
                                }
                                if (temp_is_lock===false) {
                                    if (!("section_name" in changes) === false) {
                                        for (let i = 0; i < section_ids.length; i++) {
                                            console.log('section_ids', section_ids[i].data.section_name.data.id)
                                            console.log('change id', changes['section_name'].id)
                                            console.log('result', section_ids[i].data.section_name.data.id === changes['section_name'].id)
                                            if (section_ids[i].data.section_name.data.id === changes['section_name'].id) {
                                                if (section_ids[i].data.is_lock) {
                                                    temp_is_lock = true
                                                }
                                                break;
                                            }
                                        }
                                    }
                                }
                                if (temp_is_lock===false) {
                                    if (!("variable_ref" in changes) === false) {
                                        for (let i = 0; i < variable_ids.length; i++) {
                                            console.log('variable_ids', variable_ids[i].data.variable_name.data.id)
                                            console.log('change id', changes['variable_ref'].id)
                                            console.log('result', variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id)
                                            if (variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id) {
                                                if (variable_ids[i].data.is_lock) {
                                                    temp_is_lock = true
                                                }
                                                break;
                                            }
                                        }
                                    }
                                }
                                if (temp_is_lock){
                                    _initiateIsLock(this, ev, temp_is_lock, ev.data.dataPointID)
                                }
                            }
                        }
                    }



                    if (this.name === 'material_estimation_ids'){
                        console.log('This is material line')

                        let project_scope_ids = this.recordData.project_scope_ids.data
                        let section_ids = this.recordData.section_ids.data
                        let variable_ids = this.recordData.variable_ids.data
                        let material_estimation_ids = this.recordData.material_estimation_ids.data

                        let temp_is_lock = false
                        if (!("project_scope" in changes) === false){
                            for (let i = 0; i < project_scope_ids.length; i++) {
                                console.log('project_scope_ids', project_scope_ids[i].data.project_scope.data.id)
                                console.log('change id', changes['project_scope'].id)
                                console.log('result', project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id)
                                if (project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id){
                                    if (project_scope_ids[i].data.is_lock){
                                        temp_is_lock = true
                                    }
                                    break;
                                }
                            }

                        }
                        if (temp_is_lock===false) {
                            if (!("section_name" in changes) === false) {
                                for (let i = 0; i < section_ids.length; i++) {
                                    console.log('section_ids', section_ids[i].data.section_name.data.id)
                                    console.log('change id', changes['section_name'].id)
                                    console.log('result', section_ids[i].data.section_name.data.id === changes['section_name'].id)
                                    if (section_ids[i].data.section_name.data.id === changes['section_name'].id) {
                                        if (section_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock===false) {
                            if (!("variable_ref" in changes) === false) {
                                for (let i = 0; i < variable_ids.length; i++) {
                                    console.log('variable_ids', variable_ids[i].data.variable_name.data.id)
                                    console.log('change id', changes['variable_ref'].id)
                                    console.log('result', variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id)
                                    if (variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id) {
                                        if (variable_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock){
                            _initiateIsLock(this, ev, temp_is_lock, ev.data.dataPointID)
                        }
                    }

                    if (this.name === 'labour_estimation_ids'){
                        let project_scope_ids = this.recordData.project_scope_ids.data
                        let section_ids = this.recordData.section_ids.data
                        let variable_ids = this.recordData.variable_ids.data
                        let labour_estimation_ids = this.recordData.labour_estimation_ids.data

                        let temp_is_lock = false
                        if (!("project_scope" in changes) === false){
                            for (let i = 0; i < project_scope_ids.length; i++) {
                                console.log('project_scope_ids', project_scope_ids[i].data.project_scope.data.id)
                                console.log('change id', changes['project_scope'].id)
                                console.log('result', project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id)
                                if (project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id){
                                    if (project_scope_ids[i].data.is_lock){
                                        temp_is_lock = true
                                    }
                                    break;
                                }
                            }

                        }
                        if (temp_is_lock===false) {
                            if (!("section_name" in changes) === false) {
                                for (let i = 0; i < section_ids.length; i++) {
                                    console.log('section_ids', section_ids[i].data.section_name.data.id)
                                    console.log('change id', changes['section_name'].id)
                                    console.log('result', section_ids[i].data.section_name.data.id === changes['section_name'].id)
                                    if (section_ids[i].data.section_name.data.id === changes['section_name'].id) {
                                        if (section_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock===false) {
                            if (!("variable_ref" in changes) === false) {
                                for (let i = 0; i < variable_ids.length; i++) {
                                    console.log('variable_ids', variable_ids[i].data.variable_name.data.id)
                                    console.log('change id', changes['variable_ref'].id)
                                    console.log('result', variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id)
                                    if (variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id) {
                                        if (variable_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock){
                            _initiateIsLock(this, ev, temp_is_lock, ev.data.dataPointID)
                        }
                    }

                    if (this.name === 'overhead_estimation_ids'){
                        var project_scope_ids = this.recordData.project_scope_ids.data
                        var section_ids = this.recordData.section_ids.data
                        var variable_ids = this.recordData.variable_ids.data
                        var overhead_estimation_ids = this.recordData.overhead_estimation_ids.data

                        let temp_is_lock = false
                        if (!("project_scope" in changes) === false){
                            for (let i = 0; i < project_scope_ids.length; i++) {
                                console.log('project_scope_ids', project_scope_ids[i].data.project_scope.data.id)
                                console.log('change id', changes['project_scope'].id)
                                console.log('result', project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id)
                                if (project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id){
                                    if (project_scope_ids[i].data.is_lock){
                                        temp_is_lock = true
                                    }
                                    break;
                                }
                            }

                        }
                        if (temp_is_lock===false) {
                            if (!("section_name" in changes) === false) {
                                for (let i = 0; i < section_ids.length; i++) {
                                    console.log('section_ids', section_ids[i].data.section_name.data.id)
                                    console.log('change id', changes['section_name'].id)
                                    console.log('result', section_ids[i].data.section_name.data.id === changes['section_name'].id)
                                    if (section_ids[i].data.section_name.data.id === changes['section_name'].id) {
                                        if (section_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock===false) {
                            if (!("variable_ref" in changes) === false) {
                                for (let i = 0; i < variable_ids.length; i++) {
                                    console.log('variable_ids', variable_ids[i].data.variable_name.data.id)
                                    console.log('change id', changes['variable_ref'].id)
                                    console.log('result', variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id)
                                    if (variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id) {
                                        if (variable_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock){
                            _initiateIsLock(this, ev, temp_is_lock, ev.data.dataPointID)
                        }
                    }

                    if (this.name === 'equipment_estimation_ids'){
                        var project_scope_ids = this.recordData.project_scope_ids.data
                        var section_ids = this.recordData.section_ids.data
                        var variable_ids = this.recordData.variable_ids.data
                        var equipment_estimation_ids = this.recordData.equipment_estimation_ids.data

                        let temp_is_lock = false
                        if (!("project_scope" in changes) === false){
                            for (let i = 0; i < project_scope_ids.length; i++) {
                                console.log('project_scope_ids', project_scope_ids[i].data.project_scope.data.id)
                                console.log('change id', changes['project_scope'].id)
                                console.log('result', project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id)
                                if (project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id){
                                    if (project_scope_ids[i].data.is_lock){
                                        temp_is_lock = true
                                    }
                                    break;
                                }
                            }

                        }
                        if (temp_is_lock===false) {
                            if (!("section_name" in changes) === false) {
                                for (let i = 0; i < section_ids.length; i++) {
                                    console.log('section_ids', section_ids[i].data.section_name.data.id)
                                    console.log('change id', changes['section_name'].id)
                                    console.log('result', section_ids[i].data.section_name.data.id === changes['section_name'].id)
                                    if (section_ids[i].data.section_name.data.id === changes['section_name'].id) {
                                        if (section_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock===false) {
                            if (!("variable_ref" in changes) === false) {
                                for (let i = 0; i < variable_ids.length; i++) {
                                    console.log('variable_ids', variable_ids[i].data.variable_name.data.id)
                                    console.log('change id', changes['variable_ref'].id)
                                    console.log('result', variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id)
                                    if (variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id) {
                                        if (variable_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock){
                            _initiateIsLock(this, ev, temp_is_lock, ev.data.dataPointID)
                        }
                    }

                    if (this.name === 'internal_asset_ids'){
                        var project_scope_ids = this.recordData.project_scope_ids.data
                        var section_ids = this.recordData.section_ids.data
                        var variable_ids = this.recordData.variable_ids.data
                        var internal_asset_ids = this.recordData.internal_asset_ids.data

                        let temp_is_lock = false
                        if (!("project_scope" in changes) === false){
                            for (let i = 0; i < project_scope_ids.length; i++) {
                                console.log('project_scope_ids', project_scope_ids[i].data.project_scope.data.id)
                                console.log('change id', changes['project_scope'].id)
                                console.log('result', project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id)
                                if (project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id){
                                    if (project_scope_ids[i].data.is_lock){
                                        temp_is_lock = true
                                    }
                                    break;
                                }
                            }

                        }
                        if (temp_is_lock===false) {
                            if (!("section_name" in changes) === false) {
                                for (let i = 0; i < section_ids.length; i++) {
                                    console.log('section_ids', section_ids[i].data.section_name.data.id)
                                    console.log('change id', changes['section_name'].id)
                                    console.log('result', section_ids[i].data.section_name.data.id === changes['section_name'].id)
                                    if (section_ids[i].data.section_name.data.id === changes['section_name'].id) {
                                        if (section_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock===false) {
                            if (!("variable_ref" in changes) === false) {
                                for (let i = 0; i < variable_ids.length; i++) {
                                    console.log('variable_ids', variable_ids[i].data.variable_name.data.id)
                                    console.log('change id', changes['variable_ref'].id)
                                    console.log('result', variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id)
                                    if (variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id) {
                                        if (variable_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock){
                            _initiateIsLock(this, ev, temp_is_lock, ev.data.dataPointID)
                        }
                    }

                    if (this.name === 'subcon_estimation_ids'){
                        var project_scope_ids = this.recordData.project_scope_ids.data
                        var section_ids = this.recordData.section_ids.data
                        var variable_ids = this.recordData.variable_ids.data
                        var subcon_estimation_ids = this.recordData.subcon_estimation_ids.data

                        let temp_is_lock = false
                        if (!("project_scope" in changes) === false){
                            for (let i = 0; i < project_scope_ids.length; i++) {
                                console.log('project_scope_ids', project_scope_ids[i].data.project_scope.data.id)
                                console.log('change id', changes['project_scope'].id)
                                console.log('result', project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id)
                                if (project_scope_ids[i].data.project_scope.data.id === changes['project_scope'].id){
                                    if (project_scope_ids[i].data.is_lock){
                                        temp_is_lock = true
                                    }
                                    break;
                                }
                            }

                        }
                        if (temp_is_lock===false) {
                            if (!("section_name" in changes) === false) {
                                for (let i = 0; i < section_ids.length; i++) {
                                    console.log('section_ids', section_ids[i].data.section_name.data.id)
                                    console.log('change id', changes['section_name'].id)
                                    console.log('result', section_ids[i].data.section_name.data.id === changes['section_name'].id)
                                    if (section_ids[i].data.section_name.data.id === changes['section_name'].id) {
                                        if (section_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock===false) {
                            if (!("variable_ref" in changes) === false) {
                                for (let i = 0; i < variable_ids.length; i++) {
                                    console.log('variable_ids', variable_ids[i].data.variable_name.data.id)
                                    console.log('change id', changes['variable_ref'].id)
                                    console.log('result', variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id)
                                    if (variable_ids[i].data.variable_name.data.id === changes['variable_ref'].id) {
                                        if (variable_ids[i].data.is_lock) {
                                            temp_is_lock = true
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        if (temp_is_lock){
                            _initiateIsLock(this, ev, temp_is_lock, ev.data.dataPointID)
                        }
                    }


                }

            }else{
                this._super.apply(this, arguments);
            }
        },

        _onSaveLine: function (ev) {
            if (this.model === "job.estimate") {
                function customUpdateValue(self, ev, value){
                    self._setValue({
                        operation: 'UPDATE',
                        id: ev.data.recordID,
                        data: value,
                    }).then(function () {
                        if (ev.data.onSuccess) {
                            ev.data.onSuccess();
                            console.log('success')
                        }
                    }).guardedCatch(function (reason) {
                        if (ev.data.onFailure) {
                            ev.data.onFailure(reason);
                        }
                    });
                }

                var self = this;
                ev.stopPropagation();
                this.renderer.commitChanges(ev.data.recordID).then(function () {
                    self.trigger_up('mutexify', {
                        action: function () {
                            return self._saveLine(ev.data.recordID)
                                .then(ev.data.onSuccess)
                                .guardedCatch(ev.data.onFailure);
                        },
                    });
                });

                if (this.name === 'project_scope_ids' || this.name === 'section_ids' || this.name === 'variable_ids' || this.name === 'manufacture_line'
                    || this.name === 'material_estimation_ids' || this.name === 'labour_estimation_ids' || this.name === 'equipment_estimation_ids'
                    || this.name === 'overhead_estimation_ids' || this.name === 'subcon_estimation_ids' || this.name === 'internal_asset_ids'
                )
                {
                    customUpdateValue(self, ev, {'is_new': false})
                }

            }else{
                this._super.apply(this, arguments);
            }
        },



    });

    ListRenderer.include({

        confirmUpdate: function (state, id, fields, ev) {
            if (this.state.model === "project.scope.estimate" || this.state.model === "variable.estimate" || this.state.model === "to.manufacture.line"
                || this.state.model === "section.estimate" || this.state.model === "labour.estimate" || this.state.model === "overhead.estimate"
                || this.state.model === "material.estimate" || this.state.model === "subcon.estimate" || this.state.model === "internal.assets"
                || this.state.model === "equipment.estimate")
            {
                var self = this;

                var oldData = this.state.data;
                this._setState(state);
                return this.confirmChange(state, id, fields, ev).then(function () {
                    // If no record with 'id' can be found in the state, the
                    // confirmChange method will have rerendered the whole view already,
                    // so no further work is necessary.
                    var record = self._getRecord(id);
                    if (!record) {
                        return;
                    }

                    _.each(oldData, function (rec) {
                        if (rec.id !== id) {
                            self._destroyFieldWidgets(rec.id);
                        }
                    });

                    // re-render whole body (outside the dom)
                    self.defs = [];
                    var $newBody = self._renderBody();
                    var defs = self.defs;
                    delete self.defs;

                    return Promise.all(defs).then(function () {
                        // update registered modifiers to edit 'mode' because the call to
                        // _renderBody set baseModeByRecord as 'readonly'
                        _.each(self.columns, function (node) {
                            self._registerModifiers(node, record, null, {mode: 'edit'});
                        });

                        // store the selection range to restore it once the table will
                        // be re-rendered, and the current cell re-selected
                        var currentRowID;
                        var currentWidget;
                        var focusedElement;
                        var selectionRange;
                        if (self.currentRow !== null) {
                            currentRowID = self._getRecordID(self.currentRow);
                            currentWidget = self.allFieldWidgets[currentRowID][self.currentFieldIndex];
                            if (currentWidget) {
                                focusedElement = currentWidget.getFocusableElement().get(0);
                                if (currentWidget.formatType !== 'boolean' && focusedElement) {
                                    selectionRange = dom.getSelectionRange(focusedElement);
                                }
                            }
                        }

                        // remove all data rows except the one being edited, and insert
                        // data rows of the re-rendered body before and after it
                        var $editedRow = self._getRow(id);
                        $editedRow.nextAll('.o_data_row').remove();
                        $editedRow.prevAll('.o_data_row').remove();
                        var $newRow = $newBody.find('.o_data_row[data-id="' + id + '"]');
                        $newRow.prevAll('.o_data_row').get().reverse().forEach(function (row) {
                            $(row).insertBefore($editedRow);
                        });
                        $newRow.nextAll('.o_data_row').get().reverse().forEach(function (row) {
                            $(row).insertAfter($editedRow);
                        });

                        if (self.currentRow !== null) {
                            var newRowIndex = $editedRow.prop('rowIndex') - 1;
                            self.currentRow = newRowIndex;
                            return self._selectCell(newRowIndex, self.currentFieldIndex, {force: true})
                                .then(function () {
                                    // restore the selection range
                                    currentWidget = self.allFieldWidgets[currentRowID][self.currentFieldIndex];
                                    if (currentWidget) {
                                        focusedElement = currentWidget.getFocusableElement().get(0);
                                        if (selectionRange) {
                                            if (selectionRange.start !== undefined && selectionRange.end !== undefined) {
                                                dom.setSelectionRange(focusedElement, selectionRange);
                                            }
                                        }
                                    }
                                });
                        }
                    });
                });
            }
            else{
                return this._super.apply(this, arguments);
            }
        },
    })
});