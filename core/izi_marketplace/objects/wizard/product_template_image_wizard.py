from odoo import fields, models, api, tools
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
import mimetypes
SUPPORTED_IMAGE_MIMETYPES = ['image/jpeg', 'image/jpg', 'image/png']


class ProductTemplateImagesWizard(models.TransientModel):
    _name = "product.template.images.wizard"
    _description = "Product Template Images Wizard"

    name = fields.Char(string="Image URL", readonly=True)
    image = fields.Binary('Image', attachment=True)
    file_name = fields.Char(string="Filename", readonly=True)
    mimetype = fields.Char('MimeType')
    image_width = fields.Integer('Width')
    image_height = fields.Integer('Height')

    @api.depends('image')
    def create_images(self):
        context = dict(self.env.context) or {}
        product = self.env['product.template'].browse([context.get('active_id')])
        mime_type = mimetypes.MimeTypes().guess_type(self.file_name)[0]
        if mime_type not in SUPPORTED_IMAGE_MIMETYPES:
            raise ValidationError(
                "Image has wrong image format, please use images with extensions [.jpg, .jpeg, .png]")

        try:
            image = tools.base64_to_image(self.image)
            im_width = image.width
            im_height = image.height
        except Exception:
            im_width = 0
            im_height = 0

        if im_width < 300 or im_height < 300:
            raise ValidationError(
                "Image size smaller than recommended size. Minimum image size: 300x300. For better quality using a larger than 700x700")

        product.mp_product_image_ids = [(0, 0, {
            'name': self.name,
            'image': self.image,
            'file_name': self.file_name,
            'image_width': im_width,
            'image_height': im_height,
            'mimetype': mime_type
        })]
