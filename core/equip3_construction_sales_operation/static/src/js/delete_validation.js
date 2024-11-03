odoo.define('equip3_construction_sales_operation.delete_validation', function (require) {
    'use strict';

    var core = require('web.core');
    var dom = require('web.dom');
    var ListRenderer = require('web.ListRenderer');
    var utils = require('web.utils');
    var Dialog = require('web.Dialog');

    ListRenderer.include({

        _onRemoveIconClick: function (event) {
            // I don't know if stopPropagation is needed or not
            event.stopPropagation();

            if (this.__parentedParent.model === 'job.estimate') {

                // get clicked row record
                var $row = $(event.target).closest('tr');
                var id = $row.data('id');
                var record = this._getRecord(id);

                // get tab record
                var oldData = this.state.data;

                for (let i = 0; i < oldData.length; i++) {
                    if (oldData[i].id === record.id) {
                        if (record.data.is_lock === true) {
                            Dialog.alert(
                                this,
                                "You cannot delete this record because it is locked!",
                            );
                        }else {
                            let self = this
                            let job_estimate = self.__parentedParent.recordData
                            let project_scope_ids = job_estimate.project_scope_ids.data
                            let section_ids = job_estimate.section_ids.data
                            let variable_ids = job_estimate.variable_ids.data
                            // let manufacture_line = job_estimate.manufacture_line.data

                            let material_estimation_ids = job_estimate.material_estimation_ids.data
                            let labour_estimation_ids = job_estimate.labour_estimation_ids.data
                            let overhead_estimation_ids = job_estimate.overhead_estimation_ids.data
                            let equipment_estimation_ids = job_estimate.equipment_estimation_ids.data
                            let internal_asset_ids = job_estimate.internal_asset_ids.data
                            let subcon_estimation_ids = job_estimate.subcon_estimation_ids.data


                            if (record.model === 'project.scope.estimate') {
                                // Check if project_scope_estimation has locked related data (section~estimations)
                                let rec = oldData[i].data
                                let locked_related_data = []

                                if (rec.project_scope !== false) {
                                    for (let j = 0; j < section_ids.length; j++) {
                                        if (section_ids[j].data.project_scope.data.id === rec.project_scope.data.id) {
                                            if (section_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Section Tab')) {
                                                    locked_related_data.push('Section Tab')
                                                    break;
                                                }

                                            }
                                        }
                                    }
                                    for (let j = 0; j < variable_ids.length; j++) {
                                        if (variable_ids[j].data.project_scope.data.id === rec.project_scope.data.id) {
                                            if (variable_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Variable Tab')) {
                                                    locked_related_data.push('Variable Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                    // for (let j = 0; j < manufacture_line.length; j++) {
                                    //     if (manufacture_line[j].data.project_scope.data.id === rec.project_scope.data.id) {
                                    //         if (manufacture_line[j].data.is_lock === true) {
                                    //             if (!locked_related_data.includes('Manufacture Tab')) {
                                    //                 locked_related_data.push('Manufacture Tab')
                                    //             }
                                    //         }
                                    //     }
                                    // }
                                    for (let j = 0; j < material_estimation_ids.length; j++) {
                                        if (material_estimation_ids[j].data.project_scope.data.id === rec.project_scope.data.id) {
                                            if (material_estimation_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Material Estimation Tab')) {
                                                    locked_related_data.push('Material Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                    for (let j = 0; j < labour_estimation_ids.length; j++) {
                                        if (labour_estimation_ids[j].data.project_scope.data.id === rec.project_scope.data.id) {
                                            if (labour_estimation_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Labour Estimation Tab')) {
                                                    locked_related_data.push('Labour Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                    for (let j = 0; j < overhead_estimation_ids.length; j++) {
                                        if (overhead_estimation_ids[j].data.project_scope.data.id === rec.project_scope.data.id) {
                                            if (overhead_estimation_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Overhead Estimation Tab')) {
                                                    locked_related_data.push('Overhead Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                    for (let j = 0; j < equipment_estimation_ids.length; j++) {
                                        if (equipment_estimation_ids[j].data.project_scope.data.id === rec.project_scope.data.id) {
                                            if (equipment_estimation_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Equipment Estimation Tab')) {
                                                    locked_related_data.push('Equipment Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                    for (let j = 0; j < internal_asset_ids.length; j++) {
                                        if (internal_asset_ids[j].data.project_scope.data.id === rec.project_scope.data.id) {
                                            if (internal_asset_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Internal Asset Estimation Tab')) {
                                                    locked_related_data.push('Internal Asset Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                    for (let j = 0; j < subcon_estimation_ids.length; j++) {
                                        if (subcon_estimation_ids[j].data.project_scope.data.id === rec.project_scope.data.id) {
                                            if (subcon_estimation_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Subcon Estimation Tab')) {
                                                    locked_related_data.push('Subcon Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                }

                                if (locked_related_data.length > 0) {
                                    Dialog.alert(
                                        this,
                                        "You cannot delete this project scope because it have locked related data in : " + locked_related_data.join(', ') + "!",

                                    );
                                } else {
                                    var res = this._super.apply(this, arguments);
                                    return res
                                }
                            }else if (record.model === 'section.estimate'){
                                let rec = oldData[i].data
                                let locked_related_data = []

                                if (rec.section_name !== false) {
                                    for (let j = 0; j < variable_ids.length; j++) {
                                        if (variable_ids[j].data.section_name.data.id === rec.section_name.data.id) {
                                            if (variable_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Variable Tab')) {
                                                    locked_related_data.push('Variable Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }

                                    // for (let j = 0; j<manufacture_line.length; j++){
                                    //     if (manufacture_line[j].data.section_name.data.id === rec.section_name.data.id) {
                                    //         if (manufacture_line[j].data.is_lock === true) {
                                    //             if (!locked_related_data.includes('Manufacture Tab')) {
                                    //                 locked_related_data.push('Manufacture Tab')
                                    //                 break;
                                    //             }
                                    //         }
                                    //     }
                                    // }

                                    for (let j = 0; j < material_estimation_ids.length; j++) {
                                        if (material_estimation_ids[j].data.section_name.data.id === rec.section_name.data.id) {
                                            if (material_estimation_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Material Estimation Tab')) {
                                                    locked_related_data.push('Material Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }

                                    for (let j = 0; j < labour_estimation_ids.length; j++) {
                                        if (labour_estimation_ids[j].data.section_name.data.id === rec.section_name.data.id) {
                                            if (labour_estimation_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Labour Estimation Tab')) {
                                                    locked_related_data.push('Labour Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }

                                    for (let j = 0; j < overhead_estimation_ids.length; j++) {
                                        if (overhead_estimation_ids[j].data.section_name.data.id === rec.section_name.data.id) {
                                            if (overhead_estimation_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Overhead Estimation Tab')) {
                                                    locked_related_data.push('Overhead Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }

                                    for (let j = 0; j < equipment_estimation_ids.length; j++) {
                                        if (equipment_estimation_ids[j].data.section_name.data.id === rec.section_name.data.id) {
                                            if (equipment_estimation_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Equipment Estimation Tab')) {
                                                    locked_related_data.push('Equipment Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }

                                    for (let j = 0; j < internal_asset_ids.length; j++) {
                                        if (internal_asset_ids[j].data.section_name.data.id === rec.section_name.data.id) {
                                            if (internal_asset_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Internal Asset Estimation Tab')) {
                                                    locked_related_data.push('Internal Asset Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }

                                    for (let j = 0; j < subcon_estimation_ids.length; j++) {
                                        if (subcon_estimation_ids[j].data.section_name.data.id === rec.section_name.data.id) {
                                            if (subcon_estimation_ids[j].data.is_lock === true) {
                                                if (!locked_related_data.includes('Subcon Estimation Tab')) {
                                                    locked_related_data.push('Subcon Estimation Tab')
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                }


                                if (locked_related_data.length > 0) {
                                    Dialog.alert(
                                        this,
                                        "You cannot delete this section because it have locked related data in : "+ locked_related_data.join(', ')+"!",
                                    );
                                }else{
                                    var res = this._super.apply(this, arguments);
                                    return res
                                }
                            }else if(record.model === 'variable.estimate' ){
                                var rec = oldData[i].data
                                var locked_related_data = []

                                if (rec.variable_name !== false) {

                                    // for (let j = 0; j < manufacture_line.length; j++) {
                                    //     if (manufacture_line[j].data.variable_ref !== false) {
                                    //         if (manufacture_line[j].data.variable_ref.data.id === rec.variable_name.data.id) {
                                    //             if (manufacture_line[j].data.is_lock === true) {
                                    //                 if (!locked_related_data.includes('Manufacture Tab')) {
                                    //                     locked_related_data.push('Manufacture Tab')
                                    //                     break;
                                    //                 }
                                    //             }
                                    //         }
                                    //     }
                                    // }

                                    for (let j = 0; j < material_estimation_ids.length; j++) {
                                        if (material_estimation_ids[j].data.variable_ref !== false) {
                                            if (material_estimation_ids[j].data.variable_ref.data.id === rec.variable_name.data.id) {
                                                if (material_estimation_ids[j].data.is_lock === true) {
                                                    if (!locked_related_data.includes('Material Estimation Tab')) {
                                                        locked_related_data.push('Material Estimation Tab')
                                                        break;
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    for (let j = 0; j < labour_estimation_ids.length; j++) {
                                        if (labour_estimation_ids[j].data.variable_ref !== false) {
                                            if (labour_estimation_ids[j].data.variable_ref.data.id === rec.variable_name.data.id) {
                                                if (labour_estimation_ids[j].data.is_lock === true) {
                                                    if (!locked_related_data.includes('Labour Estimation Tab')) {
                                                        locked_related_data.push('Labour Estimation Tab')
                                                        break;
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    for (let j = 0; j < overhead_estimation_ids.length; j++) {
                                        if (overhead_estimation_ids[j].data.variable_ref !== false) {
                                            if (overhead_estimation_ids[j].data.variable_ref.data.id === rec.variable_name.data.id) {
                                                if (overhead_estimation_ids[j].data.is_lock === true) {
                                                    if (!locked_related_data.includes('Overhead Estimation Tab')) {
                                                        locked_related_data.push('Overhead Estimation Tab')
                                                        break;
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    for (let j = 0; j < equipment_estimation_ids.length; j++) {
                                        if (equipment_estimation_ids[j].data.variable_ref !== false) {
                                            if (equipment_estimation_ids[j].data.variable_ref.data.id === rec.variable_name.data.id) {
                                                if (equipment_estimation_ids[j].data.is_lock === true) {
                                                    if (!locked_related_data.includes('Equipment Estimation Tab')) {
                                                        locked_related_data.push('Equipment Estimation Tab')
                                                        break;
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    for (let j = 0; j < internal_asset_ids.length; j++) {
                                        if (internal_asset_ids[j].data.variable_ref !== false) {
                                            if (internal_asset_ids[j].data.variable_ref.data.id === rec.variable_name.data.id) {
                                                if (internal_asset_ids[j].data.is_lock === true) {
                                                    if (!locked_related_data.includes('Internal Asset Estimation Tab')) {
                                                        locked_related_data.push('Internal Asset Estimation Tab')
                                                        break;
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    for (let j = 0; j < subcon_estimation_ids.length; j++) {
                                        if (subcon_estimation_ids[j].data.variable_ref !== false) {
                                            if (subcon_estimation_ids[j].data.variable_ref.data.id === rec.variable_name.data.id) {
                                                if (subcon_estimation_ids[j].data.is_lock === true) {
                                                    if (!locked_related_data.includes('Subcon Estimation Tab')) {
                                                        locked_related_data.push('Subcon Estimation Tab')
                                                        break;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                if (locked_related_data.length > 0) {
                                    Dialog.alert(
                                        this,
                                        "You cannot delete this variable because it have locked related data in : "+ locked_related_data.join(', ')+"!",

                                    );
                                }else{
                                    var res = this._super.apply(this, arguments);
                                    return res
                                }

                            }
                            
                            // else if(record.model === 'to.manufacture.line' ){
                            //     rec = oldData[i].data
                            //     locked_related_data = []

                            //     for (let j = 0; j < material_estimation_ids.length; j++) {
                            //         if (material_estimation_ids[j].data.finish_good_id !== false) {
                            //             if (material_estimation_ids[j].data.finish_good_id.data.id === rec.finish_good_id.data.id) {
                            //                 if (material_estimation_ids[j].data.is_lock === true) {
                            //                     if (!locked_related_data.includes('Material Estimation Tab')) {
                            //                         locked_related_data.push('Material Estimation Tab')
                            //                         break;
                            //                     }
                            //                 }
                            //             }
                            //         }
                            //     }

                            //     for (let j = 0; j < labour_estimation_ids.length; j++) {
                            //         if (labour_estimation_ids[j].data.finish_good_id !== false) {
                            //             if (labour_estimation_ids[j].data.finish_good_id.data.id === rec.finish_good_id.data.id) {
                            //                 if (labour_estimation_ids[j].data.is_lock === true) {
                            //                     if (!locked_related_data.includes('Labour Estimation Tab')) {
                            //                         locked_related_data.push('Labour Estimation Tab')
                            //                         break;
                            //                     }
                            //                 }
                            //             }
                            //         }
                            //     }

                            //     for (let j = 0; j < overhead_estimation_ids.length; j++) {
                            //         if (overhead_estimation_ids[j].data.finish_good_id !== false) {
                            //             if (overhead_estimation_ids[j].data.finish_good_id.data.id === rec.finish_good_id.data.id) {
                            //                 if (overhead_estimation_ids[j].data.is_lock === true) {
                            //                     if (!locked_related_data.includes('Overhead Estimation Tab')) {
                            //                         locked_related_data.push('Overhead Estimation Tab')
                            //                         break;
                            //                     }
                            //                 }
                            //             }
                            //         }
                            //     }

                            //     for (let j = 0; j < equipment_estimation_ids.length; j++) {
                            //         if (equipment_estimation_ids[j].data.finish_good_id !== false) {
                            //             if (equipment_estimation_ids[j].data.finish_good_id.data.id === rec.finish_good_id.data.id) {
                            //                 if (equipment_estimation_ids[j].data.is_lock === true) {
                            //                     if (!locked_related_data.includes('Equipment Estimation Tab')) {
                            //                         locked_related_data.push('Equipment Estimation Tab')
                            //                         break;
                            //                     }
                            //                 }
                            //             }
                            //         }
                            //     }

                            //     for (let j = 0; j < internal_asset_ids.length; j++) {
                            //         if (internal_asset_ids[j].data.finish_good_id !== false) {
                            //             if (internal_asset_ids[j].data.finish_good_id.data.id === rec.finish_good_id.data.id) {
                            //                 if (internal_asset_ids[j].data.is_lock === true) {
                            //                     if (!locked_related_data.includes('Internal Asset Estimation Tab')) {
                            //                         locked_related_data.push('Internal Asset Estimation Tab')
                            //                         break;
                            //                     }
                            //                 }
                            //             }
                            //         }
                            //     }

                            //     for (let j = 0; j < subcon_estimation_ids.length; j++) {
                            //         if (subcon_estimation_ids[j].data.finish_good_id !== false) {
                            //             if (subcon_estimation_ids[j].data.finish_good_id.data.id === rec.finish_good_id.data.id) {
                            //                 if (subcon_estimation_ids[j].data.is_lock === true) {
                            //                     if (!locked_related_data.includes('Subcon Estimation Tab')) {
                            //                         locked_related_data.push('Subcon Estimation Tab')
                            //                         break;
                            //                     }
                            //                 }
                            //             }
                            //         }
                            //     }

                            //     if (locked_related_data.length > 0) {
                            //         Dialog.alert(
                            //             this,
                            //             "You cannot delete this finish good because it have locked related data in : "+ locked_related_data.join(', ')+"!",

                            //         );
                            //     }else{
                            //         var res = this._super.apply(this, arguments);
                            //         return res
                            //     }
                            // }
                            else{
                                var res = this._super.apply(this, arguments);
                                return res
                            }

                        }

                    }
                }
            }else{
                var res = this._super.apply(this, arguments);
                return res
            }

        },

    })
});