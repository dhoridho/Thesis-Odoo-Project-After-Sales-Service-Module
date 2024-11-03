odoo.define('equip3_pos_attendance.res_users_image_form', function(require) {
  "use strict";

  var FormController = require('web.FormController');
  var rpc = require('web.rpc');

  FormController.include({
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);
        if (this.model === 'res.users.image'){
          this.promise_face_recognition = this.load_models();
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
    /**
     * Override the saveRecord method to add custom logic before/after saving.
     */
    saveRecord: function () {
      var self = this;
      var oldRecord = self.model.get(self.handle);
      return this._super(...arguments).then(function(result){
        if (self.modelName === 'res.users.image') {
          // Get the current record data (before save)

          var record = self.model.get(self.handle);
          // Check if the record is new or existing
          var isNewRecord = oldRecord.data.id === undefined;  // If there's no ID, it's a new record
          if (isNewRecord) {
            self._progressbar(record, '_save_custom')
          }
        }
        return result;
      });
    },

    _save_custom: async function (record) {
      var image = $('#face-recognition-image img')[0];
      const fullFaceDescription = await faceapi
          .detectSingleFace(image, new faceapi.TinyFaceDetectorOptions())
          .withFaceLandmarks()
          .withFaceDescriptor();

      let recordHasData = record.data !== undefined;
      if (fullFaceDescription && recordHasData) {
          record.data.image_detection = this._draw_face(image, fullFaceDescription).split(',')[1];
          record.data.descriptor = this._f32base64(fullFaceDescription.descriptor);
      }
      //this._setValue({ operation: 'CREATE', id: record.id, data:record.data });
      console.log(record);
      await this._save_descriptor(record.data.id, fullFaceDescription.descriptor, record.data.image_detection);
      Swal.close();
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
                            await this._save_descriptor($(value).data('id'), fullFaceDescription.descriptor, image_detection);
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

    _save_descriptor: function (userImageID, descriptor, image_detection) {
        return this._rpc({
            model: 'res.users.image',
            method: 'write',
            args: [[userImageID], {
                descriptor: this._f32base64(descriptor),
                image_detection: image_detection,
            }],
        }).then(function () {
            console.log('descriptor success save');
        });
    },

  })
});