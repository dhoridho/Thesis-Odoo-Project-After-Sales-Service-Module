odoo.define('equip3_hr_masterdata_employee.change_request_kanban_face_recognition', function(require) {
    "use strict";

    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;
    var rpc = require('web.rpc');
    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;

    var BtnDescriptionFieldOne2Many = FieldOne2Many.include({
        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            if (this.model =='hr.employee.change.request' && this.attrs.name == 'face_ids'){
                this.promise_face_recognition = this.load_models();
            }

        },

        _openFormDialog: function (params) {
            if (this.model =='hr.employee.change.request' && this.view.arch.tag === 'kanban') {
                var context = this.record.getContext(_.extend({},
                    this.recordParams,
                    { additionalContext: params.context }
                ));
                this.trigger_up('open_one2many_record', _.extend(params, {
                    domain: this.record.getDomain(this.recordParams),
                    context: context,
                    field: this.field,
                    fields_view: this.attrs.views && this.attrs.views.form,
                    parentID: this.value.id,
                    viewInfo: this.view,
                    deletable: this.activeActions.delete && params.deletable,
                    on_saved: async record => {
                        this._progressbar(record, '_save_custom1');
                    },
                }));
            }
            else
                this._super.apply(this, arguments);
        },

        _save_custom1: async function (record) {    
            if (_.some(this.value.data, {id: record.id})) {
                await this._setValue({ operation: 'UPDATE', id: record.id});
            }
            else{
                var image = $('#face-recognition-image img')[0];
                const fullFaceDescription = await faceapi
                    .detectSingleFace(image, new faceapi.TinyFaceDetectorOptions())
                    .withFaceLandmarks()
                    .withFaceDescriptor();

                if (fullFaceDescription) {
                    record.data.image_detection = this._draw_face(image, fullFaceDescription).split(',')[1];
                    record.data.descriptor = this._f32base64(fullFaceDescription.descriptor);
                }
                //this._setValue({ operation: 'CREATE', id: record.id, data:record.data });
                console.log(record);
                await this._create_image_ecri(record)
                // await this._setValue({ operation: 'UPDATE', id: record.id});
                Swal.close();
            }
        },
        _onAddo_kanban_button_edit_face_table: function () {
            this.o_kanban_button_edit_face_table = true
        },
        _renderButtons: function () {

            var $this = this
            $('#o_kanban_button_edit_face_table').remove()
            if (this.model !='hr.employee.change.request') {
                this._super.apply(this, arguments);
            }
            if (this.activeActions.create && this.model =='hr.employee.change.request') {
                if (!this.isReadonly && this.view.arch.tag === 'kanban') {
                    this.$buttons = $(QWeb.render('KanbanView.buttons', {
                        btnClass: 'btn-secondary',
                        create_text: this.nodeOptions.create_text,
                        model: this.field.relation,
                        face_mode: this.nodeOptions.face_mode,
                    }));
                    this.$buttons.on('click', 'button.o-kanban-button-new', function( event ) {
                      $('#o_kanban_button_edit_face_table').remove()
                    });
                    this.$buttons.on('click', 'button.o-kanban-button-new', this._onAddRecord.bind(this));
                    
                    this.$buttons.on('click', 'button.o-kanban-button-edit-face-table', function( event ) {
                      $( "button.o-kanban-button-edit-face-table" ).after("<input type='hidden' id='o_kanban_button_edit_face_table' value='1'/>");
                    });
                    // this.$buttons.on('click', 'button.o-kanban-button-edit-face-table', this._onAddo_kanban_button_edit_face_table());
                   this.$buttons.on('click', 'button.o-kanban-button-edit-face-table', this._onAddRecord.bind(this));
                }


                //this._super.apply(this, arguments);
            }
        },
        
        load_models: function(){
                let models_path = '/hr_attendance_face_recognition/static/src/js/models'
                /****Loading the model ****/
                return Promise.all([
                  faceapi.nets.tinyFaceDetector.loadFromUri(models_path),
                  faceapi.nets.faceLandmark68Net.loadFromUri(models_path),
                  faceapi.nets.faceRecognitionNet.loadFromUri(models_path),
                  faceapi.nets.faceExpressionNet.loadFromUri(models_path),
                  faceapi.nets.ageGenderNet.loadFromUri(models_path)
                ]);
        },

        _hide_canvas_face_recognition: function () {
            $('.only-descriptor').toggle( "slow", function() {});
            $('.o-kanban-button-hide-face-recognition').toggleClass('badge-success');
            $('.o-kanban-button-hide-face-recognition').toggleClass('badge-warning');
        },

        _make_descriptors: function (progressBar=false) {
            this.promise_face_recognition.then(
                async () => {
                    var list_images = this.$('.card-img-top');
                    const content = Swal.getContent();
                    list_images = _.filter(list_images, o => {return $(o).data('id');});
                    var i = 0;
                    for (var value of list_images) {
                        console.log("11111111");
                        if (progressBar && content)
                              content.textContent = `Recognition photo number (${i}/${list_images.length})`;   

                        // only descriptor empty
                        if ($(value).data('descriptor') == '0'){
                            const fullFaceDescription = await faceapi
                                  .detectSingleFace(value, new faceapi.TinyFaceDetectorOptions())
                                  .withFaceLandmarks()
                                  .withFaceDescriptor();
                            if (fullFaceDescription) {
                                var image_detection = this._draw_face(value, fullFaceDescription).split(',')[1];
                                await this._save_descriptor_ecri($(value).data('id'), fullFaceDescription.descriptor, image_detection);
                            }
                            //this._setValue({ operation: 'ADD', id: $(value).data('id') });
                        }
                        i++;
                    }
                    this.trigger_up('reload');
                    Swal.close();
            });
        },

        _make_descriptors_progressbar: function () {
            Swal.fire({
              title: 'Face descriptor create process...',
              html: 'I will close in automaticaly',
              timerProgressBar: true,
              allowOutsideClick: false,
              type: "info",
              //background: 'rgba(43, 165, 137, 0.00)',
              backdrop: `
                rgba(0,0,123,0.0)
                url("/images/nyan-cat.gif")
                left top
                no-repeat
              `,
              onBeforeOpen: () => {
                Swal.showLoading()
                this._make_descriptors(true);
              },
              onClose: () => {
                //console.log(this);
                //this._setValue({ operation: 'UPDATE'});

              }
            }).then((result) => {
              /* Read more about handling dismissals below */
              //if (result.dismiss === Swal.DismissReason.timer) {
              //  console.log('I was closed by the timer')
              //}
            })
        },

        _progressbar: function (record, func) {
            return Swal.fire({
              title: 'Face descriptor create process...',
              html: 'I will close in automaticaly',
              timerProgressBar: true,
              allowOutsideClick: false,
              type: "info",
              //background: 'rgba(43, 165, 137, 0.00)',
              backdrop: `
                rgba(0,0,123,0.0)
                url("/images/nyan-cat.gif")
                left top
                no-repeat
              `,
              onBeforeOpen: () => {
                Swal.showLoading()
                this[func](record);
              },
              onClose: () => {
              }
            });
        },

        _draw_face: function (image, detections) {
            const canvas = faceapi.createCanvasFromMedia(image);
            const displaySize = { width: image.naturalWidth, height: image.naturalHeight };
            faceapi.matchDimensions(canvas, displaySize);
            const resizedDetections = faceapi.resizeResults(detections, displaySize);
            canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
            faceapi.draw.drawDetections(canvas, resizedDetections);
            faceapi.draw.drawFaceLandmarks(canvas, resizedDetections);
            return canvas.toDataURL();
        },

        _f32base64: function (descriptor) {
            // descriptor from float32 to base64 33% more data
            let f32base64 = btoa(String.fromCharCode(...(new Uint8Array(descriptor.buffer))));
            return f32base64;
        },

        _save_descriptor_ecri: function (userImageID, descriptor, image_detection) {
            return this._rpc({
                model: 'employee.change.request.image',
                method: 'write',
                args: [[userImageID], {
                    descriptor: this._f32base64(descriptor),
                    image_detection: image_detection,
                }],
            }).then(function () {
                console.log('descriptor success save');
            });
        },

        _create_image_ecri: async function (record) {
            var data = record.data;

            
            if($('#o_kanban_button_edit_face_table').val()=="1"){
                var data_img = {
                        'descriptor': data.descriptor,
                        'image_detection': data.image_detection,
                        'image': data.image,
                        'o_kanban_button_edit_face_table':true,
                        // 'change_id': data.change_id_str, //default_res_user_id
                        'name': data.name,
                        'sequence': data.sequence
                    }
                console.log('descriptor success create');
                $('input[name="trigger_change_image"]').val(JSON.stringify(data_img));
                $('input[name="trigger_change_image"]').trigger('change')
            }
            else{

                var data_img = {
                        'descriptor': data.descriptor,
                        'image_detection': data.image_detection,
                        'image': data.image,
                 
                        // 'change_id': data.change_id_str, //default_res_user_id
                        'name': data.name,
                        'sequence': data.sequence
                    }
                $('input[name="trigger_change_image"]').val(JSON.stringify(data_img));
                $('input[name="trigger_change_image"]').trigger('change')
                console.log('descriptor success create');
            }
        },
    });


});